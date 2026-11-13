# Limitations & authorship

## slopscore is not an AI detector

It flags writing **patterns**, not provenance. A high score means the text is dense with
formulaic, generic, low-specificity, over-polished patterns, which occur in low-effort AI output
**and** in plenty of human writing (marketing copy, SEO, fan fiction). It scores **text**, not
**authors**, and must never be used to accuse anyone.

## Known limitations

- **Non-native English / plain writing** is over-flagged by pattern detectors (one study found
  ~61% false positives on non-native essays). slopscore mitigates with a corroboration gate, a
  negative human-writing signal, and abstention, but residual risk remains.
- **Short text** (< ~300 words) is unreliable; under ~100 words the label abstains.
- **Genre** matters: marketing and travel prose naturally resemble slop. Use `--profile`.
- **Light paraphrasing** evades pattern matching, as it does all detectors.
- **The rules age with the models.** Most rules were written from 2023-25 model output, and the
  newest models drop many of those habits (em dashes, "delve", "In summary"). On Wikipedia
  articles tagged as suspected AI text from July 2026 on, the rules do no better than chance.
  See `MODEL_CARD.md` for the numbers.
- **A low score does not mean a document is ready.** slopscore scores phrases, sentences, and
  Markdown block shapes. It does not judge document structure: whether a thesis is restated in
  every section, whether the evidence comes before or after the framing, or whether a headline
  figure is ever derived. A reader found a 5,000-word design document inflated and repetitive
  after it scored under 10. [Patterns slopscore does not score](unscored-patterns.md) lists
  what to check by hand.

See the project `MODEL_CARD.md` for measured numbers and the real-corpus (MAGE) experiment.

## Authorship signal (optional, separate, caveated)

slopscore ships **no** authorship detector. Every candidate (Binoculars, Fast-DetectGPT, GLTR)
collapses on paraphrase, is biased against non-native English, or is academic-only; watermark
detection covers almost no models. What it offers instead is a pluggable adapter
(`slopscore.detectors.AuthorshipDetector`) behind the `[detectors]` extra: if you bring your own
detector, its result is reported in a **separate** field with a mandatory caveat and is **never**
folded into the SlopScore. `slopscore-lint scan --detector reference` wires a no-op example to show the
separation. This is for curiosity, not accusation.
