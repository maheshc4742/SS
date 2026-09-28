import json
from pathlib import Path
import pymupdf as fitz

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Key Answers
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

# 2. Rubrics
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

# 3. Student Answers (JSON script bypassing OCR)
student_answers_json = {
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

with open(SAMPLES_DIR / "key_answers.json", "w", encoding="utf-8") as f:
    json.dump(key_answers, f, indent=4)

with open(SAMPLES_DIR / "rubric.json", "w", encoding="utf-8") as f:
    json.dump(rubrics, f, indent=4)

with open(SAMPLES_DIR / "student_script.json", "w", encoding="utf-8") as f:
    json.dump(student_answers_json, f, indent=4)

# 4. Generate a sample PDF answer sheet using PyMuPDF
doc = fitz.open()
page = doc.new_page(width=595, height=842)  # A4 size

# Add exam title and questions
text = (
    "SCRIPTSENSE DESCRIPTIVE ANSWER SCRIPT\n"
    "Student ID: CS-2026-8841 | Course: Advanced Software Engineering\n"
    "--------------------------------------------------------------------------------\n\n"
    "Q1: What is Object-Oriented Programming and its core principles?\n"
    "Ans: Object Oriented Programming is a paradigm centered around objects rather than functions.\n"
    "Its four primary pillars are Encapsulation, Abstraction, Inheritance, and Polymorphism.\n"
    "Encapsulation bundles data and methods while restricting direct access.\n\n"
    "Q2: Explain Polymorphism with its types.\n"
    "Ans: Polymorphism allows an entity to take multiple forms. Compile-time polymorphism is achieved\n"
    "via method overloading. Runtime polymorphism is achieved via method overriding in subclasses.\n\n"
    "Q3: Describe Exception Handling mechanism.\n"
    "Ans: Exception handling prevents unexpected crashes. The try block encloses risky code, catch handles\n"
    "the error gracefully, and finally ensures cleanup operations are always completed.\n"
)

point = fitz.Point(50, 60)
page.insert_text(point, text, fontsize=11, color=(0.1, 0.1, 0.15))

pdf_path = SAMPLES_DIR / "sample_student_script.pdf"
doc.save(str(pdf_path))
doc.close()

# 5. Generate a sample image from the PDF page
doc_img = fitz.open(str(pdf_path))
pix = doc_img[0].get_pixmap(dpi=150)
img_path = SAMPLES_DIR / "sample_student_script.png"
pix.save(str(img_path))
doc_img.close()

print(f"Generated sample files in {SAMPLES_DIR}:")
print(f" - {SAMPLES_DIR / 'key_answers.json'}")
print(f" - {SAMPLES_DIR / 'rubric.json'}")
print(f" - {SAMPLES_DIR / 'student_script.json'}")
print(f" - {pdf_path}")
print(f" - {img_path}")
