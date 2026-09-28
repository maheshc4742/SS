from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

class CriterionItem(BaseModel):
    criterion: str
    marks: float

class QuestionRubric(BaseModel):
    max_marks: float
    criteria: List[CriterionItem] = []

class EvaluationRequest(BaseModel):
    mode: str = Field(default="evaluate", description="'evaluate' or 'train'")
    key_answers: Dict[str, str] = Field(description="Dictionary mapping question numbers to reference answers")
    rubrics: Dict[str, Any] = Field(description="Dictionary mapping question numbers to rubric specifications")
    student_answers: Optional[Dict[str, str]] = Field(default=None, description="Direct JSON student answers if bypassing OCR")
    ocr_provider: Optional[str] = Field(default=None, description="Override OCR provider ('gemini' or 'qwen')")
    model_version: Optional[str] = Field(default=None, description="Override active semantic model")

class QuestionResult(BaseModel):
    question: str
    marks: float
    max_marks: float
    semantic_score: float
    confidence: float
    feedback: str
    criteria_breakdown: Optional[List[Dict[str, Any]]] = None
    student_answer: Optional[str] = None
    reference_answer: Optional[str] = None
    hitl_item_id: Optional[int] = None

    @field_validator("marks")
    @classmethod
    def validate_half_or_whole(cls, v: float) -> float:
        # Enforce half-point (.5) or integer marks
        return round(v * 2) / 2

class EvaluationResponse(BaseModel):
    id: str
    mode: str
    ocr_provider: str
    model: str
    total_marks: float
    obtained_marks: float
    percentage: float
    questions: List[QuestionResult]
    overall_summary: str
    report_path: Optional[str] = None

class HITLItemResponse(BaseModel):
    id: int
    evaluation_id: str
    question_id: str
    question_text: Optional[str] = None
    student_answer: str
    reference_answer: str
    rubric: Dict[str, Any]
    ai_marks: float
    ai_feedback: Optional[str] = None
    confidence: float
    semantic_score: float
    human_marks: Optional[float] = None
    human_feedback: Optional[str] = None
    status: str
    human_verified: bool
    created_at: str

class HITLApproveRequest(BaseModel):
    id: int
    human_marks: Optional[float] = None
    human_feedback: Optional[str] = None

    @field_validator("human_marks")
    @classmethod
    def validate_half_or_whole(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            return round(v * 2) / 2
        return v

class HITLRejectRequest(BaseModel):
    id: int
    reason: Optional[str] = None

class HITLUpdateRequest(BaseModel):
    human_marks: Optional[float] = None
    human_feedback: Optional[str] = None

    @field_validator("human_marks")
    @classmethod
    def validate_half_or_whole(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            return round(v * 2) / 2
        return v

class TrainingStatsResponse(BaseModel):
    verified_count: int
    min_threshold: int
    pending_count: int
    is_ready: bool
    active_model: str

class ModelItem(BaseModel):
    model_version: str
    training_samples: int
    validation_score: float
    created_at: str
    base_model: str
    is_active: bool

class ModelActivateRequest(BaseModel):
    model_version: str

class ConfigResponse(BaseModel):
    app_name: str
    app_version: str
    ocr_provider: str
    gemini_configured: bool
    gemini_model: str
    qwen_base_url: str
    qwen_model: str
    active_semantic_model: str
    min_training_samples: int

class ConfigUpdateRequest(BaseModel):
    ocr_provider: Optional[str] = None
    active_semantic_model: Optional[str] = None
    min_training_samples: Optional[int] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    qwen_base_url: Optional[str] = None
    qwen_model: Optional[str] = None
