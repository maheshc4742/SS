import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pathlib import Path

from backend.models.database_models import HITLItem, EvaluationRecord
from backend.services.grading_module import quantize_half_or_whole
from backend.core.config import settings, DATA_DIR

logger = logging.getLogger(__name__)
VERIFIED_TRAINING_FILE = DATA_DIR / "verified_training.jsonl"

class HITLService:
    """
    Manages the Human-in-the-Loop workflow.
    Ensures that only human-verified, approved records are stored as training data.
    """

    @staticmethod
    def create_pending_items(
        evaluation_id: str,
        question_results: List[Dict[str, Any]],
        key_answers: Dict[str, str],
        rubrics: Dict[str, Any],
        student_answers: Dict[str, str],
        db: Session
    ) -> List[HITLItem]:
        normalized_key_answers = {str(k): v for k, v in (key_answers or {}).items()}
        normalized_rubrics = {str(k): v for k, v in (rubrics or {}).items()}
        normalized_student_answers = {str(k): v for k, v in (student_answers or {}).items()}

        created_items = []
        for q_res in question_results:
            q_id = str(q_res["question"])
            s_ans = str(normalized_student_answers.get(q_id, ""))
            r_ans = str(normalized_key_answers.get(q_id, ""))
            rub = normalized_rubrics.get(q_id, {"max_marks": q_res.get("max_marks", 5)})

            item = HITLItem(
                evaluation_id=evaluation_id,
                question_id=q_id,
                question_text=f"Question {q_id}",
                student_answer=s_ans,
                reference_answer=r_ans,
                rubric_json=json.dumps(rub),
                ai_marks=q_res["marks"],
                ai_feedback=q_res.get("feedback", ""),
                confidence=q_res.get("confidence", 0.0),
                semantic_score=q_res.get("semantic_score", 0.0),
                human_marks=q_res["marks"],  # Pre-fill with AI prediction for convenience
                human_feedback=q_res.get("feedback", ""),
                status="pending",
                human_verified=False
            )
            db.add(item)
            created_items.append(item)

        db.commit()
        for item in created_items:
            db.refresh(item)
        return created_items

    @staticmethod
    def get_pending_items(db: Session) -> List[HITLItem]:
        return db.query(HITLItem).filter(HITLItem.status == "pending").order_by(HITLItem.created_at.desc()).all()

    @staticmethod
    def approve_item(
        item_id: int,
        human_marks: Optional[float],
        human_feedback: Optional[str],
        db: Session
    ) -> HITLItem:
        item = db.query(HITLItem).filter(HITLItem.id == item_id).first()
        if not item:
            raise ValueError(f"HITL item with ID {item_id} not found.")

        # Parse max_marks from rubric
        rubric_dict = json.loads(item.rubric_json) if item.rubric_json else {}
        max_m = float(rubric_dict.get("max_marks", 5.0))

        if human_marks is not None:
            item.human_marks = quantize_half_or_whole(human_marks, max_m)
        else:
            item.human_marks = quantize_half_or_whole(item.ai_marks, max_m)

        if human_feedback is not None:
            item.human_feedback = human_feedback.strip()
        elif not item.human_feedback:
            item.human_feedback = item.ai_feedback

        item.status = "approved"
        item.human_verified = True
        db.commit()
        db.refresh(item)

        # Append to verified_training.jsonl
        training_entry = {
            "question": item.question_id,
            "student_answer": item.student_answer,
            "reference_answer": item.reference_answer,
            "rubric": rubric_dict,
            "ai_marks": item.ai_marks,
            "human_marks": item.human_marks,
            "ai_feedback": item.ai_feedback,
            "human_feedback": item.human_feedback,
            "human_verified": True
        }

        try:
            with open(VERIFIED_TRAINING_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(training_entry) + "\n")
            logger.info(f"Appended verified item {item_id} to {VERIFIED_TRAINING_FILE}")
        except Exception as e:
            logger.error(f"Failed to write verified item to {VERIFIED_TRAINING_FILE}: {e}")

        return item

    @staticmethod
    def reject_item(item_id: int, reason: Optional[str], db: Session) -> HITLItem:
        item = db.query(HITLItem).filter(HITLItem.id == item_id).first()
        if not item:
            raise ValueError(f"HITL item with ID {item_id} not found.")

        item.status = "rejected"
        item.human_verified = False
        if reason:
            item.human_feedback = f"REJECTED: {reason}"
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_draft(
        item_id: int,
        human_marks: Optional[float],
        human_feedback: Optional[str],
        db: Session
    ) -> HITLItem:
        item = db.query(HITLItem).filter(HITLItem.id == item_id).first()
        if not item:
            raise ValueError(f"HITL item with ID {item_id} not found.")

        rubric_dict = json.loads(item.rubric_json) if item.rubric_json else {}
        max_m = float(rubric_dict.get("max_marks", 5.0))

        if human_marks is not None:
            item.human_marks = quantize_half_or_whole(human_marks, max_m)
        if human_feedback is not None:
            item.human_feedback = human_feedback.strip()

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get_training_stats(db: Session) -> Dict[str, Any]:
        # Count verified examples in database
        verified_count = db.query(HITLItem).filter(HITLItem.human_verified == True).count()
        pending_count = db.query(HITLItem).filter(HITLItem.status == "pending").count()
        min_threshold = int(settings.MIN_TRAINING_SAMPLES)

        # Also count lines in jsonl file if exists
        file_count = 0
        if VERIFIED_TRAINING_FILE.exists():
            with open(VERIFIED_TRAINING_FILE, "r", encoding="utf-8") as f:
                file_count = sum(1 for line in f if line.strip())

        effective_count = max(verified_count, file_count)
        is_ready = effective_count >= min_threshold

        return {
            "verified_count": effective_count,
            "min_threshold": min_threshold,
            "pending_count": pending_count,
            "is_ready": is_ready,
            "active_model": settings.ACTIVE_SEMANTIC_MODEL
        }

hitl_service = HITLService()
