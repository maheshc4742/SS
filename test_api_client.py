import argparse
import json
from pathlib import Path
import requests


def load_json(path: Path):
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def main():
    parser = argparse.ArgumentParser(description="Evaluate user-provided JSON answer files through the local API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--key-answers", required=True, type=Path)
    parser.add_argument("--rubrics", required=True, type=Path)
    parser.add_argument("--student-answers", required=True, type=Path)
    args = parser.parse_args()

    response = requests.post(
        f"{args.base_url.rstrip('/')}/api/evaluate",
        json={
            "mode": "evaluate",
            "key_answers": load_json(args.key_answers),
            "rubrics": load_json(args.rubrics),
            "student_answers": load_json(args.student_answers)
        }
    )
    response.raise_for_status()
    result = response.json()
    print(f"Evaluation {result['id']}: {result['obtained_marks']}/{result['total_marks']} ({result['percentage']}%)")
    for question in result["questions"]:
        print(f"Q{question['question']}: {question['marks']}/{question['max_marks']} marks")


if __name__ == "__main__":
    main()
