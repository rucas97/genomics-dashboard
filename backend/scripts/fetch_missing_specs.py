"""
Find and fetch specs for BRCA2 and CFTR.
Searches the full spec list for matching gene labels.
Retries on timeouts.
"""
import json
import time
import httpx
from pathlib import Path

BASE = "https://cspec.genome.network/cspec/api"
CACHE = Path(__file__).parent.parent / "app" / "data" / "vcep_specs.json"
INDEX = Path(__file__).parent.parent / "app" / "data" / "cspec_index.json"


def fetch_with_retry(url, params=None, retries=4, timeout=120.0):
    for attempt in range(retries):
        try:
            r = httpx.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            print(f"    HTTP {r.status_code} (attempt {attempt+1})")
        except Exception as e:
            print(f"    {type(e).__name__} (attempt {attempt+1})")
        time.sleep(4)
    return None


def find_spec_by_gene(target_gene: str) -> str | None:
    """Search the full spec list for one matching target_gene."""
    print(f"  Listing all specs...")
    data = fetch_with_retry(
        f"{BASE}/SequenceVariantInterpretation/id",
        params={"detail": "low", "pgSize": 250, "pg": 1},
        timeout=180.0,
    )
    if not data:
        return None
    items = data if isinstance(data, list) else data.get("items", [])
    print(f"    {len(items)} specs to check")

    # Check each spec's rule sets for target_gene
    for i, item in enumerate(items):
        ent_id = item.get("entId")
        if not ent_id:
            continue

        doc = fetch_with_retry(
            f"{BASE}/SequenceVariantInterpretation/id/{ent_id}",
            params={"detail": "high"},
            timeout=120.0,
        )
        if not doc:
            continue

        for rs in (doc.get("ruleSets") or []):
            genes = [g.get("label") for g in (rs.get("genes") or [])]
            if target_gene in genes:
                print(f"    FOUND: {ent_id} — {doc.get('label', '')[:80]}")
                return ent_id, doc, rs

        if (i + 1) % 20 == 0:
            print(f"    checked {i+1}/{len(items)}...")
        time.sleep(0.3)

    return None


def extract_criteria_from_rs(rs: dict) -> list[dict]:
    criteria = []
    for code in rs.get("criteriaCodes", []):
        label = code.get("label")
        if not label:
            continue
        strengths = []
        applicable = []
        for s in code.get("evidenceStrengths", []):
            app = (s.get("applicability") or "").lower()
            is_app = "applicable" in app and "not" not in app
            strengths.append({
                "strength": s.get("label"),
                "applicable": is_app,
                "description": s.get("description", ""),
            })
            if is_app:
                applicable.append(s.get("label"))
        criteria.append({
            "criterion_code": label,
            "description": code.get("description", ""),
            "strengths": strengths,
            "applicable_strengths": applicable,
        })
    return criteria


def main():
    if not CACHE.exists():
        print("No existing cache. Run fetch_vcep_specs.py first.")
        return

    existing = json.loads(CACHE.read_text())
    existing_genes = {s["gene"] for s in existing}
    print(f"Existing cache: {sorted(existing_genes)}")
    print()

    for target_gene in ("BRCA2", "CFTR"):
        if target_gene in existing_genes:
            print(f"{target_gene}: already in cache")
            continue

        print(f"Searching for {target_gene}...")
        result = find_spec_by_gene(target_gene)
        if not result:
            print(f"  {target_gene}: NOT FOUND")
            print()
            continue

        ent_id, doc, rs = result
        criteria = extract_criteria_from_rs(rs)
        print(f"  extracted {len(criteria)} criteria")

        # Determine VCEP name from label
        label = doc.get("label", "")
        vcep_name = "Unknown VCEP"
        for known in ("ENIGMA", "InSiGHT", "TP53", "CFTR", "ClinGen"):
            if known in label:
                vcep_name = known
                break

        existing.append({
            "gene": target_gene,
            "vcep_name": vcep_name,
            "spec_version": label.split("Version")[-1].strip() if "Version" in label else "1.0",
            "spec_label": label,
            "cspec_id": ent_id,
            "last_updated": doc.get("lastUpdated"),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "criteria": criteria,
        })
        print()

    CACHE.write_text(json.dumps(existing, indent=2))
    print(f"Cache now has {len(existing)} specs:")
    for s in existing:
        print(f"  {s['gene']:8} {s['vcep_name']:20} v{s['spec_version']}  criteria={len(s['criteria'])}")


if __name__ == "__main__":
    main()
