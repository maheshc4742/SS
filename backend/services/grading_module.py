import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class CriterionEvaluation:
    criterion: str
    max_marks: float
    awarded_marks: float
    status: str  # "Fully Met", "Partially Met", "Not Met"
    notes: str

@dataclass
class GradingResult:
    marks: float
    max_marks: float
    feedback: str
    semantic_score: float
    confidence: float
    criteria_breakdown: List[Dict[str, Any]]

def quantize_half_or_whole(score: float, max_marks: float) -> float:
    """
    Enforces the rule: keep fraction .5 or whole number as per rubric.
    Clamps between 0.0 and max_marks.
    Examples:
      3.22 -> 3.0
      3.35 -> 3.5
      3.65 -> 3.5
      3.78 -> 4.0
    """
    quantized = round(score * 2.0) / 2.0
    clamped = max(0.0, min(float(max_marks), quantized))
    # Return as int if it's a whole number (e.g. 4.0 -> 4.0 for float consistency or displayed cleanly)
    return clamped

class GradingModule:
    """
    Rubric-based grading module.
    Evaluates student descriptive answers against reference answers, rubrics, and semantic similarity.
    Adheres strictly to the fraction .5 or whole number requirement.
    """

    @staticmethod
    def evaluate_criterion(
        criterion_name: str,
        crit_max: float,
        student_answer: str,
        reference_answer: str,
        semantic_score: float
    ) -> CriterionEvaluation:
        s_lower = student_answer.lower()
        r_lower = reference_answer.lower()
        crit_lower = criterion_name.lower()

        # Keywords specific to this criterion
        crit_keywords = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', crit_lower) if w not in {'the', 'and', 'for', 'with'}]

        # Check for criterion-related terms in student text
        matches = [kw for kw in crit_keywords if kw in s_lower]

        # Calculate criterion satisfaction score
        criterion_match_ratio = len(matches) / max(1, len(crit_keywords))
        
        # Combined criterion fulfillment using overall semantic alignment and specific keyword presence
        fulfillment = (semantic_score * 0.7) + (criterion_match_ratio * 0.3)

        raw_score = crit_max * fulfillment
        awarded = quantize_half_or_whole(raw_score, crit_max)

        if awarded >= crit_max:
            status = "Fully Met"
            notes = f"Criterion '{criterion_name}' thoroughly addressed."
        elif awarded > 0:
            status = "Partially Met"
            notes = f"Criterion '{criterion_name}' partially covered. Lacks full depth."
        else:
            status = "Not Met"
            notes = f"Criterion '{criterion_name}' missing or insufficient in the response."

        return CriterionEvaluation(
            criterion=criterion_name,
            max_marks=crit_max,
            awarded_marks=awarded,
            status=status,
            notes=notes
        )

    def grade(
        self,
        student_answer: str,
        reference_answer: str,
        rubric: Dict[str, Any],
        semantic_score: float,
        confidence: float
    ) -> GradingResult:
        max_marks = float(rubric.get("max_marks", 5.0))
        criteria_list = rubric.get("criteria", [])

        criteria_evals: List[CriterionEvaluation] = []
        feedback_lines: List[str] = []

        if criteria_list and isinstance(criteria_list, list):
            # Sum up criteria marks
            for crit in criteria_list:
                crit_name = crit.get("criterion", "Criterion")
                crit_max = float(crit.get("marks", 1.0))
                c_eval = self.evaluate_criterion(
                    crit_name,
                    crit_max,
                    student_answer,
                    reference_answer,
                    semantic_score
                )
                criteria_evals.append(c_eval)
                feedback_lines.append(f"• {c_eval.criterion} ({c_eval.awarded_marks}/{c_eval.max_marks} marks): {c_eval.notes}")

            total_awarded = sum(c.awarded_marks for c in criteria_evals)
            # Bound to max_marks and quantize
            final_marks = quantize_half_or_whole(total_awarded, max_marks)
        else:
            # Direct semantic-based rubric grading
            raw_marks = max_marks * semantic_score
            final_marks = quantize_half_or_whole(raw_marks, max_marks)
            
            if final_marks >= max_marks * 0.9:
                feedback_lines.append("Excellent answer covering all core points accurately.")
            elif final_marks >= max_marks * 0.7:
                feedback_lines.append("Good answer demonstrating sound conceptual understanding with minor omissions.")
            elif final_marks >= max_marks * 0.4:
                feedback_lines.append("Average response. Demonstrates basic awareness but lacks key descriptive elements.")
            else:
                feedback_lines.append("Answer is insufficient or does not match reference concepts.")

        # Overall summary feedback
        percentage = (final_marks / max_marks * 100) if max_marks > 0 else 0
        overall_critique = (
            f"Awarded {final_marks:g} out of {max_marks:g} marks ({percentage:.1f}%). "
            f"Semantic similarity: {semantic_score:.0%}, Confidence: {confidence:.0%}.\n"
            + "\n".join(feedback_lines)
        )

        breakdown_dicts = [
            {
                "criterion": c.criterion,
                "max_marks": c.max_marks,
                "awarded_marks": c.awarded_marks,
                "status": c.status,
                "notes": c.notes
            }
            for c in criteria_evals
        ]

        return GradingResult(
            marks=final_marks,
            max_marks=max_marks,
            feedback=overall_critique.strip(),
            semantic_score=semantic_score,
            confidence=confidence,
            criteria_breakdown=breakdown_dicts
        )

# Global singleton
grading_module = GradingModule()
