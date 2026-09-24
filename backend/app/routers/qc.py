from fastapi import APIRouter, Depends
from app.db import get_db
from app.deps import get_current_user
from app.user import CurrentUser

router = APIRouter(prefix="/qc", tags=["qc"])


@router.get("/{sample_id}")
async def get_qc(sample_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    return db.get_qc_for_sample(sample_id)
