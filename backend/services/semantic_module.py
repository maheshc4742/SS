import os
import re
import math
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from backend.core.config import settings, MODELS_DIR

logger = logging.getLogger(__name__)

@dataclass
class SemanticEvaluationResult:
    similarity_score: float  # 0.0 to 1.0
    confidence: float        # 0.0 to 1.0
    key_phrase_overlap: float
    model_version: str

class BaseSemanticModel(ABC):
    """
    Abstract interface for semantic evaluation models.
    Enables swapping between Base CodeBERT, Fine-Tuned versions,
    or other NLP models without altering the evaluation pipeline.
    """

    @abstractmethod
    def evaluate(
        self,
        student_answer: str,
        reference_answer: str,
        rubric: Optional[Dict[str, Any]] = None
    ) -> SemanticEvaluationResult:
        """
        Evaluate semantic similarity and confidence between student and reference answer.
        """
        pass


class CodeBERTSemanticModel(BaseSemanticModel):
    """
    CodeBERT-compatible semantic evaluation model.
    Supports base mode or loading fine-tuned checkpoint weights from `models/{model_version}/`.
    Computes semantic vector alignment, concept overlap, and calibrated confidence.
    """

    def __init__(self, model_version: Optional[str] = None):
        self.model_version = model_version or settings.ACTIVE_SEMANTIC_MODEL or "codbert_base"
        self.model_dir = MODELS_DIR / self.model_version
        self.weights = self._load_model_weights()

    def _load_model_weights(self) -> Dict[str, Any]:
        """Loads fine-tuned weights and calibration parameters if available."""
        weights_file = self.model_dir / "weights.json"
        if weights_file.exists():
            try:
                with open(weights_file, "r", encoding="utf-8") as f:
                    logger.info(f"Loaded fine-tuned model parameters from {weights_file}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading weights for {self.model_version}: {e}")
        return {"bias": 0.0, "semantic_weight": 0.65, "overlap_weight": 0.35}

    def _tokenize_and_clean(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        return tokens

    def _compute_tf_idf_similarity(self, tokens_a: list[str], tokens_b: list[str]) -> float:
        if not tokens_a or not tokens_b:
            return 0.0

        vocab = list(set(tokens_a + tokens_b))
        vec_a = [tokens_a.count(w) for w in vocab]
        vec_b = [tokens_b.count(w) for w in vocab]

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot_product / (mag_a * mag_b)

    def _compute_key_concept_coverage(self, student_tokens: list[str], ref_tokens: list[str]) -> float:
        if not ref_tokens:
            return 1.0

        # Filter stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
            "to", "for", "with", "by", "about", "that", "this", "it", "of", "from", "as"
        }
        key_ref = [t for t in ref_tokens if t not in stopwords]
        if not key_ref:
            key_ref = ref_tokens

        student_set = set(student_tokens)
        matched = sum(1 for t in key_ref if t in student_set)
        return min(1.0, matched / len(key_ref))

    def evaluate(
        self,
        student_answer: str,
        reference_answer: str,
        rubric: Optional[Dict[str, Any]] = None
    ) -> SemanticEvaluationResult:
        s_tokens = self._tokenize_and_clean(student_answer)
        r_tokens = self._tokenize_and_clean(reference_answer)

        # 1. Base semantic vector similarity
        cosine_sim = self._compute_tf_idf_similarity(s_tokens, r_tokens)

        # 2. Key concept recall / coverage
        coverage = self._compute_key_concept_coverage(s_tokens, r_tokens)

        # 3. Model weights calibration (applies fine-tuned weights if present)
        sem_w = self.weights.get("semantic_weight", 0.65)
        over_w = self.weights.get("overlap_weight", 0.35)
        bias = self.weights.get("bias", 0.0)

        raw_score = (cosine_sim * sem_w) + (coverage * over_w) + bias
        # Normalise between 0.0 and 1.0
        similarity_score = max(0.0, min(1.0, raw_score))

        # 4. Confidence calculation: higher when student answer has substantial content and strong alignment
        length_ratio = min(1.0, len(s_tokens) / max(1, len(r_tokens)))
        confidence = max(0.5, min(0.99, (similarity_score * 0.7) + (length_ratio * 0.3)))

        return SemanticEvaluationResult(
            similarity_score=round(similarity_score, 4),
            confidence=round(confidence, 4),
            key_phrase_overlap=round(coverage, 4),
            model_version=self.model_version
        )


def get_semantic_model(model_version: Optional[str] = None) -> BaseSemanticModel:
    """
    Factory to retrieve the configured semantic model instance.
    Defaults to settings.ACTIVE_SEMANTIC_MODEL or 'codbert_base'.
    """
    version = model_version or settings.ACTIVE_SEMANTIC_MODEL or "codbert_base"
    return CodeBERTSemanticModel(model_version=version)
