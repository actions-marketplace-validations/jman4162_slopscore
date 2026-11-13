"""Rules from the October 2026 WP:AISIGNS revision and Graphite's 2026 study (v0.16)."""

from __future__ import annotations

import pytest

from slopscore import scan_text


def _ids(text: str) -> set[str]:
    return {e.rule_id for e in scan_text(text).evidence if not e.is_summary}


@pytest.mark.parametrize(
    ("rule", "text"),
    [
        ("RESIDUE_TEMPLATE_SLOT", "The company was founded in [Year] by [Founder Names]."),
        ("RESIDUE_TEMPLATE_SLOT", "Best regards, [Your Name]"),
        ("RESIDUE_TEMPLATE_SLOT", "Write to me at [Your Email Address] with questions."),
        ("RESIDUE_TEMPLATE_SLOT", "My articles include [Article Title 1] and [Article Title 2]."),
        ("RESIDUE_TEMPLATE_SLOT", "It is my favourite because [brief reason]."),
        ("RESIDUE_TEMPLATE_SLOT", "See the revised draft [link to the revised article]."),
        ("RESIDUE_TEMPLATE_SLOT", "Official channel: (Add your channel URL here)"),
        ("RESIDUE_TEMPLATE_SLOT", "The page was accessed on 2025-XX-XX for this entry."),
        ("RESIDUE_TEMPLATE_SLOT", "url=INSERT_SOURCE_URL_30 publisher=SOURCE_PUBLISHER"),
        ("RESIDUE_TEMPLATE_SLOT", "Listen at PASTE_SPOTIFY_TRACK_URL_HERE today."),
        ("RESIDUE_VENDOR_MARKUP", "See https://example.org/story?utm_source=openai for more."),
        ("RESIDUE_VENDOR_MARKUP", "See https://example.org/story?utm_source=copilot.com now."),
        ("RESIDUE_VENDOR_MARKUP", "See https://example.org/story?referrer=grok.com now."),
        ("RESIDUE_FOOTNOTE_ARROW", "Annual report, 2024. https://example.org ↩ ↩2"),
        ("RESIDUE_BELOW_IS", "Below is a detailed overview of the program and its history."),
        ("RESIDUE_BELOW_IS", "Here is a comprehensive breakdown of the costs."),
        ("RESIDUE_LIMITED_INFORMATION", "Her role in the resistance isn't widely documented."),
        ("RESIDUE_LIMITED_INFORMATION", "The fauna is limited in the provided search results."),
        ("RESIDUE_LIMITED_INFORMATION", "He keeps his personal life private."),
        ("RESIDUE_LIMITED_INFORMATION", "My analysis is based on the available track titles."),
        ("FORMULAIC_DESPITE_CHALLENGES", "The town faces several challenges typical of cities."),
        ("FORMULAIC_LESSON_FRAME", "We ran three pilots. Together, these point the same way."),
        ("FORMULAIC_MODEL_TRANSITION", "The new wing adds another dimension to the museum."),
        ("INSIGHT_MATTERS_BECAUSE", "This matters because the two programs are funded apart."),
        ("INSIGHT_MATTERS_BECAUSE", "The order matters more than the speed of each step."),
        ("SIGNIF_SINGLE_MOST", "The single most important factor was the rain."),
        ("PARALLEL_IS_NOT_SIMPLY", "The festival is not simply a market for local farms."),
        ("PARALLEL_LESS_ABOUT_MORE_ABOUT", "It is less like a library and more like a framework."),
        ("CANDOR_IS_GENUINELY", "This is genuinely the hard part of the migration."),
        ("META_REVISION_DELTA", "What holds up: the trend. What was wrong: the cause."),
        ("META_REVISION_DELTA", "The claim does not survive contact with the source data."),
    ],
)
def test_v016_rules_fire(rule: str, text: str) -> None:
    assert rule in _ids(text), _ids(text)


@pytest.mark.parametrize(
    ("rule", "text"),
    [
        # Reddit link labels: the reason slot names are an explicit list.
        ("RESIDUE_TEMPLATE_SLOT", "Please [read through our rules] and [message us] first."),
        ("RESIDUE_TEMPLATE_SLOT", "The INSERT_USER constant was added to the 1999 schema."),
        ("RESIDUE_TEMPLATE_SLOT", "The meeting is on 2025-10-14 at the town hall."),
        ("RESIDUE_BELOW_IS", "Below is a list of the 2019 results by county."),
        ("RESIDUE_BELOW_IS", "The table below is a detailed overview of 2019."),  # not line-initial
        ("RESIDUE_LIMITED_INFORMATION", "The drug was not widely available in 1950."),
        ("RESIDUE_LIMITED_INFORMATION", "The reclusive author maintains a low profile."),
        ("INSIGHT_MATTERS_BECAUSE", "Health matters more than wealth, my grandmother said."),
        ("FORMULAIC_MODEL_TRANSITION", "Ultimately, the council voted 5 to 2 against it."),
        ("PARALLEL_IS_NOT_SIMPLY", "It is not simply cost, but trust."),  # NOT_MERELY_BUT's span
        ("CANDOR_IS_GENUINELY", "The result is genuinely interesting."),  # SINCERITY_COLLOCATION's
        ("META_REVISION_DELTA", "No plan survives contact with the enemy, and ours did not."),
        ("META_REVISION_DELTA", "This plan does not survive contact with the enemy."),
    ],
)
def test_v016_rules_stay_quiet(rule: str, text: str) -> None:
    assert rule not in _ids(text), _ids(text)


def test_widened_rules_do_not_double_charge() -> None:
    assert _ids("It is not simply cost, but trust.") >= {"PARALLEL_NOT_MERELY_BUT"}
    assert "PARALLEL_IS_NOT_SIMPLY" not in _ids("It is not simply cost, but trust.")
    ids = _ids("The result is genuinely interesting.")
    assert "CANDOR_SINCERITY_COLLOCATION" in ids and "CANDOR_IS_GENUINELY" not in ids
