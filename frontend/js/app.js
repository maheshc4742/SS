/**
 * ScriptSense Application Logic
 * Modern async client connecting to FastAPI backend
 */

// Application State
const state = {
  currentMode: 'evaluate',
  selectedFile: null,
  keyAnswersFile: null,
  rubricsFile: null,
  studentJsonFile: null,
  sampleData: null,
  config: null,
  trainingStats: { verified_count: 0, min_threshold: 10, pending_count: 0, is_ready: false },
  lastEvaluation: null
};

// DOM Elements
const elements = {
  modeBtnEval: document.getElementById('mode-btn-evaluate'),
  modeBtnTrain: document.getElementById('mode-btn-train'),
  viewEval: document.getElementById('view-evaluate'),
  viewTrain: document.getElementById('view-train'),

  // Top Bar Status
  pillOcr: document.getElementById('pill-ocr'),
  lblOcrProvider: document.getElementById('lbl-ocr-provider'),
  ocrDot: document.getElementById('ocr-dot'),
  pillModel: document.getElementById('pill-model'),
  lblActiveModel: document.getElementById('lbl-active-model'),
  pillTraining: document.getElementById('pill-training'),
  lblTrainingStats: document.getElementById('lbl-training-stats'),
  trainingDot: document.getElementById('training-dot'),

  // Dropzone & File
  dropzoneEval: document.getElementById('dropzone-eval'),
  fileInputEval: document.getElementById('file-input-eval'),
  filePillEval: document.getElementById('file-pill-eval'),
  filenameDisplayEval: document.getElementById('filename-display-eval'),
  btnRemoveFileEval: document.getElementById('btn-remove-file-eval'),

  // Key Answers File Selector & Editor
  fileInputKeys: document.getElementById('file-input-keys'),
  btnSelectKeyFile: document.getElementById('btn-select-key-file'),
  keyFileStatus: document.getElementById('key-file-status'),
  lblKeyFileTag: document.getElementById('lbl-key-file-tag'),
  editorKeyAnswers: document.getElementById('editor-key-answers'),

  // Rubrics File Selector & Editor
  fileInputRubric: document.getElementById('file-input-rubric'),
  btnSelectRubricFile: document.getElementById('btn-select-rubric-file'),
  rubricFileStatus: document.getElementById('rubric-file-status'),
  lblRubricFileTag: document.getElementById('lbl-rubric-file-tag'),
  editorRubrics: document.getElementById('editor-rubrics'),

  // Student Answers File Selector & Editor
  fileInputStudentJson: document.getElementById('file-input-student-json'),
  btnSelectStudentJsonFile: document.getElementById('btn-select-student-json-file'),
  studentJsonFileStatus: document.getElementById('student-json-file-status'),
  lblStudentFileTag: document.getElementById('lbl-student-file-tag'),
  editorStudentAnswers: document.getElementById('editor-student-answers'),

  // Presets
  btnPresetOop: document.getElementById('btn-preset-oop'),
  btnPresetHigh: document.getElementById('btn-preset-answers-high'),
  btnPresetPartial: document.getElementById('btn-preset-answers-partial'),
  btnQuickStart: document.getElementById('btn-quick-start'),

  // Evaluate Action & Results
  btnRunEvaluate: document.getElementById('btn-run-evaluate'),
  resultsEmptyState: document.getElementById('results-empty-state'),
  resultsActiveContainer: document.getElementById('results-active-container'),
  resObtainedMarks: document.getElementById('res-obtained-marks'),
  resTotalMarks: document.getElementById('res-total-marks'),
  resPercentage: document.getElementById('res-percentage'),
  resTierTitle: document.getElementById('res-tier-title'),
  resOverallSummary: document.getElementById('res-overall-summary'),
  btnDownloadReport: document.getElementById('btn-download-report'),
  questionsCardsList: document.getElementById('questions-cards-list'),

  // HITL Studio
  trainingProgressFill: document.getElementById('training-progress-fill'),
  trainingProgressText: document.getElementById('training-progress-text'),
  lblTrainReadiness: document.getElementById('lbl-train-readiness'),
  btnStartFinetune: document.getElementById('btn-start-finetune'),
  btnSeedSamples: document.getElementById('btn-seed-samples'),
  btnStageSampleTrain: document.getElementById('btn-stage-sample-train'),
  btnRefreshPending: document.getElementById('btn-refresh-pending'),
  lblPendingBadge: document.getElementById('lbl-pending-badge'),
  hitlEmptyState: document.getElementById('hitl-empty-state'),
  hitlItemsContainer: document.getElementById('hitl-items-container'),

  // Modal
  modalSettings: document.getElementById('modal-settings'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  ocrChoiceGemini: document.getElementById('ocr-choice-gemini'),
  ocrChoiceQwen: document.getElementById('ocr-choice-qwen'),
  modelsTableContainer: document.getElementById('models-table-container'),
  btnSaveSettings: document.getElementById('btn-save-settings'),

  // Toast
  toastContainer: document.getElementById('toast-container')
};

// ==========================================
// Toast Notification Utility
// ==========================================
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function formatFileLabel(file) {
  if (!file) return 'No file chosen';
  const sizeKB = (file.size / 1024).toFixed(1);
  return `${file.name} (${sizeKB} KB)`;
}

function readTextFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
    reader.readAsText(file);
  });
}

async function handleJsonFileSelection(file, target, labelElement, statusElement, editorElement, fieldName) {
  if (!file) return;

  try {
    const text = await readTextFile(file);
    JSON.parse(text);

    if (target === 'key') {
      state.keyAnswersFile = file;
      elements.lblKeyFileTag.textContent = 'Loaded';
      elements.keyFileStatus.textContent = formatFileLabel(file);
    } else if (target === 'rubric') {
      state.rubricsFile = file;
      elements.lblRubricFileTag.textContent = 'Loaded';
      elements.rubricFileStatus.textContent = formatFileLabel(file);
    } else if (target === 'student') {
      state.studentJsonFile = file;
      elements.lblStudentFileTag.textContent = 'Loaded';
      elements.studentJsonFileStatus.textContent = formatFileLabel(file);
    }

    editorElement.value = text;
    showToast(`${fieldName} file loaded successfully`, 'success');
  } catch (err) {
    showToast(`Invalid JSON in ${fieldName} file. Please select a valid .json file.`, 'error');
    console.error(err);
  }
}

// ==========================================
// Initialization & Data Loading
// ==========================================
async function initApp() {
  setupEventListeners();
  await loadSystemConfig();
  await loadSampleData();
  await loadTrainingStats();
  if (state.currentMode === 'train') {
    await loadPendingHitlItems();
  }
}

async function loadSystemConfig() {
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      state.config = await res.json();
      updateConfigUI();
    }
  } catch (err) {
    console.error('Failed to load system config:', err);
  }
}

function updateConfigUI() {
  if (!state.config) return;
  const provider = (state.config.ocr_provider || 'gemini').toUpperCase();
  elements.lblOcrProvider.textContent = provider;
  elements.lblActiveModel.textContent = state.config.active_semantic_model || 'codbert_base';

  if (state.config.ocr_provider === 'gemini') {
    elements.ocrDot.className = 'status-dot dot-indigo';
    elements.ocrChoiceGemini.checked = true;
  } else {
    elements.ocrDot.className = 'status-dot dot-green';
    elements.ocrChoiceQwen.checked = true;
  }
}

async function loadSampleData() {
  try {
    const res = await fetch('/api/sample-data');
    if (res.ok) {
      state.sampleData = await res.json();
      // Pre-fill key answers & rubrics
      elements.editorKeyAnswers.value = JSON.stringify(state.sampleData.key_answers, null, 2);
      elements.editorRubrics.value = JSON.stringify(state.sampleData.rubrics, null, 2);
      elements.editorStudentAnswers.value = JSON.stringify(state.sampleData.sample_student_answers_excellent, null, 2);
    }
  } catch (err) {
    console.error('Failed to load sample data:', err);
  }
}

async function loadTrainingStats() {
  try {
    const res = await fetch('/api/training/stats');
    if (res.ok) {
      state.trainingStats = await res.json();
      updateTrainingStatsUI();
    }
  } catch (err) {
    console.error('Failed to load training stats:', err);
  }
}

function updateTrainingStatsUI() {
  const { verified_count, min_threshold, pending_count, is_ready } = state.trainingStats;
  elements.lblTrainingStats.textContent = `${verified_count}/${min_threshold}`;
  elements.trainingProgressText.textContent = `Verified Training Samples: ${verified_count} / ${min_threshold}`;

  const pct = Math.min(100, Math.round((verified_count / min_threshold) * 100));
  elements.trainingProgressFill.style.width = `${pct}%`;

  if (is_ready) {
    elements.lblTrainReadiness.textContent = 'Ready for Fine-Tuning';
    elements.lblTrainReadiness.className = 'status-tag fully-met';
    elements.btnStartFinetune.disabled = false;
    elements.trainingDot.className = 'status-dot dot-green';
  } else {
    elements.lblTrainReadiness.textContent = 'Collecting Annotations';
    elements.lblTrainReadiness.className = 'status-tag partially-met';
    elements.btnStartFinetune.disabled = true;
    elements.trainingDot.className = 'status-dot dot-amber';
  }

  elements.lblPendingBadge.textContent = `${pending_count} Pending`;
}

// ==========================================
// Mode Switching
// ==========================================
function setMode(mode) {
  state.currentMode = mode;
  if (mode === 'evaluate') {
    elements.modeBtnEval.classList.add('active');
    elements.modeBtnTrain.classList.remove('active');
    elements.viewEval.classList.add('active');
    elements.viewTrain.classList.remove('active');
  } else {
    elements.modeBtnTrain.classList.add('active');
    elements.modeBtnEval.classList.remove('active');
    elements.viewTrain.classList.add('active');
    elements.viewEval.classList.remove('active');
    loadPendingHitlItems();
  }
}

// ==========================================
// Evaluate Mode Logic
// ==========================================
async function runEvaluation() {
  elements.btnRunEvaluate.disabled = true;
  elements.btnRunEvaluate.innerHTML = `
    <span style="display:inline-block; animation:spin 1s linear infinite;">⏳</span>
    <span>Evaluating Descriptive Script...</span>
  `;

  try {
    let keyAnswersJson = elements.editorKeyAnswers.value.trim();
    let rubricsJson = elements.editorRubrics.value.trim();
    let studentJson = elements.editorStudentAnswers.value.trim();

    if (!keyAnswersJson || !rubricsJson) {
      showToast('Key answers and rubrics must be provided.', 'error');
      return;
    }

    let result;
    if (state.selectedFile) {
      // Multipart upload with file
      const formData = new FormData();
      formData.append('file', state.selectedFile);
      if (state.keyAnswersFile) {
        formData.append('key_answers_file', state.keyAnswersFile);
      } else {
        formData.append('key_answers', keyAnswersJson);
      }
      if (state.rubricsFile) {
        formData.append('rubrics_file', state.rubricsFile);
      } else {
        formData.append('rubrics', rubricsJson);
      }
      if (state.studentJsonFile) {
        formData.append('student_answers_file', state.studentJsonFile);
      } else if (studentJson) {
        formData.append('student_answers', studentJson);
      }

      const res = await fetch('/api/evaluate', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Evaluation failed');
      }
      result = await res.json();
    } else {
      // Direct JSON evaluation
      let parsedStudent = {};
      if (studentJson) {
        try { parsedStudent = JSON.parse(studentJson); } catch (e) { throw new Error('Invalid student answers JSON format'); }
      } else {
        throw new Error('Please upload an answer script file or enter Student Answers JSON.');
      }

      const res = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'evaluate',
          key_answers: JSON.parse(keyAnswersJson),
          rubrics: JSON.parse(rubricsJson),
          student_answers: parsedStudent
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Evaluation failed');
      }
      result = await res.json();
    }

    state.lastEvaluation = result;
    renderEvaluationResults(result);
    showToast(`Evaluation completed! Score: ${result.obtained_marks}/${result.total_marks}`, 'success');

  } catch (err) {
    showToast(err.message, 'error');
    console.error(err);
  } finally {
    elements.btnRunEvaluate.disabled = false;
    elements.btnRunEvaluate.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      <span>Run Automated Evaluation</span>
    `;
  }
}

function renderEvaluationResults(res) {
  elements.resultsEmptyState.style.display = 'none';
  elements.resultsActiveContainer.style.display = 'block';

  // Format marks cleanly
  elements.resObtainedMarks.textContent = formatMarks(res.obtained_marks);
  elements.resTotalMarks.textContent = `/ ${formatMarks(res.total_marks)} marks`;
  elements.resPercentage.textContent = `${res.percentage}%`;

  if (res.percentage >= 80) {
    elements.resTierTitle.textContent = '🌟 Excellent Performance (Distinction)';
    elements.resPercentage.style.color = '#10b981';
  } else if (res.percentage >= 60) {
    elements.resTierTitle.textContent = '👍 Good Understanding (First Class)';
    elements.resPercentage.style.color = '#06b6d4';
  } else if (res.percentage >= 40) {
    elements.resTierTitle.textContent = '⚠️ Average Response (Passing)';
    elements.resPercentage.style.color = '#f59e0b';
  } else {
    elements.resTierTitle.textContent = '❌ Needs Improvement';
    elements.resPercentage.style.color = '#f43f5e';
  }

  elements.resOverallSummary.textContent = res.overall_summary;

  // Render question breakdown
  elements.questionsCardsList.innerHTML = '';
  res.questions.forEach(q => {
    const card = document.createElement('div');
    card.className = 'q-card glass';

    const semPct = Math.round((q.semantic_score || 0) * 100);
    const confPct = Math.round((q.confidence || 0) * 100);

    // Criteria breakdown items
    let criteriaHtml = '';
    if (q.criteria_breakdown && q.criteria_breakdown.length > 0) {
      criteriaHtml = `
        <div class="criteria-list">
          <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-dim); margin-bottom:0.3rem;">
            Rubric Criteria Assessment (.5 or whole marks):
          </div>
          ${q.criteria_breakdown.map(c => `
            <div class="criterion-row">
              <span>${c.criterion} (${formatMarks(c.awarded_marks)}/${formatMarks(c.max_marks)} pts)</span>
              <span class="status-tag ${c.status === 'Fully Met' ? 'fully-met' : (c.status === 'Partially Met' ? 'partially-met' : 'not-met')}">
                ${c.status}
              </span>
            </div>
          `).join('')}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="q-header">
        <div class="q-num">Question ${q.question}</div>
        <div class="marks-badge">${formatMarks(q.marks)} / ${formatMarks(q.max_marks)} Marks</div>
      </div>

      <div class="metrics-row">
        <div class="metric-chip">
          <span>Semantic Alignment:</span>
          <div class="chip-bar"><div class="chip-fill" style="width:${semPct}%"></div></div>
          <strong>${semPct}%</strong>
        </div>
        <div class="metric-chip">
          <span>Model Confidence:</span>
          <div class="chip-bar"><div class="chip-fill" style="width:${confPct}%; background:linear-gradient(90deg, #10b981, #06b6d4);"></div></div>
          <strong>${confPct}%</strong>
        </div>
      </div>

      ${q.student_answer ? `
        <div class="answer-box">
          <div class="answer-label">Student Answer</div>
          <div>${q.student_answer}</div>
        </div>
      ` : ''}

      ${q.reference_answer ? `
        <div class="answer-box ref-box">
          <div class="answer-label">Reference Answer</div>
          <div>${q.reference_answer}</div>
        </div>
      ` : ''}

      <div class="feedback-box">
        <strong>Feedback:</strong> ${q.feedback}
      </div>

      ${criteriaHtml}
    `;
    elements.questionsCardsList.appendChild(card);
  });
}

function formatMarks(val) {
  if (val === undefined || val === null) return '0';
  const num = Number(val);
  return Number.isInteger(num) ? num.toString() : num.toFixed(1);
}

// ==========================================
// Train Mode & HITL Studio Logic
// ==========================================
async function stageSampleForTrain() {
  try {
    elements.btnStageSampleTrain.disabled = true;
    elements.btnStageSampleTrain.textContent = 'Staging in HITL Queue...';

    const keyAnswers = JSON.parse(elements.editorKeyAnswers.value);
    const rubrics = JSON.parse(elements.editorRubrics.value);
    const studentAnswers = state.sampleData ? state.sampleData.sample_student_answers_partial : {};

    const res = await fetch('/api/train/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: 'train',
        key_answers: keyAnswers,
        rubrics: rubrics,
        student_answers: studentAnswers
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Staging failed');
    }

    const data = await res.json();
    showToast(`Staged ${data.questions.length} questions for Human Review!`, 'success');
    await loadPendingHitlItems();
    await loadTrainingStats();

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    elements.btnStageSampleTrain.disabled = false;
    elements.btnStageSampleTrain.textContent = 'Stage OOP Sample Script for Review';
  }
}

async function loadPendingHitlItems() {
  try {
    const res = await fetch('/api/hitl/pending');
    if (res.ok) {
      const items = await res.json();
      renderHitlPendingQueue(items);
    }
  } catch (err) {
    console.error('Failed to load pending HITL items:', err);
  }
}

function renderHitlPendingQueue(items) {
  elements.lblPendingBadge.textContent = `${items.length} Pending`;
  elements.hitlItemsContainer.innerHTML = '';

  if (!items || items.length === 0) {
    elements.hitlEmptyState.style.display = 'block';
    return;
  }

  elements.hitlEmptyState.style.display = 'none';

  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'hitl-card glass';
    card.id = `hitl-card-${item.id}`;

    const maxMarks = item.rubric.max_marks || 5;
    const aiMarks = item.ai_marks;
    const initialHumanMarks = item.human_marks !== null ? item.human_marks : aiMarks;
    const initialHumanFeedback = item.human_feedback || item.ai_feedback || '';

    card.innerHTML = `
      <div class="q-header">
        <div style="display:flex; align-items:center; gap:0.6rem;">
          <div class="q-num">Question ${item.question_id}</div>
          <span class="status-tag partially-met">Pending Human Verification</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-muted);">
          Max Marks: <strong>${maxMarks}</strong>
        </div>
      </div>

      <div class="answer-box">
        <div class="answer-label">Extracted Student Answer</div>
        <div>${item.student_answer}</div>
      </div>

      <div class="answer-box ref-box">
        <div class="answer-label">Reference / Key Answer</div>
        <div>${item.reference_answer}</div>
      </div>

      <div class="hitl-controls-grid">
        <!-- AI Prediction Summary -->
        <div style="background: rgba(0,0,0,0.18); padding: 1rem; border-radius: var(--radius-sm);">
          <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-dim); margin-bottom:0.4rem;">
            AI Evaluation
          </div>
          <div style="font-size: 1.1rem; font-weight:700; color:var(--primary-light); margin-bottom:0.4rem;">
            Predicted Marks: ${formatMarks(aiMarks)} / ${maxMarks}
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.5rem;">
            Confidence: ${(item.confidence * 100).toFixed(0)}% • Semantic Similarity: ${(item.semantic_score * 100).toFixed(0)}%
          </div>
          <div style="font-size:0.82rem; color:#cbd5e1;">
            <strong>AI Feedback:</strong> ${item.ai_feedback || 'N/A'}
          </div>
        </div>

        <!-- Human Verification & Correction -->
        <div class="human-edit-section">
          <div style="font-size:0.75rem; text-transform:uppercase; color:var(--accent-cyan); font-weight:700;">
            Human Evaluator Marks (.5 or whole numbers)
          </div>

          <div class="stepper-row">
            <button type="button" class="stepper-btn" onclick="stepMarks(${item.id}, -0.5, ${maxMarks})">-0.5</button>
            <input type="number" step="0.5" min="0" max="${maxMarks}" class="marks-input" id="human-marks-${item.id}" value="${formatMarks(initialHumanMarks)}">
            <button type="button" class="stepper-btn" onclick="stepMarks(${item.id}, 0.5, ${maxMarks})">+0.5</button>
            <span style="font-size:0.85rem; color:var(--text-dim);">/ ${maxMarks} marks</span>
          </div>

          <div style="margin-top:0.75rem;">
            <label style="font-size:0.75rem; text-transform:uppercase; color:var(--text-dim); font-weight:700;">
              Human Verified Feedback:
            </label>
            <textarea class="human-feedback-input" id="human-feedback-${item.id}">${initialHumanFeedback}</textarea>
          </div>
        </div>
      </div>

      <div class="hitl-action-bar">
        <button type="button" class="btn-reject" onclick="rejectItem(${item.id})">
          ✕ Reject
        </button>
        <button type="button" class="btn-approve" onclick="approveItem(${item.id})">
          ✓ Approve & Add to Training Data
        </button>
      </div>
    `;

    elements.hitlItemsContainer.appendChild(card);
  });
}

// Stepper function exposed to window
window.stepMarks = function(itemId, delta, maxMarks) {
  const input = document.getElementById(`human-marks-${itemId}`);
  if (!input) return;
  let val = parseFloat(input.value) || 0;
  val = Math.max(0, Math.min(maxMarks, val + delta));
  // Keep fraction .5 or whole number
  val = Math.round(val * 2) / 2;
  input.value = formatMarks(val);
};

// Approve item exposed to window
window.approveItem = async function(itemId) {
  const marksInput = document.getElementById(`human-marks-${itemId}`);
  const feedbackInput = document.getElementById(`human-feedback-${itemId}`);

  const humanMarks = marksInput ? parseFloat(marksInput.value) : null;
  const humanFeedback = feedbackInput ? feedbackInput.value : '';

  try {
    const res = await fetch('/api/hitl/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: itemId,
        human_marks: humanMarks,
        human_feedback: humanFeedback
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to approve item');
    }

    const card = document.getElementById(`hitl-card-${itemId}`);
    if (card) {
      card.classList.add('approved');
      card.style.opacity = '0.5';
      card.innerHTML = `
        <div style="text-align:center; padding:1.5rem; color:#10b981; font-weight:700;">
          ✓ Approved! Marks: ${humanMarks} • Added to Verified Training Dataset
        </div>
      `;
      setTimeout(() => card.remove(), 1200);
    }

    showToast('Verified example added to training data!', 'success');
    await loadTrainingStats();

  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Reject item exposed to window
window.rejectItem = async function(itemId) {
  try {
    const res = await fetch('/api/hitl/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: itemId, reason: 'Rejected by human evaluator' })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to reject item');
    }

    const card = document.getElementById(`hitl-card-${itemId}`);
    if (card) {
      card.classList.add('rejected');
      card.style.opacity = '0.5';
      card.innerHTML = `
        <div style="text-align:center; padding:1.5rem; color:#f43f5e; font-weight:700;">
          ✕ Rejected (Not added to training data)
        </div>
      `;
      setTimeout(() => card.remove(), 1200);
    }

    showToast('Item rejected. Will NOT be used for training.', 'info');
    await loadTrainingStats();

  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Fine-Tuning Execution
async function startFineTuning() {
  elements.btnStartFinetune.disabled = true;
  elements.btnStartFinetune.innerHTML = `
    <span style="display:inline-block; animation:spin 1s linear infinite;">⚙️</span>
    <span>Fine-Tuning Checkpoint...</span>
  `;

  try {
    const res = await fetch('/api/training/start?force=true', { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Fine-tuning failed');
    }
    const data = await res.json();
    const meta = data.metadata;
    showToast(`Fine-tuning complete! Created ${meta.model_version} (Val Score: ${meta.validation_score})`, 'success');

    // Automatically prompt activation
    await activateModel(meta.model_version);
    await loadSystemConfig();
    await loadTrainingStats();

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    elements.btnStartFinetune.disabled = false;
    elements.btnStartFinetune.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      <span>Start Fine-Tuning</span>
    `;
  }
}

// Seed Demo Samples for testing fine-tuning without typing 10 times
async function seedDemoSamples() {
  try {
    for (let i = 0; i < 4; i++) {
      await stageSampleForTrain();
      const res = await fetch('/api/hitl/pending');
      const items = await res.json();
      for (const it of items) {
        await window.approveItem(it.id);
      }
    }
    showToast('Seeded verified training samples! Ready for fine-tuning.', 'success');
    await loadTrainingStats();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// Models & Settings Modal
// ==========================================
async function openSettingsModal() {
  elements.modalSettings.classList.add('active');
  await renderModelsList();
}

function closeSettingsModal() {
  elements.modalSettings.classList.remove('active');
}

async function renderModelsList() {
  try {
    const res = await fetch('/api/models');
    if (!res.ok) return;
    const models = await res.json();

    elements.modelsTableContainer.innerHTML = `
      <table style="width:100%; font-size:0.85rem; border-collapse:collapse;">
        <thead>
          <tr style="text-align:left; border-bottom:1px solid var(--border-glass); color:var(--text-dim);">
            <th style="padding:0.5rem 0;">Version</th>
            <th>Samples</th>
            <th>Val Score</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${models.map(m => `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
              <td style="padding:0.55rem 0; font-weight:600; color:#fff;">${m.model_version}</td>
              <td>${m.training_samples}</td>
              <td>${(m.validation_score * 100).toFixed(1)}%</td>
              <td>
                ${m.is_active ? '<span class="status-tag fully-met">Active</span>' : '<span style="color:var(--text-dim);">Standby</span>'}
              </td>
              <td>
                ${!m.is_active ? `
                  <button class="btn-preset" onclick="activateModel('${m.model_version}')" style="padding:2px 8px;">
                    Activate
                  </button>
                ` : '—'}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error(err);
  }
}

window.activateModel = async function(version) {
  try {
    const res = await fetch('/api/models/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_version: version })
    });
    if (res.ok) {
      showToast(`Activated model '${version}'!`, 'success');
      await loadSystemConfig();
      await renderModelsList();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
};

async function saveSettings() {
  const provider = elements.ocrChoiceGemini.checked ? 'gemini' : 'qwen';
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ocr_provider: provider })
    });
    if (res.ok) {
      showToast(`Configuration updated: OCR set to ${provider.toUpperCase()}`, 'success');
      await loadSystemConfig();
      closeSettingsModal();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// Event Listeners Setup
// ==========================================
function setupEventListeners() {
  // Mode Switcher
  elements.modeBtnEval.addEventListener('click', () => setMode('evaluate'));
  elements.modeBtnTrain.addEventListener('click', () => setMode('train'));

  // Dropzone drag & drop
  elements.dropzoneEval.addEventListener('click', () => elements.fileInputEval.click());
  elements.fileInputEval.addEventListener('change', e => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  elements.dropzoneEval.addEventListener('dragover', e => {
    e.preventDefault();
    elements.dropzoneEval.classList.add('dragover');
  });

  elements.dropzoneEval.addEventListener('dragleave', () => {
    elements.dropzoneEval.classList.remove('dragover');
  });

  elements.dropzoneEval.addEventListener('drop', e => {
    e.preventDefault();
    elements.dropzoneEval.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  elements.btnRemoveFileEval.addEventListener('click', e => {
    e.stopPropagation();
    state.selectedFile = null;
    elements.filePillEval.classList.remove('active');
    elements.fileInputEval.value = '';
  });

  // JSON file selectors
  elements.btnSelectKeyFile.addEventListener('click', () => elements.fileInputKeys.click());
  elements.fileInputKeys.addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    if (file) await handleJsonFileSelection(file, 'key', elements.lblKeyFileTag, elements.keyFileStatus, elements.editorKeyAnswers, 'Key answers');
  });

  elements.btnSelectRubricFile.addEventListener('click', () => elements.fileInputRubric.click());
  elements.fileInputRubric.addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    if (file) await handleJsonFileSelection(file, 'rubric', elements.lblRubricFileTag, elements.rubricFileStatus, elements.editorRubrics, 'Rubric');
  });

  elements.btnSelectStudentJsonFile.addEventListener('click', () => elements.fileInputStudentJson.click());
  elements.fileInputStudentJson.addEventListener('change', async e => {
    const file = e.target.files && e.target.files[0];
    if (file) await handleJsonFileSelection(file, 'student', elements.lblStudentFileTag, elements.studentJsonFileStatus, elements.editorStudentAnswers, 'Student answer');
  });

  // Accordions
  document.querySelectorAll('.accordion-header').forEach(hdr => {
    hdr.addEventListener('click', () => {
      const item = hdr.closest('.accordion-item');
      item.classList.toggle('open');
    });
  });

  // Presets
  elements.btnPresetOop.addEventListener('click', () => {
    if (state.sampleData) {
      elements.editorKeyAnswers.value = JSON.stringify(state.sampleData.key_answers, null, 2);
      elements.editorRubrics.value = JSON.stringify(state.sampleData.rubrics, null, 2);
      showToast('Loaded OOP Reference Key & Rubrics', 'info');
    }
  });

  elements.btnPresetHigh.addEventListener('click', () => {
    if (state.sampleData) {
      elements.editorStudentAnswers.value = JSON.stringify(state.sampleData.sample_student_answers_excellent, null, 2);
      const acc = document.getElementById('acc-student-json');
      if (acc) acc.classList.add('open');
      showToast('Loaded High-Scoring Student Answers Preset', 'info');
    }
  });

  elements.btnPresetPartial.addEventListener('click', () => {
    if (state.sampleData) {
      elements.editorStudentAnswers.value = JSON.stringify(state.sampleData.sample_student_answers_partial, null, 2);
      const acc = document.getElementById('acc-student-json');
      if (acc) acc.classList.add('open');
      showToast('Loaded Partial-Scoring Student Answers Preset', 'info');
    }
  });

  elements.btnQuickStart.addEventListener('click', () => {
    elements.btnPresetHigh.click();
    runEvaluation();
  });

  // Evaluate Action
  elements.btnRunEvaluate.addEventListener('click', runEvaluation);

  // Download Report
  elements.btnDownloadReport.addEventListener('click', () => {
    if (!state.lastEvaluation) return;
    const blob = new Blob([JSON.stringify(state.lastEvaluation, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evaluation_report_${state.lastEvaluation.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // HITL Studio Buttons
  elements.btnStageSampleTrain.addEventListener('click', stageSampleForTrain);
  elements.btnRefreshPending.addEventListener('click', loadPendingHitlItems);
  elements.btnSeedSamples.addEventListener('click', seedDemoSamples);
  elements.btnStartFinetune.addEventListener('click', startFineTuning);

  // Settings Modal
  elements.pillOcr.addEventListener('click', openSettingsModal);
  elements.pillModel.addEventListener('click', openSettingsModal);
  elements.btnCloseModal.addEventListener('click', closeSettingsModal);
  elements.btnSaveSettings.addEventListener('click', saveSettings);
}

function handleFileSelected(file) {
  state.selectedFile = file;
  elements.filenameDisplayEval.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  elements.filePillEval.classList.add('active');
  showToast(`Selected file: ${file.name}`, 'info');
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initApp);
