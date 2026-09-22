from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.supabase_client import supabase
from app.deps import get_current_user
from app.services.annotate import annotate_batch
from app.services.audit import log_action

router = APIRouter(prefix="/annotate", tags=["annotate"])


@router.post("/sample/{sample_id}")
async def annotate_sample(
    sample_id: str,
    background: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Kick off annotation for all variants in a sample."""
    resp = supabase.table("variants").select("*").eq("sample_id", sample_id).execute()
    if not resp.data:
        raise HTTPException(404, "No variants for this sample")

    log_action(user.id, "annotate", "sample", sample_id)
    background.add_task(_run_annotation, sample_id, user.id)
    return {"status": "annotating", "variant_count": len(resp.data)}


def _run_annotation(sample_id: str, user_id: str):
    """Background job: annotate all variants for a sample."""
    try:
        resp = supabase.table("variants").select("*").eq("sample_id", sample_id).execute()
        variants = resp.data or []

        # Only annotate variants missing a gene
        to_annotate = [v for v in variants if not v.get("gene")]
        if not to_annotate:
            print(f"No unannotated variants for {sample_id}")
            return

        annotated = annotate_batch(to_annotate)

        # Update each row
        for v in annotated:
            supabase.table("variants").update({
                "gene": v.get("gene"),
                "consequence": v.get("consequence"),
                "impact": v.get("impact"),
                "clinvar_significance": v.get("clinvar_significance"),
            }).eq("id", v["id"]).execute()

        print(f"Annotated {len(annotated)} variants for sample {sample_id}")
    except Exception as e:
        print(f"Annotation job failed for {sample_id}: {e}")
