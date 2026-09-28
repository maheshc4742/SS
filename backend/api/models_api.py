import json
import logging
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import MODELS_DIR, settings
from backend.models.database_models import ModelRegistry
from backend.models.schemas import ModelItem, ModelActivateRequest

router = APIRouter(prefix="/api/models", tags=["Model Management"])
logger = logging.getLogger(__name__)

@router.get("", response_model=List[ModelItem])
def list_available_models(db: Session = Depends(get_db)):
    """
    Returns list of all available semantic model checkpoints (base and fine-tuned versions).
    """
    results: List[ModelItem] = []

    # 1. Base model
    is_base_active = (settings.ACTIVE_SEMANTIC_MODEL == "codbert_base")
    base_meta_path = MODELS_DIR / "codbert_base" / "metadata.json"
    base_score = 0.82
    created_at = "2026-01-01T00:00:00"

    if base_meta_path.exists():
        try:
            with open(base_meta_path, "r", encoding="utf-8") as f:
                b_data = json.load(f)
                base_score = b_data.get("validation_score", base_score)
                created_at = b_data.get("created_at", created_at)
        except Exception:
            pass

    results.append(ModelItem(
        model_version="codbert_base",
        training_samples=0,
        validation_score=base_score,
        created_at=created_at,
        base_model="codbert_base",
        is_active=is_base_active
    ))

    # 2. Check directories in models/
    for sub in sorted(MODELS_DIR.iterdir()):
        if sub.is_dir() and sub.name.startswith("codbert_ft_v"):
            meta_file = sub / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    results.append(ModelItem(
                        model_version=meta.get("model_version", sub.name),
                        training_samples=meta.get("training_samples", 0),
                        validation_score=meta.get("validation_score", 0.0),
                        created_at=meta.get("created_at", ""),
                        base_model=meta.get("base_model", "codbert_base"),
                        is_active=(settings.ACTIVE_SEMANTIC_MODEL == sub.name)
                    ))
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {sub.name}: {e}")

    return results


@router.post("/activate")
def activate_model_version(req: ModelActivateRequest, db: Session = Depends(get_db)):
    """
    Sets the active model version to be used for all subsequent evaluations.
    """
    version = req.model_version.strip()
    target_dir = MODELS_DIR / version

    if version != "codbert_base" and not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model version '{version}' not found on server.")

    # Update runtime setting
    settings.ACTIVE_SEMANTIC_MODEL = version

    # Update DB registry
    db.query(ModelRegistry).update({ModelRegistry.is_active: False})
    reg = db.query(ModelRegistry).filter(ModelRegistry.model_version == version).first()
    if reg:
        reg.is_active = True
    db.commit()

    logger.info(f"Active semantic model changed to: {version}")
    return {
        "success": True,
        "message": f"Active model set to '{version}'",
        "active_model": version
    }
