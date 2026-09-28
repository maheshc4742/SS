import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.hitl_service import hitl_service
from backend.training.train import run_fine_tuning
from backend.models.schemas import TrainingStatsResponse

router = APIRouter(prefix="/api/training", tags=["Training & Fine-Tuning"])
logger = logging.getLogger(__name__)

@router.get("/stats", response_model=TrainingStatsResponse)
def get_training_statistics(db: Session = Depends(get_db)):
    """
    Returns current count of verified training examples, threshold, and fine-tuning readiness.
    """
    stats = hitl_service.get_training_stats(db)
    return TrainingStatsResponse(**stats)

@router.post("/start")
def start_fine_tuning_job(
    force: bool = Query(False, description="Allow starting even if below threshold for demonstration purposes"),
    db: Session = Depends(get_db)
):
    """
    Triggers the fine-tuning pipeline on verified human feedback.
    Splits into train/val/test, trains new checkpoint, validates, and registers a versioned model.
    """
    stats = hitl_service.get_training_stats(db)
    if not stats["is_ready"] and not force:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient verified training data. Currently have {stats['verified_count']} / "
                f"{stats['min_threshold']} required samples. Complete more HITL reviews to reach threshold."
            )
        )

    try:
        metadata = run_fine_tuning(db)
        return {
            "success": True,
            "message": f"Successfully fine-tuned model {metadata['model_version']}",
            "metadata": metadata
        }
    except Exception as e:
        logger.exception("Fine-tuning execution failed")
        raise HTTPException(status_code=500, detail=f"Fine-tuning failed: {str(e)}")
