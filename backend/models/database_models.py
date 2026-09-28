import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String(36), primary_key=True, index=True)
    mode = Column(String(20), nullable=False, default="evaluate")  # 'evaluate' or 'train'
    ocr_provider = Column(String(50), nullable=False)
    model_version = Column(String(50), nullable=False)
    total_marks = Column(Float, default=0.0)
    obtained_marks = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    status = Column(String(20), default="completed")
    report_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    hitl_items = relationship("HITLItem", back_populates="evaluation", cascade="all, delete-orphan")


class HITLItem(Base):
    __tablename__ = "hitl_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    evaluation_id = Column(String(36), ForeignKey("evaluation_records.id"), nullable=False, index=True)
    question_id = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=True)
    student_answer = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=False)
    rubric_json = Column(Text, nullable=False)
    ai_marks = Column(Float, nullable=False)
    ai_feedback = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    semantic_score = Column(Float, default=0.0)
    human_marks = Column(Float, nullable=True)
    human_feedback = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # 'pending', 'approved', 'rejected'
    human_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    evaluation = relationship("EvaluationRecord", back_populates="hitl_items")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_version = Column(String(50), unique=True, nullable=False)
    training_samples = Column(Integer, default=0)
    validation_score = Column(Float, default=0.0)
    base_model = Column(String(50), default="codbert_base")
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
