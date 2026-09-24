from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db import get_db
from app.deps import get_current_user
from app.user import CurrentUser
from app.services.audit import log_action
from app.services.acmg import (
    classify_variant, what_would_change_it, CRITERIA, classify,
)
from app.services.mane import normalize_variant

router = APIRouter(prefix="/acmg", tags=["acmg"])


@router.get("/criteria")
async def list_criteria(user: CurrentUser = Depends(get_current_user)):
    return [{"code": k, **v} for k, v in CRITERIA.items()]


@router.get("/variant/{variant_id}")
async def get_variant_acmg(variant_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")

    acmg = db.get_variant_acmg(variant_id)
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

    enriched = normalize_variant(variant)
    suggestions = what_would_change_it(variant)
    return {"variant": enriched, "acmg": acmg, "suggestions": suggestions}


class SimulateRequest(BaseModel):
    criteria_fired: list[dict]


@router.post("/variant/{variant_id}/simulate")
async def simulate_acmg(variant_id: str, body: SimulateRequest, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")

    simulated, confidence = classify(body.criteria_fired)
    stored = db.get_variant_acmg(variant_id)

    stored_codes = {c["code"] for c in (stored.get("criteria_fired") or [])} if stored else set()
    sim_codes = {c["code"] for c in body.criteria_fired}
    added = sorted(sim_codes - stored_codes)
    removed = sorted(stored_codes - sim_codes)

    return {
        "simulated_classification": simulated,
        "simulated_confidence": confidence,
        "stored_classification": stored.get("classification") if stored else None,
        "changed": stored and stored.get("classification") != simulated,
        "criteria_added": added,
        "criteria_removed": removed,
    }


class CriteriaOverride(BaseModel):
    criteria_fired: list[dict]
    notes: str | None = None
    classification_override: str | None = None


@router.put("/variant/{variant_id}")
async def update_variant_acmg(variant_id: str, body: CriteriaOverride, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")

    computed, confidence = classify(body.criteria_fired)
    classification = body.classification_override or computed

    payload = {
        "variant_id": variant_id,
        "classification": classification,
        "criteria_fired": body.criteria_fired,
        "auto_classification": computed,
        "confidence": confidence,
        "notes": body.notes,
        "reviewed_by": user.id,
    }

    db.upsert_variant_acmg(payload)
    log_action(user.id, "acmg_override", "variant", variant_id, {
        "classification": classification,
        "criteria_count": len(body.criteria_fired),
    })

    return {"ok": True, "classification": classification, "confidence": confidence}


@router.get("/explain/{variant_id}")
async def explain_classification(variant_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    variant = db.get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")

    acmg = db.get_variant_acmg(variant_id)
    fired = acmg.get("criteria_fired") if acmg else []
    if isinstance(fired, str):
        import json
        fired = json.loads(fired)
    if not isinstance(fired, list):
        fired = []

    supporting_pathogenic = [c for c in fired if CRITERIA.get(c.get("code"), {}).get("category") == "pathogenic"]
    supporting_benign = [c for c in fired if CRITERIA.get(c.get("code"), {}).get("category") == "benign"]

    missing_evidence = []
    if not variant.get("gene"):
        missing_evidence.append("Gene annotation missing — cannot evaluate gene-specific criteria")
    if not variant.get("consequence"):
        missing_evidence.append("Consequence missing — cannot evaluate PVS1, PP3, BP4, BP7")
    if variant.get("gnomad_af") is None:
        missing_evidence.append("gnomAD population frequency missing — cannot evaluate PM2, BA1, BS1")
    if not variant.get("clinvar_significance"):
        missing_evidence.append("No ClinVar record — cannot evaluate PP4, PP5, BP6")

    current = acmg.get("classification") if acmg else "VUS"
    rank = {"Benign": 0, "Likely Benign": 1, "VUS": 2, "Likely Pathogenic": 3, "Pathogenic": 4}

    upgrade_paths = []
    candidates = ["PVS1", "PS1", "PS2", "PS3", "PS4", "PM1", "PM2", "PM3", "PP1", "PP2", "PP3"]
    fired_codes = {c.get("code") for c in fired}

    for extra in candidates:
        if extra in fired_codes:
            continue
        test_set = list(fired) + [{"code": extra, "source": "hypothetical", "evidence": "What-if"}]
        simulated, _ = classify(test_set)
        if rank.get(simulated, 0) > rank.get(current, 0):
            upgrade_paths.append({
                "add_criterion": extra,
                "would_become": simulated,
                "description": CRITERIA.get(extra, {}).get("desc", ""),
            })

    return {
        "classification": current,
        "confidence": acmg.get("confidence") if acmg else None,
        "supporting_pathogenic": [
            {"code": c["code"], "evidence": c.get("evidence", ""),
             "description": CRITERIA.get(c["code"], {}).get("desc", ""),
             "weight": CRITERIA.get(c["code"], {}).get("weight")}
            for c in supporting_pathogenic
        ],
        "supporting_benign": [
            {"code": c["code"], "evidence": c.get("evidence", ""),
             "description": CRITERIA.get(c["code"], {}).get("desc", ""),
             "weight": CRITERIA.get(c["code"], {}).get("weight")}
            for c in supporting_benign
        ],
        "missing_evidence": missing_evidence,
        "upgrade_paths": upgrade_paths[:5],
        "notes": acmg.get("notes") if acmg else None,
    }


@router.get("/summary/{sample_id}")
async def sample_acmg_summary(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    variants, _ = db.list_variants({"sample_id": sample_id}, limit=10000, offset=0)
    if not variants:
        return {"total": 0, "counts": {}}

    counts = {}
    for v in variants:
        a = db.get_variant_acmg(v["id"])
        c = a.get("classification") if a else "VUS"
        counts[c] = counts.get(c, 0) + 1

    return {"total": len(variants), "counts": counts}
