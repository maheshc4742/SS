import os
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.core.config import settings, MODELS_DIR, DATA_DIR, REPORTS_DIR, UPLOADS_DIR
from backend.core.database import init_db
from backend.api.evaluate import router as evaluate_router
from backend.api.hitl import router as hitl_router
from backend.api.training import router as training_router
from backend.api.models_api import router as models_router
from backend.api.config_api import router as config_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ScriptSense")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB and base models exist
    logger.info("Initializing ScriptSense database and models...")
    init_db()

    # Ensure codbert_base model metadata exists
    base_dir = MODELS_DIR / "codbert_base"
    base_dir.mkdir(parents=True, exist_ok=True)
    base_meta = base_dir / "metadata.json"
    if not base_meta.exists():
        with open(base_meta, "w", encoding="utf-8") as f:
            json.dump({
                "model_version": "codbert_base",
                "training_samples": 0,
                "validation_score": 0.8250,
                "created_at": "2026-01-01T00:00:00",
                "base_model": "codbert_base"
            }, f, indent=4)

    logger.info(f"ScriptSense startup complete. Active OCR Provider: {settings.OCR_PROVIDER}, Active Model: {settings.ACTIVE_SEMANTIC_MODEL}")
    yield
    logger.info("ScriptSense shutting down.")

app = FastAPI(
    title="ScriptSense API",
    description="AI-Based Answer Evaluation with HITL Fine-Tuning & Pluggable OCR",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(evaluate_router)
app.include_router(hitl_router)
app.include_router(training_router)
app.include_router(models_router)
app.include_router(config_router)

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Welcome to ScriptSense API. Visit /docs for OpenAPI documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
