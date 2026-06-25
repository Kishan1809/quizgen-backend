"""
Curated MCQ bank used when Gemini is unavailable or returns an error.
Questions are exam-style and keyed by topic bucket for realistic practice.
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
from datetime import datetime


def _q(
    text: str,
    options: list[str],
    correct: int,
    topic: str,
    difficulty: str = "medium",
    explanation: str = "",
) -> dict:
    h = hashlib.sha256(text.encode()).hexdigest()[:12]
    return {
        "id": f"bank_{h}",
        "type": "mcq",
        "text": text,
        "options": options,
        "correctAnswer": correct,
        "explanation": explanation or "Review the concept and try a similar problem.",
        "topic": topic,
        "difficulty": difficulty,
        "marks": 1,
    }


# ── Bucketed pools (subset shown; expanded for production variety) ─────────

_DEFAULT_POOL = [
    _q(
        "If a train travels 180 km in 3 hours at constant speed, what is its speed in km/h?",
        ["45 km/h", "60 km/h", "90 km/h", "540 km/h"],
        1,
        "Quantitative reasoning",
        "easy",
        "Speed = distance ÷ time = 180 ÷ 3 = 60 km/h.",
    ),
    _q(
        "Which sentence uses the subjunctive mood correctly?",
        ["I wish I was there.", "I wish I were there.", "I wish I am there.", "I wish I be there."],
        1,
        "English grammar",
        "medium",
        "The subjunctive uses 'were' for hypothetical wishes.",
    ),
    _q(
        "In a right triangle with legs 3 and 4, what is the length of the hypotenuse?",
        ["5", "6", "7", "12"],
        0,
        "Geometry",
        "easy",
        "3-4-5 is a Pythagorean triple.",
    ),
    _q(
        "Photosynthesis primarily occurs in which plant organelle?",
        ["Mitochondria", "Chloroplast", "Nucleus", "Ribosome"],
        1,
        "Biology",
        "easy",
    ),
    _q(
        "What is the value of log₁₀(100)?",
        ["1", "2", "10", "100"],
        1,
        "Logarithms",
        "easy",
    ),
    _q(
        "Which gas makes up most of Earth's atmosphere?",
        ["Oxygen", "Carbon dioxide", "Nitrogen", "Hydrogen"],
        2,
        "General Science",
        "easy",
    ),
    _q(
        "If f(x) = 2x + 3, what is f(5)?",
        ["10", "11", "13", "16"],
        2,
        "Algebra",
        "easy",
        "f(5) = 2(5)+3 = 13.",
    ),
    _q(
        "The derivative of x² with respect to x is:",
        ["x", "2x", "x²/2", "2"],
        1,
        "Calculus",
        "medium",
    ),
    _q(
        "In economics, when demand increases and supply is unchanged, ceteris paribus, equilibrium price will:",
        ["Fall", "Rise", "Stay the same", "Become zero"],
        1,
        "Economics",
        "medium",
    ),
    _q(
        "Which organ filters blood to form urine?",
        ["Liver", "Heart", "Kidney", "Lung"],
        2,
        "Human Biology",
        "easy",
    ),
]

_SAT_GRE_POOL = _DEFAULT_POOL + [
    _q(
        "If 3x − 7 = 14, what is x?",
        ["5", "6", "7", "8"],
        2,
        "Algebra",
        "medium",
        "3x = 21 → x = 7.",
    ),
    _q(
        "A rectangle has length 8 and width 5. What is its area?",
        ["13", "26", "40", "80"],
        2,
        "Geometry",
        "easy",
    ),
    _q(
        "Choose the word that best completes the sentence: The committee ___ divided on the issue.",
        ["is", "are", "were", "be"],
        0,
        "English usage",
        "hard",
        "Committee as a single unit takes singular verb in formal US English.",
    ),
    _q(
        "Reading comp: 'Mitigate' most nearly means:",
        ["Intensify", "Lessen", "Ignore", "Postpone"],
        1,
        "Vocabulary",
        "medium",
    ),
]

_JEE_NEET_POOL = _DEFAULT_POOL + [
    _q(
        "A body of mass 2 kg accelerates at 3 m/s². What is the net force (F = ma)?",
        ["5 N", "6 N", "9 N", "12 N"],
        1,
        "Physics – Mechanics",
        "easy",
    ),
    _q(
        "What is the pH of a neutral solution at 25°C?",
        ["0", "7", "14", "1"],
        1,
        "Chemistry",
        "easy",
    ),
    _q(
        "In DNA, adenine pairs with:",
        ["Guanine", "Cytosine", "Thymine", "Uracil"],
        2,
        "Biology – Genetics",
        "medium",
    ),
    _q(
        "The integral ∫₀¹ 2x dx equals:",
        ["0", "1", "2", "4"],
        1,
        "Calculus",
        "medium",
        "∫2x dx = x²; from 0 to 1 → 1.",
    ),
]

_IELTS_POOL = _DEFAULT_POOL + [
    _q(
        "Which is grammatically correct?",
        ["She don't like coffee.", "She doesn't likes coffee.", "She doesn't like coffee.", "She not like coffee."],
        2,
        "Grammar",
        "easy",
    ),
    _q(
        "In academic writing, a 'thesis statement' primarily:",
        ["Lists references", "States the main argument", "Summarizes methodology", "Thanks the reader"],
        1,
        "Academic English",
        "medium",
    ),
]

_MEDICAL_POOL = _DEFAULT_POOL + [
    _q(
        "Normal resting heart rate for healthy adults is typically closest to:",
        ["40 bpm", "60–100 bpm", "120 bpm", "180 bpm"],
        1,
        "Physiology",
        "easy",
    ),
    _q(
        "Which vitamin deficiency is classically associated with scurvy?",
        ["A", "B12", "C", "D"],
        2,
        "Biochemistry",
        "medium",
    ),
]

_LAW_POOL = _DEFAULT_POOL + [
    _q(
        "In common law systems, 'stare decisis' refers to:",
        ["Judicial review of statutes", "Standing to sue", "Adherence to precedent", "Strict liability"],
        2,
        "Legal reasoning",
        "hard",
    ),
]


def _bucket_for_exam(exam_name: str) -> str:
    n = (exam_name or "").lower()
    if re.search(r"\bjee\b|gate|neet|upsc|ssc|ibps|cat\b", n):
        return "STEM_IN"
    if re.search(r"\bsat\b|act\b|gre|gmat|lsat", n):
        return "US_GRAD"
    if re.search(r"ielts|toefl|celpip", n):
        return "ENGLISH"
    if re.search(r"mcat|usmle|gamsat|medic", n):
        return "MEDICAL"
    if re.search(r"lsat|lnat|law", n):
        return "LAW"
    return "GENERAL"


_POOL_MAP = {
    "GENERAL": _DEFAULT_POOL,
    "STEM_IN": _JEE_NEET_POOL,
    "US_GRAD": _SAT_GRE_POOL,
    "ENGLISH": _IELTS_POOL,
    "MEDICAL": _MEDICAL_POOL,
    "LAW": _LAW_POOL,
}


def _difficulty_ok(q: dict, target: str) -> bool:
    d = (q.get("difficulty") or "medium").lower()
    t = (target or "medium").lower()
    if t == "easy":
        return d in ("easy", "medium")
    if t == "hard":
        return d in ("medium", "hard")
    return True


def get_curated_mcq(exam_name: str, difficulty: str, count: int) -> list[dict]:
    """Return up to `count` shuffled, deduplicated MCQs appropriate for the exam name."""
    bucket = _bucket_for_exam(exam_name)
    pool = copy.deepcopy(_POOL_MAP.get(bucket, _DEFAULT_POOL))
    random.shuffle(pool)
    out: list[dict] = []
    seen = set()
    for q in pool:
        if len(out) >= count:
            break
        if not _difficulty_ok(q, difficulty):
            continue
        key = q["text"][:80]
        if key in seen:
            continue
        seen.add(key)
        q = copy.deepcopy(q)
        q["id"] = f"{q['id']}_{int(datetime.utcnow().timestamp() * 1000)}_{len(out)}"
        q.setdefault("topic", exam_name)
        out.append(q)
    # If still short, pull from the general pool (ignore difficulty filter)
    if len(out) < count:
        for q in copy.deepcopy(_DEFAULT_POOL):
            if len(out) >= count:
                break
            key = q["text"][:80]
            if key in seen:
                continue
            seen.add(key)
            q = copy.deepcopy(q)
            q["id"] = f"bank_fill_{hashlib.sha256(key.encode()).hexdigest()[:8]}_{len(out)}"
            out.append(q)
    return out[:count]


def get_curated_for_topic(topic: str, difficulty: str, count: int) -> list[dict]:
    """Institute flows pass a free-text topic string."""
    return get_curated_mcq(topic or "General Knowledge", difficulty, count)
