"""
Fetch VCEP specifications from ClinGen CSpec API for 3 pilot genes.

Confirmed spec IDs:
  - BRCA1: GN092           (ENIGMA BRCA1/2 v1.2)
  - TP53:  GN009           (TP53 VCEP v2.4)
  - MLH1:  1564688410      (InSiGHT Hereditary CRC/Polyposis)

API returns JSON-LD. Criteria live at:
    doc["ruleSets"][i]["criteriaCodes"][]
Each rule set has a "genes" field identifying which gene it applies to.
"""
import json
import time
from pathlib import Path
import httpx

CSPEC_BASE = "https://cspec.genome.network/cspec/api"

# Confirmed spec IDs and the target gene for each
TARGET_SPECS = {
    "BRCA1": {"spec_id": "GN092", "vcep": "ENIGMA BRCA1/2", "target_gene": "BRCA1"},
    "TP53":  {"spec_id": "GN009", "vcep": "TP53 VCEP", "target_gene": "TP53"},
    "MLH1":  {"spec_id": "1564688410", "vcep": "InSiGHT MMR", "target_gene": "MLH1"},
}

OUTPUT = Path(__file__).parent.parent / "app" / "data" / "vcep_specs.json"


def fetch_spec(spec_id: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = httpx.get(
                f"{CSPEC_BASE}/SequenceVariantInterpretation/id/{spec_id}",
                params={"detail": "high"},
                timeout=120.0,
            )
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code} (attempt {attempt+1})")
        except Exception as e:
            print(f"  {type(e).__name__} (attempt {attempt+1})")
        time.sleep(4)
    return None


def extract_criteria_for_gene(doc: dict, target_gene: str) -> list[dict]:
    """Find the rule set for target_gene and extract its criteria."""
    rule_sets = doc.get("ruleSets") or []

    for rs in rule_sets:
        genes = [g.get("label") for g in (rs.get("genes") or [])]
        if target_gene not in genes:
            continue

        # Found the matching rule set
        criteria = []
        for code in rs.get("criteriaCodes", []):
            label = code.get("label")
            if not label:
                continue

            strengths = []
            applicable_strengths = []
            for s in code.get("evidenceStrengths", []):
                app = (s.get("applicability") or "").lower()
                is_applicable = "applicable" in app and "not" not in app
                entry = {
                    "strength": s.get("label"),
                    "applicable": is_applicable,
                    "description": s.get("description", ""),
                }
                strengths.append(entry)
                if is_applicable:
                    applicable_strengths.append(entry["strength"])

            criteria.append({
                "criterion_code": label,
                "description": code.get("description", ""),
                "strengths": strengths,
                "applicable_strengths": applicable_strengths,
            })

        return criteria

    return []


def extract_metadata(doc: dict) -> dict:
    return {
        "spec_label": doc.get("label"),
        "spec_version": (doc.get("label") or "").split("Version")[-1].strip() if "Version" in (doc.get("label") or "") else "1.0",
        "cspec_status": doc.get("cspecStatus"),
        "last_updated": doc.get("lastUpdated"),
        "affiliation": doc.get("affiliation", {}).get("label"),
    }


def main():
    print("Fetching VCEP specifications from ClinGen CSpec...")
    print()

    specs = []
    for gene, meta in TARGET_SPECS.items():
        print(f"{gene} <- {meta['spec_id']} ({meta['vcep']})")
        doc = fetch_spec(meta["spec_id"])
        if not doc:
            print(f"  FAILED after retries")
            continue

        criteria = extract_criteria_for_gene(doc, meta["target_gene"])
        metadata = extract_metadata(doc)

        specs.append({
            "gene": gene,
            "vcep_name": meta["vcep"],
            "spec_version": metadata["spec_version"],
            "spec_label": metadata["spec_label"],
            "cspec_id": meta["spec_id"],
            "last_updated": metadata["last_updated"],
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "criteria": criteria,
        })
        print(f"  extracted {len(criteria)} criteria for {meta['target_gene']}")

        for c in criteria[:5]:
            print(f"    {c['criterion_code']}: {c['applicable_strengths']}")

        time.sleep(1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(specs, indent=2))
    print()
    print(f"Wrote {OUTPUT} ({len(specs)} specs)")


if __name__ == "__main__":
    main()
