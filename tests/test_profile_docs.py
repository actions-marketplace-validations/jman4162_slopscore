"""The profile table in docs/configuration.md matches scoring/profiles.py (v0.15)."""

from __future__ import annotations

from pathlib import Path

from slopscore.models import Dimension
from slopscore.scoring.profiles import PROFILES

_DOC = Path(__file__).resolve().parents[1] / "docs" / "configuration.md"


def _table() -> dict[str, dict[Dimension, float]]:
    lines = _DOC.read_text(encoding="utf-8").splitlines()
    start = lines.index("## What each profile changes")
    rows = [line for line in lines[start:] if line.startswith("|")]
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    profiles = header[1:]
    table: dict[str, dict[Dimension, float]] = {p: {} for p in profiles}
    for row in rows[2:]:
        cells = [c.strip() for c in row.strip("|").split("|")]
        dim = Dimension(cells[0])
        for profile, cell in zip(profiles, cells[1:], strict=True):
            if cell:
                table[profile][dim] = float(cell)
    return table


def test_profile_table_matches_code() -> None:
    table = _table()
    assert set(table) == set(PROFILES)
    for profile, multipliers in PROFILES.items():
        expected = {d: m for d, m in multipliers.items() if m != 1.0}
        assert table[profile] == expected, profile
