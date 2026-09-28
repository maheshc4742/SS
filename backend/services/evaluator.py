import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from backend.ocr.ocr_factory import get_ocr_engine
from backend.services.semantic_module import get_semantic_model
from backend.services.grading_module import grading_module, quantize_half_or_whole
from backend.services.hitl_service import hitl_service
from backend.models.database_models import EvaluationRecord
from backend.core.config import settings, REPORTS_DIR

logger = logging.getLogger(__name__)

class ScriptSenseEvaluator:
    """
    Main evaluation orchestrator for ScriptSense.
    Handles Answer Extraction (OCR or JSON bypass), Semantic Evaluation,
    Rubric Grading, and separation of Evaluate vs Train modes.
    """

    async def evaluate_script(
        self,
        mode: str,
        key_answers: Dict[str, str],
        rubrics: Dict[str, Any],
        student_answers: Optional[Dict[str, str]] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        ocr_provider: Optional[str] = None,
        model_version: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        eval_id = str(uuid.uuid4())
        active_provider = ocr_provider or settings.OCR_PROVIDER
        active_model = model_version or settings.ACTIVE_SEMANTIC_MODEL

        normalized_key_answers = {str(k): v for k, v in (key_answers or {}).items()}
        normalized_rubrics = {str(k): v for k, v in (rubrics or {}).items()}

        # 1. Answer Extraction
        extracted_answers: Dict[str, str] = {}
        if student_answers:
            # JSON Answer Script: Direct bypass of OCR
            logger.info("JSON input detected. Bypassing OCR pipeline.")
            extracted_answers = {str(k): str(v) for k, v in student_answers.items()}
        elif file_bytes and filename:
            # Check if uploaded file is a JSON file
            if filename.lower().endswith(".json"):
                logger.info("Uploaded file is JSON. Bypassing OCR.")
                try:
                    parsed = json.loads(file_bytes.decode("utf-8"))
                    extracted_answers = {str(k): str(v) for k, v in parsed.items()}
                except Exception as e:
                    logger.error(f"Error parsing uploaded JSON: {e}")
                    extracted_answers = {}
            else:
                # Image or PDF input -> OCR provider
                logger.info(f"Invoking OCR provider '{active_provider}' for {filename}...")
                ocr_engine = get_ocr_engine(active_provider)
                questions_hint = list(key_answers.keys())
                extracted_answers = await ocr_engine.extract_answers(
                    file_bytes=file_bytes,
                    filename=filename,
                    questions_hint=questions_hint
                )
        else:
            raise ValueError("No student answers or script file provided for evaluation.")

        # 2. Semantic Evaluation & Rubric-Based Grading per Question
        semantic_evaluator = get_semantic_model(active_model)
        question_results: List[Dict[str, Any]] = []

        total_max_marks = 0.0
        total_obtained_marks = 0.0

        def sort_question_key(question_id: Any) -> tuple:
            q_text = str(question_id)
            return (0, int(q_text)) if q_text.isdigit() else (1, q_text)

        all_q_keys = sorted(
            set(normalized_key_answers.keys()) | set(extracted_answers.keys()),
            key=sort_question_key
        )

        for q_id in all_q_keys:
            s_answer = extracted_answers.get(q_id, "").strip()
            r_answer = str(normalized_key_answers.get(q_id, "")).strip()
            rubric = normalized_rubrics.get(q_id, {"max_marks": 5.0, "criteria": []})
            max_marks = float(rubric.get("max_marks", 5.0))
            total_max_marks += max_marks

            if not s_answer:
                # Student did not answer or was not detected
                question_results.append({
                    "question": q_id,
                    "marks": 0.0,
                    "max_marks": max_marks,
                    "semantic_score": 0.0,
                    "confidence": 1.0,
                    "feedback": f"No answer provided for Question {q_id}. Awarded 0 marks.",
                    "criteria_breakdown": [],
                    "student_answer": "",
                    "reference_answer": r_answer,
                    "hitl_item_id": None
                })
                continue

            # Compute semantic score
            sem_res = semantic_evaluator.evaluate(
                student_answer=s_answer,
                reference_answer=r_answer,
                rubric=rubric
            )

            # Rubric grading (enforces .5 or whole number marks)
            grade_res = grading_module.grade(
                student_answer=s_answer,
                reference_answer=r_answer,
                rubric=rubric,
                semantic_score=sem_res.similarity_score,
                confidence=sem_res.confidence
            )

            total_obtained_marks += grade_res.marks

            question_results.append({
                "question": q_id,
                "marks": grade_res.marks,
                "max_marks": grade_res.max_marks,
                "semantic_score": grade_res.semantic_score,
                "confidence": grade_res.confidence,
                "feedback": grade_res.feedback,
                "criteria_breakdown": grade_res.criteria_breakdown,
                "student_answer": s_answer,
                "reference_answer": r_answer,
                "hitl_item_id": None
            })

        # Calculate totals and percentage
        total_obtained_marks = quantize_half_or_whole(total_obtained_marks, total_max_marks)
        percentage = round((total_obtained_marks / total_max_marks * 100), 2) if total_max_marks > 0 else 0.0

        overall_summary = (
            f"Script evaluated with {active_model} ({active_provider} OCR). "
            f"Overall score: {total_obtained_marks:g}/{total_max_marks:g} ({percentage}%). "
            f"Evaluated {len(question_results)} descriptive question(s)."
        )

        # 3. Mode Handling
        report_path = None
        if mode.lower() == "evaluate":
            # Save evaluation report
            report_data = {
                "id": eval_id,
                "mode": "evaluate",
                "model": active_model,
                "ocr_provider": active_provider,
                "total_marks": total_max_marks,
                "obtained_marks": total_obtained_marks,
                "percentage": percentage,
                "overall_summary": overall_summary,
                "questions": [
                    {
                        "question": q["question"],
                        "marks": q["marks"],
                        "max_marks": q["max_marks"],
                        "semantic_score": q["semantic_score"],
                        "confidence": q["confidence"],
                        "feedback": q["feedback"]
                    }
                    for q in question_results
                ]
            }
            report_file = REPORTS_DIR / f"evaluation_report_{eval_id}.json"
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, indent=4)
                report_path = str(report_file)
                logger.info(f"Evaluation report written to {report_path}")
            except Exception as e:
                logger.error(f"Failed to write evaluation report: {e}")

            # Record in DB (without HITL items)
            if db:
                rec = EvaluationRecord(
                    id=eval_id,
                    mode="evaluate",
                    ocr_provider=active_provider,
                    model_version=active_model,
                    total_marks=total_max_marks,
                    obtained_marks=total_obtained_marks,
                    percentage=percentage,
                    status="completed",
                    report_path=report_path
                )
                db.add(rec)
                db.commit()

        elif mode.lower() == "train":
            # Train Mode: Stage in HITL queue for human verification
            if db:
                rec = EvaluationRecord(
                    id=eval_id,
                    mode="train",
                    ocr_provider=active_provider,
                    model_version=active_model,
                    total_marks=total_max_marks,
                    obtained_marks=total_obtained_marks,
                    percentage=percentage,
                    status="in_review"
                )
                db.add(rec)
                db.commit()

                # Stage HITL review items
                hitl_items = hitl_service.create_pending_items(
                    evaluation_id=eval_id,
                    question_results=question_results,
                    key_answers=key_answers,
                    rubrics=rubrics,
                    student_answers=extracted_answers,
                    db=db
                )

                # Attach generated hitl_item_ids
                for idx, q_res in enumerate(question_results):
                    if idx < len(hitl_items):
                        q_res["hitl_item_id"] = hitl_items[idx].id

        return {
            "id": eval_id,
            "mode": mode.lower(),
            "ocr_provider": active_provider,
            "model": active_model,
            "total_marks": total_max_marks,
            "obtained_marks": total_obtained_marks,
            "percentage": percentage,
            "questions": question_results,
            "overall_summary": overall_summary,
            "report_path": report_path
        }

evaluator = ScriptSenseEvaluator()
