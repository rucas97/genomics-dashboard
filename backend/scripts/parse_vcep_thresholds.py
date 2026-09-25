"""
Parse threshold values from VCEP criterion descriptions.

Reads app/data/vcep_specs.json, extracts machine-readable thresholds,
and writes app/data/vcep_thresholds.json.

Handles multiple description patterns across VCEPs:
- "FAF > 0.0001"
- "AF is above 0.01%"
- "GnomAD v4 Grpmax filtering allele frequency >= 0.001 (0.1%)"
- "SpliceAI >= 0.2"
- "BayesDel no-AF score >= 0.28"
- "LR >= 18.7:1"
- ">= 4 points"
- "average read depth >= 25"

Also records criteria the VCEP explicitly disabled (applicable_strengths: []).
"""
import json
import re
from pathlib import Path

CACHE = Path(__file__).parent.parent / "app" / "data" / "vcep_specs.json"
OUTPUT = Path(__file__).parent.parent / "app" / "data" / "vcep_thresholds.json"


# --- Regex patterns for threshold extraction ---

AF_PATTERN = re.compile(
    r"(?:FAF|AF|gnomAD\s+AF|filter\s+allele\s+frequency)\s*"
    r"(≥|>=|>|≤|<=|<)\s*"
    r"([0-9]*\.?[0-9]+(?:[eE]-?[0-9]+)?)\s*%?",
    re.IGNORECASE,
)

AF_ABOVE_PATTERN = re.compile(
    r"(?:AF|FAF|filter\s+allele\s+frequency)\s+is\s+"
    r"(above|greater than|below|less than|at or above|at or below)\s+"
    r"([0-9]*\.?[0-9]+)\s*%",
    re.IGNORECASE,
)

SPLICEAI_PATTERN = re.compile(
    r"SpliceAI\s*(≥|>=|>|≤|<=|<)\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)

BAYESDEL_PATTERN = re.compile(
    r"BayesDel[^.]*?(≥|>=|>|≤|<=|<)\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)

LR_PATTERN = re.compile(
    r"LR\s*(≥|>=|>|≤|<=|<)\s*([0-9]*\.?[0-9]+):1",
    re.IGNORECASE,
)

READ_DEPTH_PATTERN = re.compile(
    r"read\s+depth\s*(≥|>=|>|≤|<=|<)\s*([0-9]+)",
    re.IGNORECASE,
)

# MLH1 / InSiGHT style: "GnomAD v4 Grpmax filtering allele frequency >= 0.001 (0.1%)"
GRPMAX_PATTERN = re.compile(
    r"Grpmax\s+filtering\s+allele\s+frequency\s*"
    r"(≥|>=|>|≤|<=|<)\s*"
    r"([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)

# Points-based: ">= 4 points" or "2 - 3.5 points"
POINTS_PATTERN = re.compile(
    r"(≥|>=|>|≤|<=|<)\s*([0-9]*\.?[0-9]+)\s*points?",
    re.IGNORECASE,
)

# Generic ">= X%" for BA1-style thresholds (fallback)
PERCENT_PATTERN = re.compile(
    r"(≥|>=|>|≤|<=|<)\s*([0-9]*\.?[0-9]+)\s*%",
    re.IGNORECASE,
)


def normalize_operator(op: str) -> str:
    """Normalize unicode ≥ ≤ variants to ascii."""
    return op.replace("≥", ">=").replace("≤", "<=").replace("≧", ">=").replace("≦", "<=")


def extract_thresholds(description: str) -> list[dict]:
    """Extract every threshold expression from a description string."""
    if not description:
        return []

    results = []

    # AF/FAF with numeric value
    for m in AF_PATTERN.finditer(description):
        op, value = m.group(1), m.group(2)
        tail = description[m.end():m.end() + 1]
        is_pct = tail == "%"
        try:
            threshold = float(value)
            if is_pct and threshold > 1:
                threshold = threshold / 100
            results.append({
                "type": "af",
                "operator": normalize_operator(op),
                "threshold": threshold,
            })
        except ValueError:
            continue

    # "AF is above 0.01%"
    for m in AF_ABOVE_PATTERN.finditer(description):
        word, value = m.group(1).lower(), m.group(2)
        op = ">" if ("above" in word or "greater" in word) else "<"
        try:
            results.append({
                "type": "af",
                "operator": op,
                "threshold": float(value) / 100,
            })
        except ValueError:
            continue

    # SpliceAI
    for m in SPLICEAI_PATTERN.finditer(description):
        try:
            results.append({
                "type": "spliceai",
                "operator": normalize_operator(m.group(1)),
                "threshold": float(m.group(2)),
            })
        except ValueError:
            continue

    # BayesDel
    for m in BAYESDEL_PATTERN.finditer(description):
        try:
            results.append({
                "type": "bayesdel",
                "operator": normalize_operator(m.group(1)),
                "threshold": float(m.group(2)),
            })
        except ValueError:
            continue

    # LR (likelihood ratio)
    for m in LR_PATTERN.finditer(description):
        try:
            results.append({
                "type": "lr",
                "operator": normalize_operator(m.group(1)),
                "threshold": float(m.group(2)),
            })
        except ValueError:
            continue

    # Read depth
    for m in READ_DEPTH_PATTERN.finditer(description):
        try:
            results.append({
                "type": "read_depth",
                "operator": normalize_operator(m.group(1)),
                "threshold": int(m.group(2)),
            })
        except ValueError:
            continue

    # Grpmax filtering AF (MLH1 / InSiGHT style)
    for m in GRPMAX_PATTERN.finditer(description):
        try:
            results.append({
                "type": "af",
                "operator": normalize_operator(m.group(1)),
                "threshold": float(m.group(2)),
            })
        except ValueError:
            continue

    # Points-based (MLH1 PM3)
    for m in POINTS_PATTERN.finditer(description):
        try:
            results.append({
                "type": "points",
                "operator": normalize_operator(m.group(1)),
                "threshold": float(m.group(2)),
            })
        except ValueError:
            continue

    # Standalone percentages (fallback)
    if not results:
        for m in PERCENT_PATTERN.finditer(description):
            try:
                pct = float(m.group(2))
                results.append({
                    "type": "af",
                    "operator": normalize_operator(m.group(1)),
                    "threshold": pct / 100 if pct > 1 else pct,
                })
            except ValueError:
                continue

    return results


def main():
    if not CACHE.exists():
        print(f"Missing {CACHE}")
        return

    specs = json.loads(CACHE.read_text())
    output = {}

    for spec in specs:
        gene = spec["gene"]
        vcep_name = spec["vcep_name"]
        spec_version = spec["spec_version"]

        print(f"\n=== {gene} ({vcep_name} v{spec_version}) ===")

        gene_output = {
            "gene": gene,
            "vcep_name": vcep_name,
            "spec_version": spec_version,
            "cspec_id": spec.get("cspec_id"),
            "criteria": {},
        }

        for crit in spec["criteria"]:
            code = crit["criterion_code"]

            applicable = []
            for s in crit["strengths"]:
                if not s.get("applicable"):
                    continue
                thresholds = extract_thresholds(s.get("description", ""))
                if thresholds:
                    applicable.append({
                        "strength": s["strength"],
                        "thresholds": thresholds,
                    })

            crit_thresholds = extract_thresholds(crit.get("description", ""))

            if applicable or crit_thresholds:
                gene_output["criteria"][code] = {
                    "applicable_strengths": crit["applicable_strengths"],
                    "strength_thresholds": applicable,
                    "criterion_thresholds": crit_thresholds,
                }
                n_thresholds = sum(len(a["thresholds"]) for a in applicable) + len(crit_thresholds)
                print(f"  {code}: {n_thresholds} thresholds extracted")
            elif not crit["applicable_strengths"]:
                # VCEP explicitly disabled this criterion
                gene_output["criteria"][code] = {
                    "applicable_strengths": [],
                    "suppressed": True,
                    "reason": "VCEP marked all strengths Not Applicable",
                }
                print(f"  {code}: SUPPRESSED by VCEP")

        output[gene] = gene_output

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2))
    print()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
