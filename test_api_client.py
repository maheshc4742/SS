import json
import requests

BASE_URL = "http://127.0.0.1:8000"

with open("samples/key_answers.json", "r", encoding="utf-8") as f:
    key_answers = json.load(f)

with open("samples/rubric.json", "r", encoding="utf-8") as f:
    rubrics = json.load(f)

with open("samples/student_script.json", "r", encoding="utf-8") as f:
    student_answers = json.load(f)

print("=== 1. Testing POST /api/evaluate (JSON Bypass) ===")
res = requests.post(f"{BASE_URL}/api/evaluate", json={
    "mode": "evaluate",
    "key_answers": key_answers,
    "rubrics": rubrics,
    "student_answers": student_answers
})
assert res.status_code == 200, f"Error: {res.text}"
data = res.json()
print("ID:", data["id"])
print(f"Obtained Marks: {data['obtained_marks']}/{data['total_marks']} ({data['percentage']}%)")
print("Report File:", data.get("report_path"))
for q in data["questions"]:
    print(f"  Q{q['question']}: {q['marks']}/{q['max_marks']} marks (Confidence: {q['confidence']:.0%})")

print("\n=== 2. Testing POST /api/evaluate (PDF File Upload) ===")
with open("samples/sample_student_script.pdf", "rb") as pdf_file:
    res_pdf = requests.post(
        f"{BASE_URL}/api/evaluate",
        files={"file": ("sample_student_script.pdf", pdf_file, "application/pdf")},
        data={
            "key_answers": json.dumps(key_answers),
            "rubrics": json.dumps(rubrics)
        }
    )
assert res_pdf.status_code == 200, f"Error: {res_pdf.text}"
data_pdf = res_pdf.json()
print("PDF Evaluation Result:")
print(f"Obtained Marks: {data_pdf['obtained_marks']}/{data_pdf['total_marks']} ({data_pdf['percentage']}%)")
for q in data_pdf["questions"]:
    print(f"  Q{q['question']}: {q['marks']}/{q['max_marks']} marks")

print("\n=== 3. Testing POST /api/train/evaluate (HITL Staging) ===")
res_train = requests.post(f"{BASE_URL}/api/train/evaluate", json={
    "mode": "train",
    "key_answers": key_answers,
    "rubrics": rubrics,
    "student_answers": student_answers
})
assert res_train.status_code == 200, f"Error: {res_train.text}"
data_train = res_train.json()
print(f"Staged {len(data_train['questions'])} questions in Train mode.")

print("\n=== 4. Testing GET /api/hitl/pending ===")
res_pending = requests.get(f"{BASE_URL}/api/hitl/pending")
assert res_pending.status_code == 200
pending_items = res_pending.json()
print(f"Found {len(pending_items)} pending items.")
assert len(pending_items) > 0

item_to_approve = pending_items[0]
print(f"Approving item ID {item_to_approve['id']} for Q{item_to_approve['question_id']}...")
res_approve = requests.post(f"{BASE_URL}/api/hitl/approve", json={
    "id": item_to_approve["id"],
    "human_marks": 4.5,
    "human_feedback": "Approved with full 4.5 marks for clear definition."
})
assert res_approve.status_code == 200
print("Approve response:", res_approve.json()["message"])

print("\n=== 5. Testing GET /api/training/stats ===")
res_stats = requests.get(f"{BASE_URL}/api/training/stats")
assert res_stats.status_code == 200
print("Training stats:", res_stats.json())

print("\n=== 6. Testing GET /api/models ===")
res_models = requests.get(f"{BASE_URL}/api/models")
assert res_models.status_code == 200
print("Models available:", [m["model_version"] for m in res_models.json()])

print("\nALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")
