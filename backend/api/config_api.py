import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from backend.core.config import settings, REPORTS_DIR
from backend.models.schemas import ConfigResponse, ConfigUpdateRequest

router = APIRouter(prefix="/api", tags=["Configuration & Samples"])

@router.get("/config", response_model=ConfigResponse)
def get_system_configuration():
    """
    Returns non-sensitive system configuration, active OCR provider, and model info.
    Does NOT expose API keys to the frontend.
    """
    return ConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        ocr_provider=settings.OCR_PROVIDER,
        gemini_configured=bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        gemini_model=settings.GEMINI_MODEL,
        qwen_base_url=settings.QWEN_BASE_URL,
        qwen_model=settings.QWEN_MODEL,
        active_semantic_model=settings.ACTIVE_SEMANTIC_MODEL,
        min_training_samples=settings.MIN_TRAINING_SAMPLES
    )

@router.post("/config")
def update_system_configuration(req: ConfigUpdateRequest):
    """
    Allows runtime switching of OCR provider (Local Qwen vs Gemini API),
    active model version, or training threshold.
    """
    if req.ocr_provider:
        provider = req.ocr_provider.lower().strip()
        if provider in ["gemini", "qwen"]:
            settings.OCR_PROVIDER = provider
        else:
            raise HTTPException(status_code=400, detail="OCR provider must be 'gemini' or 'qwen'.")

    if req.active_semantic_model:
        settings.ACTIVE_SEMANTIC_MODEL = req.active_semantic_model.strip()

    if req.min_training_samples is not None and req.min_training_samples > 0:
        settings.MIN_TRAINING_SAMPLES = req.min_training_samples

    if req.gemini_api_key is not None:
        settings.GEMINI_API_KEY = req.gemini_api_key.strip()

    if req.gemini_model:
        settings.GEMINI_MODEL = req.gemini_model.strip()

    if req.qwen_base_url:
        settings.QWEN_BASE_URL = req.qwen_base_url.strip()

    if req.qwen_model:
        settings.QWEN_MODEL = req.qwen_model.strip()

    return {
        "success": True,
        "message": "Configuration updated successfully.",
        "config": get_system_configuration()
    }

@router.get("/evaluation/{id}")
def get_evaluation_report(id: str):
    """Retrieves a saved evaluation report by ID."""
    report_file = REPORTS_DIR / f"evaluation_report_{id}.json"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail=f"Report with ID '{id}' not found.")

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@router.get("/sample-data")
def get_sample_exam_data():
    """
    Returns pre-packaged sample exam questions, reference answers, rubrics,
    and student answers for 1-click testing of Evaluate and Train modes.
    """
    key_answers = {
        "1": (
            "Object-Oriented Programming (OOP) is a programming paradigm centered on objects containing data "
            "(attributes) and code (methods). The four fundamental principles are: 1. Encapsulation - bundling data "
            "and methods while restricting direct access. 2. Abstraction - hiding internal implementation complexity. "
            "3. Inheritance - creating new classes based on existing classes to reuse code. 4. Polymorphism - allowing "
            "entities to take on different forms depending on context."
        ),
        "2": (
            "Polymorphism allows objects of different classes to be treated as objects of a common superclass. "
            "The two main forms are: 1. Compile-time (Static) Polymorphism: Achieved via method overloading or operator "
            "overloading where method signatures differ. 2. Runtime (Dynamic) Polymorphism: Achieved via method overriding "
            "where a subclass provides a specific implementation of a method already declared in its parent class."
        ),
        "3": (
            "Exception handling is a structured programming mechanism to handle unexpected runtime errors gracefully "
            "without crashing the entire application. It separates error handling code from normal business logic. "
            "Core components include: try block to enclose vulnerable code, catch/except block to catch and handle the "
            "specific error, and finally block to ensure cleanup routines (like closing file streams) always execute."
        )
    }

    rubrics = {
        "1": {
            "max_marks": 5.0,
            "criteria": [
                {"criterion": "OOP Definition", "marks": 1.0},
                {"criterion": "Encapsulation & Abstraction", "marks": 2.0},
                {"criterion": "Inheritance & Polymorphism", "marks": 2.0}
            ]
        },
        "2": {
            "max_marks": 5.0,
            "criteria": [
                {"criterion": "Polymorphism Definition", "marks": 1.0},
                {"criterion": "Compile-time Overloading", "marks": 2.0},
                {"criterion": "Runtime Overriding", "marks": 2.0}
            ]
        },
        "3": {
            "max_marks": 5.0,
            "criteria": [
                {"criterion": "Purpose & Mechanism", "marks": 1.5},
                {"criterion": "Try and Catch Blocks", "marks": 2.0},
                {"criterion": "Finally Block & Cleanup", "marks": 1.5}
            ]
        }
    }

    student_answers_excellent = {
        "1": (
            "Object Oriented Programming (OOP) organizes software design around data or objects rather than functions. "
            "Its four foundational pillars are Encapsulation (binding data and functions together into a class), "
            "Abstraction (exposing only essential features while concealing implementation details), Inheritance "
            "(subclasses inheriting state and behavior from a parent class), and Polymorphism (ability of methods to "
            "behave differently based on the object instance)."
        ),
        "2": (
            "Polymorphism means 'many forms'. It enables a single interface to control access to a general class of actions. "
            "There are two types: Static/Compile-time polymorphism implemented through function or method overloading, "
            "and Dynamic/Runtime polymorphism implemented using virtual functions or method overriding in derived classes."
        ),
        "3": (
            "Exception handling is used to intercept runtime anomalies to prevent abnormal program termination. "
            "The program places critical code inside a try block. When an error occurs, an exception is raised and caught "
            "by the catch/except handler. A finally block always runs regardless of whether an exception occurred, ensuring "
            "resources are released."
        )
    }

    student_answers_partial = {
        "1": (
            "OOP is about using classes and objects. It has inheritance and encapsulation. Inheritance allows reusing code "
            "from another class."
        ),
        "2": (
            "Polymorphism is when a function has multiple names or forms. Overloading is one example."
        ),
        "3": (
            "Exception handling catches bugs using try and except blocks so the code does not stop running."
        )
    }

    return {
        "key_answers": key_answers,
        "rubrics": rubrics,
        "sample_student_answers_excellent": student_answers_excellent,
        "sample_student_answers_partial": student_answers_partial
    }
