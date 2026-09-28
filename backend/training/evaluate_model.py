import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.config import DATA_DIR, MODELS_DIR
from backend.services.semantic_module import CodeBERTSemanticModel
from backend.services.grading_module import quantize_half_or_whole

logger = logging.getLogger(__name__)

def evaluate_model_on_test_set(
    model_version: str,
    test_file: Path = DATA_DIR / "test_split.jsonl"
) -> Dict[str, Any]:
    """
    Evaluates a specific model version on the held-out test split.
    Calculates Mean Absolute Error, accuracy, and test metrics.
    """
    if not test_file.exists():
        raise FileNotFoundError(f"Test split file {test_file} does not exist.")

    model = CodeBERTSemanticModel(model_version=model_version)
    test_samples = []

    with open(test_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_samples.append(json.loads(line.strip()))

    if not test_samples:
        return {"model_version": model_version, "test_samples": 0, "message": "Test set is empty."}

    errors = []
    exact_matches = 0

    for item in test_samples:
        s_ans = item["student_answer"]
        r_ans = item["reference_answer"]
        rub = item.get("rubric", {})
        max_m = float(rub.get("max_marks", 5.0))
        human_marks = float(item.get("human_marks", max_m))

        sem_res = model.evaluate(s_ans, r_ans, rub)
        pred_raw = max_m * sem_res.similarity_score
        pred_marks = quantize_half_or_whole(pred_raw, max_m)

        err = abs(pred_marks - human_marks)
        errors.append(err)
        if err <= 0.5:
            exact_matches += 1

    mae = sum(errors) / len(errors)
    accuracy_within_half_mark = (exact_matches / len(test_samples)) * 100

    report = {
        "model_version": model_version,
        "test_samples": len(test_samples),
        "mean_absolute_error": round(mae, 4),
        "accuracy_within_0_5_marks": round(accuracy_within_half_mark, 2),
        "test_score": round(max(0.0, 1.0 - (mae / 5.0)), 4)
    }

    logger.info(f"Test Evaluation for {model_version}: {report}")
    return report
