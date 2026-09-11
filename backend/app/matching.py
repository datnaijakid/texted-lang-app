import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.config import get_settings

settings = get_settings()


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


@dataclass
class GradeResult:
    correct: bool
    almost: bool
    missing_accents: bool
    similarity: float
    message: str


def grade_answer(user_answer: str, correct_answer: str) -> GradeResult:
    """
    Grades a typed answer against the correct term.
    - Exact match (accent/case-insensitive) -> correct, no note.
    - Correct except for accents -> correct, but gently note the accent.
    - Close but has a typo (above fuzzy threshold) -> "almost" correct, shown the fix.
    - Otherwise -> incorrect.
    """
    user_clean = user_answer.strip().lower()
    correct_clean = correct_answer.strip().lower()

    user_no_accents = strip_accents(user_clean)
    correct_no_accents = strip_accents(correct_clean)

    if user_no_accents == correct_no_accents:
        if user_clean == correct_clean:
            return GradeResult(True, False, False, 100.0, "Correct!")
        return GradeResult(
            True, False, True, 100.0,
            f"Correct! Just remember the accent: \"{correct_answer}\"."
        )

    similarity = fuzz.ratio(user_no_accents, correct_no_accents)
    if similarity >= settings.fuzzy_match_threshold:
        return GradeResult(
            False, True, False, similarity,
            f"Almost! You had a small typo. Correct spelling: \"{correct_answer}\"."
        )

    return GradeResult(
        False, False, False, similarity,
        f"Not quite. The correct answer is \"{correct_answer}\"."
    )
