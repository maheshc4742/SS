import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.evaluator import evaluator
from backend.models.schemas import EvaluationResponse, EvaluationRequest

router = APIRouter(prefix="/api", tags=["Evaluation"])
logger = logging.getLogger(__name__)

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_script_endpoint(
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
    Evaluate Mode Endpoint.
    Directly evaluates the uploaded answer script (image, PDF, or JSON)
    without triggering the HITL review or training data collection.
    """
    content_type = request.headers.get("content-type", "")

    # Handle application/json requests
    if "application/json" in content_type:
        try:
            body = await request.json()
            eval_req = EvaluationRequest(**body)
            result = await evaluator.evaluate_script(
                mode="evaluate",
                key_answers=eval_req.key_answers,
                rubrics=eval_req.rubrics,
                student_answers=eval_req.student_answers,
                ocr_provider=eval_req.ocr_provider,
                model_version=eval_req.model_version,
                db=db
            )
            return result
        except Exception as e:
            logger.exception("Error in JSON evaluate request")
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
        raise HTTPException(status_code=400, detail="Must provide either a file (.png, .jpg, .pdf, .json) or student_answers JSON.")

    try:
        result = await evaluator.evaluate_script(
            mode="evaluate",
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
        logger.exception("Failed during evaluation")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
