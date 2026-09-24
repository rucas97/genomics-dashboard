from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.db import get_db
from app.deps import get_current_user
from app.user import CurrentUser
from app.services.annotate import annotate_batch
from app.services.audit import log_action

router = APIRouter(prefix="/annotate", tags=["annotate"])


@router.post("/sample/{sample_id}")
async def annotate_sample(
    sample_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    variants, _ = db.list_variants({"sample_id": sample_id}, limit=10000, offset=0)
    if not variants:
        raise HTTPException(404, "No variants for this sample")

    log_action(user.id, "annotate", "sample", sample_id)
    background.add_task(_run_annotation, sample_id)
    return {"status": "annotating", "variant_count": len(variants)}


def _run_annotation(sample_id: str):
    db = get_db()
    try:
        variants, _ = db.list_variants({"sample_id": sample_id}, limit=10000, offset=0)
        to_annotate = [v for v in variants if not v.get("gene")]
        if not to_annotate:
            print(f"No unannotated variants for {sample_id}")
            return

        annotated = annotate_batch(to_annotate)
        for v in annotated:
            if v.get("id"):
                db.update_variant(v["id"], {
                    "gene": v.get("gene"),
                    "consequence": v.get("consequence"),
                    "impact": v.get("impact"),
                    "clinvar_significance": v.get("clinvar_significance"),
                })
        print(f"Annotated {sum(1 for v in annotated if v.get('gene'))}/{len(annotated)} variants for sample {sample_id}")
    except Exception as e:
        print(f"Annotation job failed for {sample_id}: {e}")
