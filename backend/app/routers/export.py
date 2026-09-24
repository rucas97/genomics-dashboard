from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from app.db import get_db
from app.deps import get_current_user
from app.user import CurrentUser
from app.services.audit import log_action
from app.services.export import to_fhir_bundle, to_json_payload, to_hl7_oru
import json

router = APIRouter(prefix="/export", tags=["export"])


def _load(sample_id: str):
    db = get_db()
    sample = db.get_sample(sample_id)
    if not sample:
        raise HTTPException(404, "Sample not found")

    variants, _ = db.list_variants({"sample_id": sample_id}, limit=10000, offset=0)
    for v in variants:
        a = db.get_variant_acmg(v["id"])
        v["acmg_classification"] = a["classification"] if a else "VUS"
        v["acmg_confidence"] = a["confidence"] if a else None
        v["acmg_summary"] = a["evidence_summary"] if a else None
    return sample, variants


@router.get("/sample/{sample_id}/fhir")
async def export_fhir(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    sample, variants = _load(sample_id)
    bundle = to_fhir_bundle(sample, variants)
    log_action(user.id, "export", "sample", sample_id, {"format": "fhir", "variant_count": len(variants)})
    filename = f"{sample.get('name', 'sample').replace('.', '_')}_fhir.json"
    return Response(
        content=json.dumps(bundle, indent=2),
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/json")
async def export_json(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    sample, variants = _load(sample_id)
    payload = to_json_payload(sample, variants)
    log_action(user.id, "export", "sample", sample_id, {"format": "json", "variant_count": len(variants)})
    filename = f"{sample.get('name', 'sample').replace('.', '_')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/hl7")
async def export_hl7(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    sample, variants = _load(sample_id)
    message = to_hl7_oru(sample, variants)
    log_action(user.id, "export", "sample", sample_id, {"format": "hl7", "variant_count": len(variants)})
    filename = f"{sample.get('name', 'sample').replace('.', '_')}.hl7"
    return Response(
        content=message,
        media_type="application/hl7-v2",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/preview")
async def export_preview(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    sample, variants = _load(sample_id)
    actionable = [v for v in variants if (v.get("acmg_classification") or "VUS").lower() in ("pathogenic", "likely pathogenic")]
    return {
        "sample_id": sample_id,
        "sample_name": sample.get("name"),
        "variant_count": len(variants),
        "actionable_count": len(actionable),
        "formats_available": ["fhir", "json", "hl7"],
    }
