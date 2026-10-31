"""Redundancy: adjacent-sentence overlap, lexical or structural.

Default path (numpy only): TF-IDF cosine similarity between consecutive sentences over stopword-
filtered unigrams and bigrams, plus a token-alignment check that catches TEMPLATED neighbours:
sentences that reuse the same frame with the slots swapped ("The get_user function returns a user
object. The get_group function returns a group object."). TF-IDF alone misses those, because the
swapped slot words dominate the vector and IDF down-weights the shared frame.

When the ``[nlp]`` extra brings sentence-transformers, a dense-embedding path catches *rephrased*
redundancy (the same idea in different words) that neither lexical measure sees; the numpy path
stays the fallback.

v0.15 adds a document-wide check: a long sentence repeated, verbatim or nearly so, anywhere later
in the document (shingle candidates, verified by token alignment). Adjacent comparison cannot see
a thesis sentence copied from the summary into the last section. Score is the larger of the
adjacent-pair fraction and a saturating count of repeated sentences. URLs are removed before
comparing, so two link lines that share a host and path prefix are not "redundant".

scikit-learn used to provide the TF-IDF and was therefore a required dependency of a package whose
scan path is meant to be numpy-only; it is now an ``[eval]`` extra.
"""

from __future__ import annotations

import math
from collections import Counter
from itertools import pairwise

import numpy as np
import regex as re

from slopscore.document import Document
from slopscore.features._nlp import embed, is_embeddings_available
from slopscore.features.base import register, saturating
from slopscore.models import Dimension, Evidence, EvidenceKind, FeatureResult, Severity
from slopscore.normalize.quotes import inside_quotes
from slopscore.spans import TextSpan

RULE_ADJACENT_PAIR = "REDUNDANT_ADJACENT_PAIR"
RULE_REPEATED_SENTENCE = "REDUNDANT_REPEATED_SENTENCE"
_RULES = frozenset({RULE_ADJACENT_PAIR, RULE_REPEATED_SENTENCE})
_SUMMARY_LIMIT = 3

_URL = re.compile(r"https?://\S+")
# A sentence that carried a URL and has fewer content tokens than this once it is removed is a
# link line ("Runbook (https://...)"); it is never redundant with its neighbour.
_LINK_LINE_MAX_CONTENT = 3

# Document-wide repeats. Fifteen words is the floor because short sentences recur in ordinary
# prose ("The results are shown below."). Candidates are earlier sentences sharing a word
# 5-shingle; a candidate counts when its token alignment (LCS over the longer sentence) is at
# least 0.85, which allows a word or two of edit between copies. Shingle Jaccard alone does not:
# one changed word near the end of a 19-word sentence already drops it to 0.76.
_SHINGLE = 5
_REPEAT_MIN_TOKENS = 15
_REPEAT_ALIGNMENT = 0.85
# Repeated sentences at which the repeat term reaches 1.0; one repeat scores 0.25.
_REPEAT_FULL_SCALE = 4.0
# Headings and list items repeat legitimately (navigation, reference lists, table rows).
_NON_PROSE = frozenset({"heading", "list_item"})

_SIMILARITY_THRESHOLD = 0.6
# Fraction of aligned tokens (longest common subsequence over the longer sentence) at or above
# which two neighbours share a frame. Ordinary adjacent prose sits around 0.2-0.35 because only
# function words align; templated pairs sit above 0.7.
_FRAME_THRESHOLD = 0.6
# Frame alignment needs enough tokens to mean anything; very short sentences ("I like it. I
# like them.") are ordinary in plain and non-native English and must not count.
_FRAME_MIN_TOKENS = 6
# Dense embeddings (MiniLM) score paraphrases higher than TF-IDF; a higher bar avoids flagging
# merely on-topic adjacent sentences. Measured: rephrased redundancy ~0.53-0.56, while clean
# non-native and simple-English adjacent pairs stay <=0.30, so 0.50 separates them with headroom
# and keeps the fairness gate green.
_EMBED_THRESHOLD = 0.5

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'_-]*")
_STOPWORDS = frozenset(
    """a an the and or but if so of to in on at by for from with as is are was were be been
    being it its this that these those there here he she they we you i me him her them us my
    your his their our not no nor do does did done have has had can could will would shall
    should may might must than then when where which who whom whose what why how all any each
    every some such only own same too very just also into onto over under up down out about
    after before between through during while because until again further once""".split()
)


def _tokens(sentence: str) -> list[str]:
    return list(_TOKEN.findall(_URL.sub(" ", sentence).lower()))


def _is_link_line(sentence: str) -> bool:
    if not _URL.search(sentence):
        return False
    return sum(1 for t in _tokens(sentence) if t not in _STOPWORDS) < _LINK_LINE_MAX_CONTENT


def _content_features(tokens: list[str]) -> Counter[str]:
    content = [t for t in tokens if t not in _STOPWORDS]
    feats: Counter[str] = Counter(content)
    feats.update(f"{a} {b}" for a, b in pairwise(content))
    return feats


def _tfidf_cosines(sentences: list[str]) -> list[float]:
    docs = [_content_features(_tokens(s)) for s in sentences]
    vocab: dict[str, int] = {}
    df: Counter[str] = Counter()
    for d in docs:
        for term in d:
            vocab.setdefault(term, len(vocab))
            df[term] += 1
    if not vocab:
        return [0.0] * (len(sentences) - 1)
    n = len(docs)
    idf = np.array([math.log((1 + n) / (1 + df[t])) + 1.0 for t in vocab], dtype=float)
    matrix = np.zeros((n, len(vocab)), dtype=float)
    for i, d in enumerate(docs):
        for term, count in d.items():
            matrix[i, vocab[term]] = count
    matrix *= idf
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    matrix /= norms[:, None]
    return [float(matrix[i] @ matrix[i + 1]) for i in range(n - 1)]


def _lcs_length(a: list[str], b: list[str]) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, start=1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def _frame_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if min(len(ta), len(tb)) < _FRAME_MIN_TOKENS:
        return 0.0
    return _lcs_length(ta, tb) / max(len(ta), len(tb))


def _embedding_pairs(sentences: list[str]) -> list[tuple[int, float]] | None:
    """(index, similarity) for each redundant adjacent pair on the embedding path."""
    try:
        emb = embed(tuple(_URL.sub(" ", s) for s in sentences))
        sims = [float(emb[i] @ emb[i + 1]) for i in range(len(sentences) - 1)]
    except Exception:
        return None
    links = [_is_link_line(s) for s in sentences]
    return [
        (i, s)
        for i, s in enumerate(sims)
        if s >= _EMBED_THRESHOLD and not (links[i] or links[i + 1])
    ]


def lexical_pairs(sentences: list[str]) -> list[tuple[int, float]]:
    """(index, similarity) for each adjacent pair that is lexically or structurally redundant."""
    if len(sentences) < 2:
        return []
    cosines = _tfidf_cosines(sentences)
    frames = [_frame_similarity(a, b) for a, b in pairwise(sentences)]
    links = [_is_link_line(s) for s in sentences]
    return [
        (i, max(c, f))
        for i, (c, f) in enumerate(zip(cosines, frames, strict=True))
        if (c >= _SIMILARITY_THRESHOLD or f >= _FRAME_THRESHOLD) and not (links[i] or links[i + 1])
    ]


def lexical_redundancy(sentences: list[str]) -> float:
    """Fraction of adjacent pairs that are lexically or structurally redundant (numpy path)."""
    if len(sentences) < 2:
        return 0.0
    return len(lexical_pairs(sentences)) / (len(sentences) - 1)


def _shingles(tokens: list[str]) -> frozenset[tuple[str, ...]]:
    return frozenset(tuple(tokens[i : i + _SHINGLE]) for i in range(len(tokens) - _SHINGLE + 1))


def repeated_sentences(sentences: list[str], eligible: list[bool]) -> list[tuple[int, int, float]]:
    """(later, earlier, alignment) for each eligible sentence repeating an earlier non-adjacent one.

    Each later sentence is reported once, against its closest earlier match. An inverted index
    from shingle to sentence keeps this near-linear: only sentences sharing a shingle are aligned.
    """
    index: dict[tuple[str, ...], list[int]] = {}
    tokens_of: dict[int, list[str]] = {}
    out: list[tuple[int, int, float]] = []
    for i, (text, ok) in enumerate(zip(sentences, eligible, strict=True)):
        tokens = _tokens(text)
        if not ok or len(tokens) < _REPEAT_MIN_TOKENS:
            continue
        mine = _shingles(tokens)
        candidates = {j for sh in mine for j in index.get(sh, ()) if j != i - 1}
        best: tuple[int, float] | None = None
        for j in sorted(candidates):
            other = tokens_of[j]
            ratio = _lcs_length(tokens, other) / max(len(tokens), len(other))
            if ratio >= _REPEAT_ALIGNMENT and (best is None or ratio > best[1]):
                best = (j, ratio)
        if best is not None:
            out.append((i, best[0], best[1]))
        tokens_of[i] = tokens
        for sh in mine:
            index.setdefault(sh, []).append(i)
    return out


class Redundancy:
    dimension = Dimension.redundancy

    def rule_ids(self) -> frozenset[str]:
        return _RULES

    def score_spans(self, doc: Document, profile: str, spans: list[Evidence]) -> float:
        # The adjacent term is a document fraction reported through at most _SUMMARY_LIMIT summary
        # spans, so it is recomputed rather than read off them; it counts while any of its
        # summary spans survives (disabling the rule removes them all).
        adjacent = 0.0
        if any(e.rule_id == RULE_ADJACENT_PAIR for e in spans):
            spans_in = _prose_sentences(doc)
            adjacent = len(_adjacent_pairs(spans_in)) / (len(spans_in) - 1)
        repeats = sum(1 for e in spans if e.rule_id == RULE_REPEATED_SENTENCE)
        return max(adjacent, saturating(repeats, _REPEAT_FULL_SCALE))

    def extract(self, doc: Document, profile: str) -> FeatureResult:
        spans_in = _prose_sentences(doc)
        sentences = [s.text for s in spans_in]
        if len(sentences) < 2:
            return FeatureResult(dimension=self.dimension, score=0.0, spans=[])

        pairs = _adjacent_pairs(spans_in)
        adjacent = len(pairs) / (len(sentences) - 1)

        spans: list[Evidence] = []
        for i, sim in sorted(pairs, key=lambda t: -t[1])[:_SUMMARY_LIMIT]:
            spans.append(
                doc.evidence(
                    rule_id=RULE_ADJACENT_PAIR,
                    severity=Severity.low,
                    clean_start=spans_in[i].start,
                    clean_end=spans_in[i + 1].end,
                    explanation=(
                        f"Adjacent sentences {sim:.2f} similar (redundancy {adjacent:.2f}: "
                        f"{len(pairs)} of {len(sentences) - 1} adjacent pairs)."
                    ),
                    kind=EvidenceKind.summary,
                )
            )

        eligible = [
            not doc.in_block_kind(s.start, _NON_PROSE)
            and not inside_quotes(doc.quoted, s.start, s.end)
            for s in spans_in
        ]
        repeats = repeated_sentences(sentences, eligible)
        for later, earlier, jac in repeats:
            # Anchored on the later copy only: a span covering both would swallow every finding
            # between them in the HTML report and change its baseline fingerprint on any edit.
            spans.append(
                doc.evidence(
                    rule_id=RULE_REPEATED_SENTENCE,
                    severity=Severity.low,
                    clean_start=spans_in[later].start,
                    clean_end=spans_in[later].end,
                    explanation=(
                        f"Repeats an earlier sentence ({jac:.0%} of words aligned): "
                        f'"{_opening(sentences[earlier])}". State it once.'
                    ),
                )
            )

        spans.sort(key=lambda e: e.start_char)
        # Same formula as score_spans over every span, without recomputing the adjacent pairs.
        score = max(adjacent, saturating(len(repeats), _REPEAT_FULL_SCALE))
        return FeatureResult(dimension=self.dimension, score=score, spans=spans)


def _opening(sentence: str, words: int = 8) -> str:
    head = sentence.split()
    return " ".join(head[:words]) + (" ..." if len(head) > words else "")


def _prose_sentences(doc: Document) -> list[TextSpan]:
    return [s for s in doc.sentences if s.text.strip()]


def _adjacent_pairs(spans_in: list[TextSpan]) -> list[tuple[int, float]]:
    sentences = [s.text for s in spans_in]
    if len(sentences) < 2:
        return []
    pairs: list[tuple[int, float]] | None = None
    if is_embeddings_available():
        pairs = _embedding_pairs(sentences)
    if pairs is None:
        pairs = lexical_pairs(sentences)
    return pairs


register(Redundancy())
