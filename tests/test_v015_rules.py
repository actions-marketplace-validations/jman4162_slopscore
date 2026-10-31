"""Rule fixes and additions from a reader's review of a long design document (v0.15)."""

from __future__ import annotations

import pytest

from slopscore import scan_text
from slopscore.config import Settings
from slopscore.core import SlopScorer, build_document
from slopscore.features.catalog import all_rule_ids
from slopscore.features.redundancy import (
    RULE_ADJACENT_PAIR,
    RULE_REPEATED_SENTENCE,
    Redundancy,
)
from slopscore.ingest.markdown import ingest_markdown


def _ids(text: str) -> set[str]:
    return {e.rule_id for e in scan_text(text).evidence}


# --- RESIDUE_KNOWLEDGE_CUTOFF: first-person assistant framing only ---------------------------


@pytest.mark.parametrize(
    "text",
    [
        "My knowledge cutoff is April 2024, so I cannot speak to later releases.",
        "My training data only goes up to early 2023.",
        "My knowledge extends to the end of 2022.",
        "My training data is current as of June 2024.",
    ],
)
def test_cutoff_fires_on_assistant_disclaimers(text: str) -> None:
    assert "RESIDUE_KNOWLEDGE_CUTOFF" in _ids(text)


@pytest.mark.parametrize(
    "text",
    [
        "Historical training data is sparse for this sensor type, so the model sees few faults.",
        "The training data is drawn from three hospitals and labelled by two radiologists.",
        "The model's knowledge cutoff is April 2024, according to the vendor's release notes.",
        "My training data is imbalanced, so I reweighted the minority class by a factor of 4.",
        "Knowledge cutoff dates differ between the two checkpoints we compared.",
    ],
)
def test_cutoff_stays_quiet_on_ml_prose(text: str) -> None:
    assert "RESIDUE_KNOWLEDGE_CUTOFF" not in _ids(text)


# --- RESIDUE_TEMPLATE_SLOT ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "The launch is planned for [X date] pending review.",
        "The program would save [$X] per year.",
        "We expect [N hosts] to move in the first wave.",
        "Margins improved by [XX%] after the change.",
        "Send the draft to [Company Name] for sign-off.",
        "The pilot found [XX] defects.",
    ],
)
def test_template_slot_fires(text: str) -> None:
    assert "RESIDUE_TEMPLATE_SLOT" in _ids(text)


@pytest.mark.parametrize(
    "text",
    [
        "As shown in [1], the method converges in 40 steps.",
        "He wrote that the plan was [sic] unworkable.",
        "The [X-ray] archive holds 3,000 films from 1950 onward.",
        "Louis [X] signed the treaty in 1315.",
        "Open questions are tracked separately [TBD] until the review.",
    ],
)
def test_template_slot_stays_quiet(text: str) -> None:
    assert "RESIDUE_TEMPLATE_SLOT" not in _ids(text)


def test_template_slot_ignores_task_list_boxes() -> None:
    md = "# Checklist\n\n- [x] wrote the spec\n- [X] ran the tests\n- [ ] shipped it\n"
    report = SlopScorer()._score(ingest_markdown(md))
    assert "RESIDUE_TEMPLATE_SLOT" not in {e.rule_id for e in report.evidence}


# --- PARALLEL_NOT_MERELY_BUT ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Our objective is not simply to build a capable parser, but to change how the team ships.",
        "The goal is not merely to cut cost, but to rethink the process.",
    ],
)
def test_not_simply_but_fires(text: str) -> None:
    assert "PARALLEL_NOT_MERELY_BUT" in _ids(text)


def test_not_just_but_is_left_alone() -> None:
    # Six human rows to two AI rows on the corpora; see the rule comment.
    assert "PARALLEL_NOT_MERELY_BUT" not in _ids("I miss not just the food, but the people.")


# --- FORMULAIC_LESSON_FRAME ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "The larger lesson is that small teams can move fast.",
        "This case illustrates how a process change can outlast a tool.",
        "This example underscores the importance of early review.",
        "We ran three pilots. Taken together, they point the same way.",
    ],
)
def test_lesson_frame_fires(text: str) -> None:
    assert "FORMULAIC_LESSON_FRAME" in _ids(text)


@pytest.mark.parametrize(
    "text",
    [
        "This example illustrates the use of a for loop over a list of 10 items.",
        "The key lesson from the 2019 outage was to page the on-call engineer sooner.",
        "This case shows the bracket failing at 40 kN.",
    ],
)
def test_lesson_frame_stays_quiet(text: str) -> None:
    assert "FORMULAIC_LESSON_FRAME" not in _ids(text)


# --- Redundancy: link lines and document-wide repeats ----------------------------------------

_REPEATED = (
    "The migration moved every reporting job off the legacy scheduler and onto the shared "
    "queue in under one quarter."
)
_FILLER = [
    "The first wave covered 40 jobs owned by the finance team.",
    "Two jobs failed on the first run because of a missing credential.",
    "The second wave covered the remaining 85 jobs over six weeks.",
    "Run time fell from 50 minutes to 12 minutes on the largest job.",
]


def _redundancy(text: str) -> tuple[float, list[str]]:
    result = Redundancy().extract(build_document(ingest_markdown(text)), "blog")
    return result.score, [e.rule_id for e in result.spans]


def test_adjacent_link_lines_are_not_redundant() -> None:
    md = (
        "We measured 41 jobs over 7 days and moved 32 of them before the review.\n\n"
        "[Runbook](https://wiki.example.com/team/projects/migration/runbook-v2)\n\n"
        "[Weekly dashboard](https://wiki.example.com/team/projects/migration/metrics-weekly)\n\n"
        "[Link](https://wiki.example.com/team/projects/migration/notes-a)\n\n"
        "[Link](https://wiki.example.com/team/projects/migration/notes-b)\n\n"
        "The second cohort had 19 jobs and 11 moved within a week of triage.\n"
    )
    _, rules = _redundancy(md)
    assert RULE_ADJACENT_PAIR not in rules


def test_repeated_sentence_fires_once_on_the_later_copy() -> None:
    text = " ".join([_REPEATED, *_FILLER, _REPEATED])
    doc = build_document(ingest_markdown(text))
    result = Redundancy().extract(doc, "blog")
    repeats = [e for e in result.spans if e.rule_id == RULE_REPEATED_SENTENCE]
    assert len(repeats) == 1
    assert repeats[0].start_char > len(_REPEATED)  # the later copy, not the first
    assert repeats[0].span.strip() == _REPEATED
    assert result.score == pytest.approx(0.25)


def test_near_repeat_with_one_word_changed_fires() -> None:
    edited = _REPEATED.replace("under one quarter", "under a quarter")
    _, rules = _redundancy(" ".join([_REPEATED, *_FILLER, edited]))
    assert RULE_REPEATED_SENTENCE in rules


def test_short_or_adjacent_repeats_are_not_document_repeats() -> None:
    short = "The results are shown below."
    _, rules = _redundancy(" ".join([short, *_FILLER, short]))
    assert RULE_REPEATED_SENTENCE not in rules
    _, rules = _redundancy(" ".join([*_FILLER, _REPEATED, _REPEATED]))
    assert RULE_REPEATED_SENTENCE not in rules  # adjacent: REDUNDANT_ADJACENT_PAIR's job


def test_repeated_list_items_and_headings_do_not_count() -> None:
    item = f"- {_REPEATED}\n"
    md = "# Plan\n\n" + item + "\n".join(_FILLER) + "\n\n## Later\n\n" + item
    _, rules = _redundancy(md)
    assert RULE_REPEATED_SENTENCE not in rules


def test_disabling_the_repeat_rule_removes_its_points() -> None:
    text = " ".join([_REPEATED, *_FILLER, _REPEATED] * 1)
    on = SlopScorer().scan_text(text)
    off = SlopScorer(
        settings=Settings(disabled_rules=frozenset({RULE_REPEATED_SENTENCE}))
    ).scan_text(text)
    assert on.dimensions.redundancy > 0.0
    assert off.dimensions.redundancy == 0.0


def test_redundancy_rules_are_suppressible_by_name() -> None:
    assert {RULE_ADJACENT_PAIR, RULE_REPEATED_SENTENCE} <= all_rule_ids()
