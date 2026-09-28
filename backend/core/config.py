import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
UPLOADS_DIR = BASE_DIR / "uploads"

# Ensure directories exist
for d in [DATA_DIR, MODELS_DIR, REPORTS_DIR, UPLOADS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    # App
    APP_NAME: str = "ScriptSense"
    APP_VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # OCR Settings
    OCR_PROVIDER: str = Field(default="gemini", description="OCR provider: 'gemini' or 'qwen'")
    
    # Gemini API Settings
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    
    # Qwen Local Settings
    QWEN_BASE_URL: str = Field(default="http://127.0.0.1:1234/v1", description="Local Qwen endpoint")
    QWEN_MODEL: str = Field(default="qwen2-vl-7b-instruct", description="Local Qwen model name")
    QWEN_API_KEY: str = Field(default="not-needed", description="Local Qwen API key")
    
    # Semantic Model & HITL Settings
    ACTIVE_SEMANTIC_MODEL: str = Field(default="codbert_base", description="Active semantic scoring model")
    MIN_TRAINING_SAMPLES: int = Field(default=10, description="Minimum samples to unlock fine-tuning")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./data/scriptsense.db", description="Database connection URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
