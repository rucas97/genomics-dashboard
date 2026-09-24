"""
Validation runner for the GenomicsOps ACMG engine.
Compares engine output against a corpus of expert-classified variants.

Usage:
    python -m tests.validation.run_validation
    python -m tests.validation.run_validation --json  # machine-readable output
"""
import json
import sys
from pathlib import Path
from app.services.acmg import classify_variant


CORPUS_PATH = Path(__file__).parent / "clingen_corpus.json"


def load_corpus() -> list[dict]:
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return data["variants"]


def run_validation(verbose: bool = True) -> dict:
    variants = load_corpus()
    results = []
    passed = 0
    failed = 0
    errors = 0

    for v in variants:
        try:
            result = classify_variant(v)
            engine_class = result["classification"]
            expected = v["expected_classification"]
            match = engine_class == expected

            results.append({
                "id": v["id"],
                "gene": v.get("gene"),
                "expected": expected,
                "engine": engine_class,
                "match": match,
                "criteria": [c["code"] for c in result.get("criteria_fired", [])],
                "engine_version": result.get("engine_version"),
            })

            if match:
                passed += 1
            else:
                failed += 1

            if verbose:
                status = "✓" if match else "✗"
                print(f"  {status} {v['id']:<30} expected={expected:<20} engine={engine_class}")
                if not match:
                    print(f"      criteria: {[c['code'] for c in result.get('criteria_fired', [])]}")

        except Exception as e:
            errors += 1
            if verbose:
                print(f"  ! {v['id']:<30} ERROR: {e}")
            results.append({
                "id": v["id"],
                "error": str(e),
                "match": False,
            })

    total = len(variants)
    agreement = (passed / total * 100) if total else 0

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "agreement_pct": round(agreement, 1),
        "results": results,
    }

    if verbose:
        print()
        print("=" * 60)
        print(f"  Validation Result")
        print("=" * 60)
        print(f"  Total variants:    {total}")
        print(f"  Agreement:         {passed}/{total} ({agreement:.1f}%)")
        print(f"  Disagreements:     {failed}")
        print(f"  Errors:            {errors}")
        print()

        # Classification breakdown
        by_expected = {}
        for r in results:
            if "expected" in r:
                exp = r["expected"]
                by_expected.setdefault(exp, {"total": 0, "match": 0})
                by_expected[exp]["total"] += 1
                if r["match"]:
                    by_expected[exp]["match"] += 1

        print("  By expected classification:")
        for cls, counts in sorted(by_expected.items()):
            pct = counts["match"] / counts["total"] * 100
            print(f"    {cls:<25} {counts['match']}/{counts['total']} ({pct:.0f}%)")

        print()

    return summary


def main():
    verbose = "--json" not in sys.argv
    summary = run_validation(verbose=verbose)

    if "--json" in sys.argv:
        print(json.dumps(summary, indent=2))
    else:
        # Exit non-zero if agreement is below 80% (CI gate)
        if summary["agreement_pct"] < 80:
            sys.exit(1)


if __name__ == "__main__":
    main()
