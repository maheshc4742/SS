import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.evaluator import evaluator
from backend.services.hitl_service import hitl_service
from backend.models.schemas import (
    EvaluationResponse,
    EvaluationRequest,
    HITLApproveRequest,
    HITLRejectRequest,
    HITLUpdateRequest,
    HITLItemResponse
)

router = APIRouter(prefix="/api", tags=["HITL"])
logger = logging.getLogger(__name__)

@router.post("/train/evaluate", response_model=EvaluationResponse)
async def train_evaluate_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    key_answers: Optional[str] = Form(None),
    rubrics: Optional[str] = Form(None),
    student_answers: Optional[str] = Form(None),
    key_answers_file: Optional[UploadFile] = File(None),
    rubrics_file: Optional[UploadFile] = File(None),
    student_answers_file: Optional[UploadFile] = File(None),
    ocr_provider: Optional[str] = Form(None),
    model_version: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Train Mode Evaluation Endpoint.
    Extracts answers, performs AI prediction, and creates pending records
    in the HITL review queue. Human verification is required before data is added to training.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            eval_req = EvaluationRequest(**body)
            result = await evaluator.evaluate_script(
                mode="train",
                key_answers=eval_req.key_answers,
                rubrics=eval_req.rubrics,
                student_answers=eval_req.student_answers,
                ocr_provider=eval_req.ocr_provider,
                model_version=eval_req.model_version,
                db=db
            )
            return result
        except Exception as e:
            logger.exception("Error in JSON train evaluate request")
            raise HTTPException(status_code=400, detail=str(e))

    # Read key_answers from file or form
    keys_dict = None
    if key_answers_file:
        try:
            content = await key_answers_file.read()
            keys_dict = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in uploaded key_answers_file: {e}")
    elif key_answers:
        try:
            keys_dict = json.loads(key_answers)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in key_answers: {e}")

    # Read rubrics from file or form
    rubrics_dict = None
    if rubrics_file:
        try:
            content = await rubrics_file.read()
            rubrics_dict = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in uploaded rubrics_file: {e}")
    elif rubrics:
        try:
            rubrics_dict = json.loads(rubrics)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in rubrics: {e}")

    if not keys_dict or not rubrics_dict:
        raise HTTPException(status_code=400, detail="Missing key_answers or rubrics (either as JSON string or file).")

    # Read student_answers from file or form
    s_answers_dict = None
    if student_answers_file:
        try:
            content = await student_answers_file.read()
            s_answers_dict = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in uploaded student_answers_file: {e}")
    elif student_answers:
        try:
            s_answers_dict = json.loads(student_answers)
        except Exception:
            pass

    file_bytes = None
    filename = None
    if file:
        file_bytes = await file.read()
        filename = file.filename

    if not file_bytes and not s_answers_dict:
        raise HTTPException(status_code=400, detail="Must provide either a file or student_answers JSON.")

    try:
        result = await evaluator.evaluate_script(
            mode="train",
            key_answers=keys_dict,
            rubrics=rubrics_dict,
            student_answers=s_answers_dict,
            file_bytes=file_bytes,
            filename=filename,
            ocr_provider=ocr_provider,
            model_version=model_version,
            db=db
        )
        return result
    except Exception as e:
        logger.exception("Failed during Train mode evaluation")
        raise HTTPException(status_code=500, detail=f"Train evaluation failed: {str(e)}")


@router.get("/hitl/pending", response_model=List[HITLItemResponse])
def get_pending_hitl_items(db: Session = Depends(get_db)):
    """Fetches all answer evaluation items currently pending Human-in-the-Loop review."""
    items = hitl_service.get_pending_items(db)
    response = []
    for it in items:
        rub = json.loads(it.rubric_json) if it.rubric_json else {}
        response.append(HITLItemResponse(
            id=it.id,
            evaluation_id=it.evaluation_id,
            question_id=it.question_id,
            question_text=it.question_text,
            student_answer=it.student_answer,
            reference_answer=it.reference_answer,
            rubric=rub,
            ai_marks=it.ai_marks,
            ai_feedback=it.ai_feedback,
            confidence=it.confidence,
            semantic_score=it.semantic_score,
            human_marks=it.human_marks,
            human_feedback=it.human_feedback,
            status=it.status,
            human_verified=it.human_verified,
            created_at=it.created_at.isoformat() if it.created_at else ""
        ))
    return response


@router.post("/hitl/approve")
def approve_hitl_item(req: HITLApproveRequest, db: Session = Depends(get_db)):
    """
    Approves an evaluation item. Sets human_verified = True and appends to verified_training.jsonl.
    """
    try:
        updated = hitl_service.approve_item(
            item_id=req.id,
            human_marks=req.human_marks,
            human_feedback=req.human_feedback,
            db=db
        )
        return {
            "success": True,
            "message": f"Question {updated.question_id} approved and added to verified training data.",
            "item_id": updated.id,
            "human_marks": updated.human_marks,
            "human_feedback": updated.human_feedback,
            "status": updated.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hitl/reject")
def reject_hitl_item(req: HITLRejectRequest, db: Session = Depends(get_db)):
    """
    Rejects an evaluation item. Does NOT store in training data.
    """
    try:
        updated = hitl_service.reject_item(
            item_id=req.id,
            reason=req.reason,
            db=db
        )
        return {
            "success": True,
            "message": f"Question {updated.question_id} rejected.",
            "item_id": updated.id,
            "status": updated.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/hitl/{id}")
def update_hitl_item(id: int, req: HITLUpdateRequest, db: Session = Depends(get_db)):
    """Updates draft human marks or feedback before approval."""
    try:
        updated = hitl_service.update_draft(
            item_id=id,
            human_marks=req.human_marks,
            human_feedback=req.human_feedback,
            db=db
        )
        return {
            "success": True,
            "item_id": updated.id,
            "human_marks": updated.human_marks,
            "human_feedback": updated.human_feedback
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
