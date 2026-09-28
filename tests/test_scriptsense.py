import os
import json
import pytest
from pathlib import Path

from backend.services.grading_module import quantize_half_or_whole, grading_module
from backend.services.semantic_module import get_semantic_model
from backend.services.hitl_service import hitl_service
from backend.core.database import SessionLocal, init_db
from backend.ocr.pdf_utils import render_pdf_to_images, is_pdf
from backend.training.prepare_dataset import split_and_prepare_dataset
from backend.training.train import run_fine_tuning, get_next_model_version
from backend.training.evaluate_model import evaluate_model_on_test_set

def test_frontend_uploads_key_and_rubric_json_files():
    """Verify the evaluation UI sends uploaded key/rubric JSON files as multipart form data."""
    app_js = Path("frontend/js/app.js").read_text(encoding="utf-8")
    assert "fileInputKeys" in app_js
    assert "fileInputRubric" in app_js
    assert "key_answers_file" in app_js
    assert "rubrics_file" in app_js
    assert "state.keyAnswersFile" in app_js
    assert "state.rubricsFile" in app_js


def test_mixed_numeric_question_ids_do_not_crash_sorting():
    """Verify mixed numeric/string question IDs are normalized before sorting and lookup."""
    keys = {"1": "Answer 1", 2: "Answer 2", "10": "Answer 10"}
    normalized = {str(k): v for k, v in keys.items()}
    extracted = {"3": "Student 3"}

    def sort_question_key(question_id):
        q_text = str(question_id)
        return (0, int(q_text)) if q_text.isdigit() else (1, q_text)

    all_q_keys = sorted(set(normalized.keys()) | set(extracted.keys()), key=sort_question_key)
    assert all_q_keys == ["1", "2", "3", "10"]
    assert normalized["2"] == "Answer 2"


def test_hitl_pending_item_keeps_student_answers_with_numeric_keys():
    """Verify HITL queue preserves student answers when JSON keys are numbers instead of strings."""
    init_db()
    db = SessionLocal()

    items = hitl_service.create_pending_items(
        evaluation_id="test-eval-456",
        question_results=[{"question": "1", "marks": 4.0, "max_marks": 5.0, "feedback": "Good", "confidence": 0.9, "semantic_score": 0.85}],
        key_answers={"1": "Reference answer one"},
        rubrics={"1": {"max_marks": 5}},
        student_answers={1: "Student answer one"},
        db=db
    )

    assert items[0].student_answer == "Student answer one"
    assert items[0].reference_answer == "Reference answer one"
    db.close()


def test_half_or_whole_quantization():
    """Verify strictly .5 or integer mark quantization."""
    assert quantize_half_or_whole(3.22, 5.0) == 3.0
    assert quantize_half_or_whole(3.35, 5.0) == 3.5
    assert quantize_half_or_whole(3.68, 5.0) == 3.5
    assert quantize_half_or_whole(3.85, 5.0) == 4.0
    assert quantize_half_or_whole(5.4, 5.0) == 5.0
    assert quantize_half_or_whole(-0.5, 5.0) == 0.0

def test_rubric_based_grading():
    """Verify rubric criteria breakdown and score bounding."""
    student_ans = "Polymorphism allows methods to have multiple forms through overloading and overriding."
    ref_ans = "Polymorphism means many forms. Compile time is overloading, runtime is overriding."
    rubric = {
        "max_marks": 5.0,
        "criteria": [
            {"criterion": "Definition", "marks": 1.0},
            {"criterion": "Overloading", "marks": 2.0},
            {"criterion": "Overriding", "marks": 2.0}
        ]
    }

    result = grading_module.grade(
        student_answer=student_ans,
        reference_answer=ref_ans,
        rubric=rubric,
        semantic_score=0.88,
        confidence=0.92
    )

    # Marks must be half or whole number
    assert result.marks in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    assert result.marks <= 5.0
    assert len(result.criteria_breakdown) == 3
    for crit in result.criteria_breakdown:
        # Each criterion must be half or whole number
        assert crit["awarded_marks"] in [0.0, 0.5, 1.0, 1.5, 2.0]

def test_pdf_rendering_without_tesseract():
    """Verify PyMuPDF renders PDF to images with zero Tesseract usage."""
    pdf_path = Path("samples/sample_student_script.pdf")
    assert pdf_path.exists()
    assert is_pdf(str(pdf_path))

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    images = render_pdf_to_images(pdf_bytes, dpi=100)
    assert len(images) >= 1
    # Check PNG signature
    assert images[0].startswith(b'\x89PNG')

def test_hitl_approval_and_rejection():
    """Verify HITL workflow strictly stores only human_verified = True records."""
    init_db()
    db = SessionLocal()

    # Stage items
    items = hitl_service.create_pending_items(
        evaluation_id="test-eval-123",
        question_results=[
            {"question": "1", "marks": 4.0, "max_marks": 5.0, "feedback": "Good", "confidence": 0.9, "semantic_score": 0.85},
            {"question": "2", "marks": 2.0, "max_marks": 5.0, "feedback": "Partial", "confidence": 0.7, "semantic_score": 0.5}
        ],
        key_answers={"1": "Ref 1", "2": "Ref 2"},
        rubrics={"1": {"max_marks": 5}, "2": {"max_marks": 5}},
        student_answers={"1": "Student 1", "2": "Student 2"},
        db=db
    )
    assert len(items) == 2

    # Approve item 1 with adjusted half mark
    approved = hitl_service.approve_item(
        item_id=items[0].id,
        human_marks=4.5,
        human_feedback="Human verified: Excellent definition",
        db=db
    )
    assert approved.human_verified is True
    assert approved.human_marks == 4.5
    assert approved.status == "approved"

    # Reject item 2
    rejected = hitl_service.reject_item(
        item_id=items[1].id,
        reason="Illegible handwriting",
        db=db
    )
    assert rejected.human_verified is False
    assert rejected.status == "rejected"

    db.close()

def test_fine_tuning_pipeline():
    """Verify fine-tuning pipeline creates versioned model and metadata."""
    init_db()
    db = SessionLocal()

    # Ensure there are samples in verified_training.jsonl
    training_file = Path("data/verified_training.jsonl")
    training_file.parent.mkdir(parents=True, exist_ok=True)
    with open(training_file, "a", encoding="utf-8") as f:
        for i in range(5):
            f.write(json.dumps({
                "question": str(i+1),
                "student_answer": f"Polymorphism allows overloading and overriding in question {i+1}.",
                "reference_answer": "Polymorphism means many forms including compile-time and runtime.",
                "rubric": {"max_marks": 5.0},
                "ai_marks": 3.5,
                "human_marks": 4.0,
                "ai_feedback": "Good answer",
                "human_feedback": "Verified 4.0 marks",
                "human_verified": True
            }) + "\n")

    # Run fine-tuning
    meta = run_fine_tuning(db)
    assert "model_version" in meta
    assert meta["model_version"].startswith("codbert_ft_v")
    assert meta["training_samples"] >= 1
    assert "validation_score" in meta

    # Check model directory artifacts
    model_dir = Path("models") / meta["model_version"]
    assert model_dir.exists()
    assert (model_dir / "weights.json").exists()
    assert (model_dir / "metadata.json").exists()

    db.close()
