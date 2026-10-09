# ScriptSense — AI-Based Descriptive Answer Evaluation with HITL Fine-Tuning

ScriptSense is a production-ready, modular web application for automated evaluation of descriptive, handwritten student answer scripts. It combines OCR vision models, semantic evaluation, rubric-based criteria grading, and a **Human-in-the-Loop (HITL)** training cycle.

---

## 🌟 Key Features

### 1. Dual Operational Modes
* **Evaluate Mode**:
  - Direct automated evaluation of student answer scripts (`.jpg`, `.jpeg`, `.png`, `.pdf`, `.json`).
  - Question-wise marks, semantic alignment, model confidence, criteria breakdown, and actionable feedback.
  - Generates downloadable structured evaluation reports (`reports/evaluation_report_<id>.json`).
  - **Zero HITL interaction** — no training data collection occurs in this mode.
* **Train Mode (HITL Continuous Improvement Loop)**:
  - Answers are extracted and scored by AI, then staged into the **HITL Review Queue**.
  - Human evaluators can inspect student answers vs reference answers, view rubrics and AI predictions, adjust marks using `+0.5` / `-0.5` steppers, refine feedback, and approve or reject questions.
  - **Strict Constraint**: Only `human_verified = true` evaluations are appended to `data/verified_training.jsonl`. Unverified or rejected evaluations are never used for training.
  - Unlocks model fine-tuning once the verified sample threshold (`MIN_TRAINING_SAMPLES`) is satisfied.

### 2. Pluggable Vision OCR (No Tesseract)
* **Local Qwen**: Integrates with locally running Qwen vision-language models (e.g. via LM Studio, vLLM, or Ollama) via an OpenAI-compatible vision chat completion endpoint.
* **Google Gemini API**: High-accuracy multimodal vision OCR via Gemini 2.5 Flash / Pro.
* **Zero Tesseract**: PDF files are rendered into high-resolution images using **PyMuPDF (`pymupdf`)** and processed natively by the vision model.
* **JSON Answer Scripts**: Automatically bypass OCR and proceed straight to semantic grading.

### 3. Rubric-Based Grading with 0.5 Quantization
* Evaluates descriptive answers using weighted sub-criteria or prose rubrics aligned with numbered answer-key points.
* **Fraction Rule**: Strictly keeps marks as **whole numbers or half-integers (`.5`)** (e.g., 0, 0.5, 1.0, 1.5 ... up to max marks).

### 4. Versioned Model Fine-Tuning Pipeline
* Separates verified data into **Train (70%)**, **Validation (15%)**, and **Test (15%)** splits.
* Automatically versions fine-tuned models (`models/codbert_ft_v1/`, `codbert_ft_v2/`, etc.) with `weights.json` and `metadata.json`.
* Instant runtime activation of any trained model checkpoint via the UI or API.

---

## 📁 Project Architecture

```text
ScriptSense/
├── backend/
│   ├── main.py                     # FastAPI application & lifecycle
│   ├── api/
│   │   ├── evaluate.py             # Evaluate Mode endpoints
│   │   ├── hitl.py                 # Train Mode & HITL endpoints
│   │   ├── training.py             # Training stats & fine-tuning trigger
│   │   ├── models_api.py           # Model registry & activation
│   │   └── config_api.py           # Dynamic application settings
│   ├── core/
│   │   ├── config.py               # Pydantic Settings & environment
│   │   └── database.py             # SQLite engine & sessionmaker
│   ├── models/
│   │   ├── database_models.py      # SQLAlchemy Evaluation, HITL, & Model tables
│   │   └── schemas.py              # Pydantic validation schemas
│   ├── services/
│   │   ├── evaluator.py            # Main evaluation orchestrator
│   │   ├── grading_module.py       # Rubric grading (.5 / whole numbers)
│   │   ├── semantic_module.py      # Pluggable semantic comparator & CodeBERT
│   │   └── hitl_service.py         # Human-in-the-Loop review & dataset logic
│   ├── ocr/
│   │   ├── base_ocr.py             # Abstract OCR provider interface
│   │   ├── gemini_ocr.py           # Google Gemini multimodal vision OCR
│   │   ├── qwen_ocr.py             # Local Qwen vision-language client
│   │   ├── ocr_factory.py          # OCR provider factory switch
│   │   └── pdf_utils.py            # PyMuPDF page rendering (No Tesseract)
│   └── training/
│       ├── dataset.py              # Verified JSONL dataset loader
│       ├── prepare_dataset.py      # Train/Val/Test 70-15-15 split
│       ├── train.py                # Fine-tuning engine & versioning
│       └── evaluate_model.py       # Test set benchmarking
├── frontend/
│   ├── index.html                  # Responsive SPA dashboard
│   ├── css/
│   │   └── styles.css              # Dark glassmorphic styling system
│   └── js/
│       └── app.js                  # Frontend controller & API interactions
├── data/
│   ├── scriptsense.db              # SQLite database
│   └── verified_training.jsonl     # Verified human annotations
├── models/
│   ├── codbert_base/               # Baseline model checkpoint
│   └── codbert_ft_v1/              # Fine-tuned model checkpoints
├── reports/                        # Saved evaluation JSON reports
├── tests/
│   └── test_scriptsense.py         # Pytest verification suite
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10+ (Tested on Python 3.13)

### 2. Setup Virtual Environment
```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure:
* `OCR_PROVIDER`: `gemini` or `qwen`
* `GEMINI_API_KEY`: Required for image/PDF OCR with Gemini. JSON answer scripts can be evaluated without OCR credentials.
* `GEMINI_MODEL`: Gemini model for OCR (default: `gemini-3.8-flash`).
* `QWEN_BASE_URL`: Local Qwen endpoint (e.g. `http://127.0.0.1:1234/v1`)
* `MIN_TRAINING_SAMPLES`: Threshold to enable fine-tuning (e.g. `10`)

### 5. Start the Server
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser at:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Interactive API docs available at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧪 Running Automated Tests

Run the test suite:
```bash
pytest tests/test_scriptsense.py -v
```

---

## 🔄 The Continuous Improvement Cycle

```text
       ┌──────────────────┐
       │ Student Script   │
       └────────┬─────────┘
                ↓
         OCR / JSON Input
                ↓
       Semantic Evaluation
                ↓
      Rubric-Based Grading
                │
     ┌──────────┴──────────┐
     │  Evaluate Mode?     │
     ├──────────┬──────────┤
     │ YES      │ NO       │
     ↓          ↓
Final Result  HITL Review (Human verifies/corrects marks)
Report Saved    ↓
              Verified Data (data/verified_training.jsonl)
                ↓
              Fine-Tuning Trigger (Train/Val/Test split)
                ↓
              Versioned Model (models/codbert_ft_v{N}/)
                ↓
              Active Model Deployed
```
