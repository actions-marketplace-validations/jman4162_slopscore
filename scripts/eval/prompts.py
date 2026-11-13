"""Prompt pack for a hand-generated 2026 AI slice (eval-only, never committed as data).

Every cached corpus predates the mid-2026 patterns Wikipedia's AI Cleanup project now lists as
most common, so new rules could be measured only for false-positive cost. This pack gets
current-model text without API keys: ``render`` prints one prompt per source article for a person
to paste into each chat model, and ``import`` reads the saved replies into a labelled JSONL.

The design follows Graphite's 2026 "AI Tells" study. Each prompt carries a topic and terse fact
notes written from a human article (``prompt_pack.json``), never the article's own wording, and
asks for a matched length with no style instruction, so the model's default register shows.
``import --with-human`` also writes the source articles as label-0 rows, giving matched pairs.

    python scripts/eval/prompts.py render > prompts.md
    # save each reply as <dir>/<model>/<id>.md, e.g. ~/gen2026/claude-opus-5-5/fw119.md
    python scripts/eval/prompts.py import ~/gen2026 --with-human
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CACHE = Path.home() / ".cache" / "slopscore"
PACK = Path(__file__).with_name("prompt_pack.json")
OUT_NAME = "generated_2026"
_SUFFIXES = (".md", ".txt")
# A reply this far under its target was probably cut off or refused; it is reported, not kept.
_MIN_FRACTION = 0.5


def _pack() -> dict:
    return json.loads(PACK.read_text(encoding="utf-8"))


def prompt_for(item: dict, template: str) -> str:
    notes = "\n".join(f"- {n}" for n in item["notes"])
    return template.format(words=item["words"], topic=item["topic"], notes=notes)


def render() -> str:
    pack = _pack()
    parts = [
        "# slopscore 2026 prompt pack",
        "",
        f"{len(pack['items'])} prompts. Paste each into a new chat with no custom instructions,",
        "memory, or style settings, and save the reply exactly as given (keep any preamble or",
        "Markdown) as `<dir>/<model>/<id>.md`. Use one folder per model, named for the model",
        "and version the chat showed (e.g. `gpt-6`, `claude-opus-5-5`, `gemini-3-1-pro`).",
        "",
    ]
    for item in pack["items"]:
        parts += [f"## {item['id']}", "", "```text", prompt_for(item, pack["template"]), "```", ""]
    return "\n".join(parts)


def _source_rows(name: str) -> list[dict]:
    path = CACHE / f"{name}.jsonl"
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def import_replies(root: Path, with_human: bool) -> Path:
    items = {i["id"]: i for i in _pack()["items"]}
    rows: list[dict] = []
    skipped: list[str] = []
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(model_dir.iterdir()):
            if path.suffix not in _SUFFIXES or path.stem not in items:
                continue
            item = items[path.stem]
            text = path.read_text(encoding="utf-8").strip()
            words = len(text.split())
            if words < _MIN_FRACTION * item["words"]:
                skipped.append(f"{model_dir.name}/{path.name} ({words} words)")
                continue
            rows.append(
                {
                    "text": text,
                    "label": 1,
                    "bucket": "raw_llm",
                    "subgroup": f"gen2026_{model_dir.name}",
                    "model": model_dir.name,
                    "source_id": item["id"],
                    "target_words": item["words"],
                    "word_count": words,
                }
            )
    if with_human:
        cache: dict[str, list[dict]] = {}
        for item in items.values():
            src = cache.setdefault(item["source"], _source_rows(item["source"]))
            text = src[item["row"]]["text"]
            rows.append(
                {
                    "text": text,
                    "label": 0,
                    "bucket": "human_good",
                    "subgroup": "gen2026_human",
                    "source_id": item["id"],
                    "word_count": len(text.split()),
                }
            )
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{OUT_NAME}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    ai = sum(r["label"] for r in rows)
    print(f"[{OUT_NAME}] wrote {len(rows)} rows ({ai} AI, {len(rows) - ai} human) to {out}")
    for s in skipped:
        print(f"  skipped (under {_MIN_FRACTION:.0%} of target): {s}", file=sys.stderr)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("render", help="print every prompt as one Markdown document")
    imp = sub.add_parser("import", help="read <dir>/<model>/<id>.md replies into the cache")
    imp.add_argument("root", type=Path)
    imp.add_argument("--with-human", action="store_true", help="add the matched source articles")
    args = ap.parse_args()
    if args.cmd == "render":
        print(render())
    else:
        import_replies(args.root.expanduser(), args.with_human)


if __name__ == "__main__":
    main()
