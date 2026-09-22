from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.supabase_client import supabase
from app.db import sb_select, sb_insert, sb_update
from app.deps import get_current_user
from app.services.audit import log_action
from app.services.acmg import classify_variant, what_would_change_it, CRITERIA
from app.services.mane import normalize_variant

router = APIRouter(prefix="/acmg", tags=["acmg"])


@router.get("/criteria")
async def list_criteria(user=Depends(get_current_user)):
    """Return the full ACMG criteria catalog for the UI."""
    return [{"code": k, **v} for k, v in CRITERIA.items()]


@router.get("/variant/{variant_id}")
async def get_variant_acmg(variant_id: str, user=Depends(get_current_user)):
    """Get the full ACMG detail for one variant."""
    vresp = supabase.table("variants").select("*").eq("id", variant_id).execute()
    if not vresp.data:
        raise HTTPException(404, "Variant not found")
    variant = vresp.data[0]

    aresp = supabase.table("variant_acmg").select("*").eq("variant_id", variant_id).execute()
    acmg = aresp.data[0] if aresp.data else None

    # If no ACMG yet, compute on the fly
    if not acmg:
        result = classify_variant(variant)
        acmg = {
            "variant_id": variant_id,
            "classification": result["classification"],
            "confidence": result["confidence"],
            "criteria_fired": result["criteria_fired"],
            "auto_classification": result["auto_classification"],
            "evidence_summary": result["evidence_summary"],
            "notes": None,
        }

    # Enrich with MANE and "what would change it"
    enriched = normalize_variant(variant)
    suggestions = what_would_change_it(variant)

    return {
        "variant": enriched,
        "acmg": acmg,
        "suggestions": suggestions,
    }


class CriteriaOverride(BaseModel):
    criteria_fired: list[dict]
    notes: str | None = None
    classification_override: str | None = None


@router.put("/variant/{variant_id}")
async def update_variant_acmg(
    variant_id: str,
    body: CriteriaOverride,
    user=Depends(get_current_user),
):
    """
    Save a manual override of the criteria list.
    Recomputes the classification from the edited criteria.
    """
    vresp = supabase.table("variants").select("*").eq("id", variant_id).execute()
    if not vresp.data:
        raise HTTPException(404, "Variant not found")

    # Recompute classification from the edited criteria
    from app.services.acmg import classify
    computed, confidence = classify(body.criteria_fired)

    classification = body.classification_override or computed

    # Upsert the ACMG row
    payload = {
        "variant_id": variant_id,
        "classification": classification,
        "criteria_fired": body.criteria_fired,
        "auto_classification": computed,
        "confidence": confidence,
        "notes": body.notes,
        "reviewed_by": user.id,
        "reviewed_at": "now()",
    }

    existing = supabase.table("variant_acmg").select("id").eq("variant_id", variant_id).execute()
    if existing.data:
        supabase.table("variant_acmg").update(payload).eq("variant_id", variant_id).execute()
    else:
        sb_insert("variant_acmg", payload)

    log_action(user.id, "acmg_override", "variant", variant_id, {
        "classification": classification,
        "criteria_count": len(body.criteria_fired),
    })

    return {"ok": True, "classification": classification, "confidence": confidence}


@router.get("/summary/{sample_id}")
async def sample_acmg_summary(sample_id: str, user=Depends(get_current_user)):
    """ACMG classification counts for one sample."""
    vresp = supabase.table("variants").select("id").eq("sample_id", sample_id).execute()
    if not vresp.data:
        return {"total": 0, "counts": {}}

    variant_ids = [v["id"] for v in vresp.data]
    aresp = supabase.table("variant_acmg").select("classification").in_("variant_id", variant_ids).execute()

    counts = {}
    for row in (aresp.data or []):
        c = row.get("classification") or "VUS"
        counts[c] = counts.get(c, 0) + 1

    return {"total": len(vresp.data), "counts": counts}
