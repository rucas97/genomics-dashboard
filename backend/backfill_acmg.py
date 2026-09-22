"""
One-time script: classify every variant in the DB with ACMG.
Run once after deploying the schema.
"""
from app.supabase_client import supabase
from app.services.acmg import classify_variant
from app.services.provenance import record_provenance


def main():
    print("Fetching all variants...")
    resp = supabase.table("variants").select("*").execute()
    variants = resp.data or []
    print(f"Found {len(variants)} variants")

    classified = 0
    errors = 0
    last_sample_id = None

    for i, v in enumerate(variants):
        try:
            result = classify_variant(v)
            supabase.table("variant_acmg").upsert({
                "variant_id": v["id"],
                "classification": result["classification"],
                "criteria_fired": result["criteria_fired"],
                "auto_classification": result["auto_classification"],
                "evidence_summary": result["evidence_summary"],
                "confidence": result["confidence"],
            }, on_conflict="variant_id").execute()
            classified += 1
            last_sample_id = v.get("sample_id")
        except Exception as e:
            errors += 1
            print(f"  Failed {v.get('id')}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(variants)}")

    # Record provenance against the last sample seen (a valid UUID)
    if last_sample_id:
        record_provenance(
            resource_type="sample",
            resource_id=last_sample_id,
            annotation_db_version="ACMG-2015",
            command="backfill_acmg.py",
            outputs={"classified": classified, "errors": errors},
        )

    print(f"\nDone. Classified: {classified}, Errors: {errors}")


if __name__ == "__main__":
    main()
