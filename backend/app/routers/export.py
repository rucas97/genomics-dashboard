from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from app.supabase_client import supabase
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.export import to_fhir_bundle, to_json_payload, to_hl7_oru
import json
from datetime import datetime

router = APIRouter(prefix="/export", tags=["export"])


def _load_sample_variants(sample_id: str):
    sresp = supabase.table("samples").select("*").eq("id", sample_id).execute()
    if not sresp.data:
        raise HTTPException(404, "Sample not found")
    sample = sresp.data[0]

    vresp = supabase.table("variants").select("*").eq("sample_id", sample_id).execute()
    variants = vresp.data or []

    if variants:
        vids = [v["id"] for v in variants]
        aresp = supabase.table("variant_acmg").select("*").in_("variant_id", vids).execute()
        acmg_map = {a["variant_id"]: a for a in (aresp.data or [])}
        for v in variants:
            a = acmg_map.get(v["id"])
            v["acmg_classification"] = a["classification"] if a else "VUS"
            v["acmg_confidence"] = a["confidence"] if a else None
            v["acmg_summary"] = a["evidence_summary"] if a else None

    return sample, variants


@router.get("/sample/{sample_id}/fhir")
async def export_fhir(sample_id: str, user=Depends(get_current_user)):
    sample, variants = _load_sample_variants(sample_id)
    bundle = to_fhir_bundle(sample, variants)

    log_action(user.id, "export", "sample", sample_id, {
        "format": "fhir",
        "variant_count": len(variants),
    })

    filename = f"{sample.get('name', 'sample').replace('.', '_')}_fhir.json"
    return Response(
        content=json.dumps(bundle, indent=2),
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/json")
async def export_json(sample_id: str, user=Depends(get_current_user)):
    sample, variants = _load_sample_variants(sample_id)
    payload = to_json_payload(sample, variants)

    log_action(user.id, "export", "sample", sample_id, {
        "format": "json",
        "variant_count": len(variants),
    })

    filename = f"{sample.get('name', 'sample').replace('.', '_')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/hl7")
async def export_hl7(sample_id: str, user=Depends(get_current_user)):
    sample, variants = _load_sample_variants(sample_id)
    message = to_hl7_oru(sample, variants)

    log_action(user.id, "export", "sample", sample_id, {
        "format": "hl7",
        "variant_count": len(variants),
    })

    filename = f"{sample.get('name', 'sample').replace('.', '_')}.hl7"
    return Response(
        content=message,
        media_type="application/hl7-v2",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample/{sample_id}/preview")
async def export_preview(sample_id: str, user=Depends(get_current_user)):
    """Preview all three formats without downloading."""
    sample, variants = _load_sample_variants(sample_id)
    return {
        "sample_id": sample_id,
        "sample_name": sample.get("name"),
        "variant_count": len(variants),
        "actionable_count": sum(
            1 for v in variants
            if (v.get("acmg_classification") or "VUS").lower() in ("pathogenic", "likely pathogenic")
        ),
        "fhir_preview": {
            "resourceType": "Bundle",
            "type": "collection",
            "entry_count": sum(
                1 for v in variants
                if (v.get("acmg_classification") or "VUS").lower() in ("pathogenic", "likely pathogenic")
            ),
        },
        "hl7_preview": to_hl7_oru(sample, variants).split("\r")[:5],
        "formats_available": ["fhir", "json", "hl7"],
    }
