"""Run the committed benchmark (+ any cached external slices) and write eval/results.json.

Reproduces the numbers in eval/RESULTS.md. The committed benchmark is in-sample (it overlaps the
seed the model trained on); the cached Wikipedia AI-Cleanup slice is held-out and eval-only.

Run: python scripts/eval/report.py
"""

from __future__ import annotations

import json
from pathlib import Path

from slopscore.eval.datasets import load_jsonl
from slopscore.eval.harness import evaluate, should_promote

CACHE = Path.home() / ".cache" / "slopscore"


def _display(path: Path) -> str:
    """Repo-relative or ~-relative, so the committed results never record a local home path."""
    root = Path(__file__).resolve().parents[2]
    for base, prefix in ((root, ""), (Path.home(), "~/")):
        try:
            return prefix + str(path.resolve().relative_to(base))
        except ValueError:
            continue
    return path.name


def _run(path: Path, name: str, eval_only: bool) -> dict:
    rows = load_jsonl(path)
    out = {"name": name, "path": _display(path), "eval_only": eval_only, "n": len(rows)}
    for kind in ("rules", "ml"):
        out[kind] = evaluate(rows, profile="blog", scorer=kind)
    out["promote_ml"] = should_promote(out["rules"], out["ml"])
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    results = [_run(root / "eval" / "datasets" / "benchmark.jsonl", "benchmark", eval_only=False)]
    longform = root / "eval" / "datasets" / "longform.jsonl"
    if longform.exists():
        results.append(_run(longform, "longform (300+ words, eval-only)", eval_only=True))
    # Optional cached slices. The dated Wikipedia slice comes from `fetch.py wiki_aicleanup --since
    # 2026-07 --full`; the generated one from `prompts.py import`.
    for name, label in (
        ("wiki_aicleanup", "wiki_aicleanup (held-out, eval-only)"),
        ("wiki_aicleanup_since2026-07", "wiki_aicleanup tagged since 2026-07 (eval-only)"),
        ("generated_2026", "generated 2026 matched pairs (eval-only)"),
    ):
        path = CACHE / f"{name}.jsonl"
        if path.exists():
            results.append(_run(path, label, eval_only=True))

    out = root / "eval" / "results.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for r in results:
        rm, mm = r["rules"]["metrics"], r["ml"]["metrics"]
        print(f"\n## {r['name']}  (n={r['n']})")
        print(
            f"  rules: AUROC={rm['auroc']:.3f} PR-AUC={rm['pr_auc']:.3f} "
            f"TPR@1%FPR={rm['tpr_at_1fpr']:.3f} ECE={rm['ece']:.3f}"
        )
        print(
            f"  ml   : AUROC={mm['auroc']:.3f} PR-AUC={mm['pr_auc']:.3f} "
            f"TPR@1%FPR={mm['tpr_at_1fpr']:.3f} ECE={mm['ece']:.3f}"
        )
        for g, gv in r["rules"]["fairness"].items():
            mv = r["ml"]["fairness"].get(g, {})
            print(
                f"    [{g}] n={gv['n']} rules_FPR={gv['fpr']:.2f} ml_FPR={mv.get('fpr', float('nan')):.2f}"
            )
        print(f"  promote ml -> default: {r['promote_ml']}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
