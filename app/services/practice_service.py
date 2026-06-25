"""
Practice Service
Handles personalised practice session generation and history.
"""

from datetime import datetime, timezone
from ..models.database import mongo, doc_to_json
from .performance_service import get_user_results, get_topic_breakdown
from .ai_service import generate_personalised_practice


# 🔥 NEW: sanitize + fix questions
def _sanitize_questions(questions):
    clean = []

    for i, q in enumerate(questions):
        try:
            clean.append({
                "id": q.get("id", f"Q{i+1}"),
                "type": q.get("type", "mcq"),
                "text": q.get("text") or q.get("question_text") or "",
                "options": q.get("options", []),
                "correctAnswer": int(q.get("correctAnswer", 0)),
                "explanation": q.get("explanation", ""),
            })
        except:
            continue

    return clean


# 🔥 NEW: remove duplicates
def _remove_duplicates(questions):
    seen = set()
    unique = []

    for q in questions:
        key = q["text"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    return unique


def generate_session(user_id: str, country: str, exam_type: str,
                     target_score: int = 80) -> dict:
    """Generate an AI-personalised practice session."""

    results = get_user_results(user_id, limit=10)
    breakdown = get_topic_breakdown(user_id)

    weak_topics = [t["topic"] for t in breakdown if t["mastery"] == "low"][:5]
    strong_topics = [t["topic"] for t in breakdown if t["mastery"] == "high"][:3]

    try:
        practice = generate_personalised_practice(
            country=country,
            exam_type=exam_type,
            weak_areas=weak_topics,
            strong_areas=strong_topics,
            target_score=target_score,
            has_history=bool(results),
        )

        questions = practice.get("questions", [])

        # 🔥 FIX 1: sanitize
        questions = _sanitize_questions(questions)

        # 🔥 FIX 2: remove duplicates
        questions = _remove_duplicates(questions)

        # 🔥 FIX 3: fallback if empty
        if not questions:
            raise ValueError("AI returned empty questions")

        return {
            "practice": {
                "questions": questions,
                "weak_topics": weak_topics,
                "strong_topics": strong_topics,
            }
        }

    except Exception as e:
        print("[Practice] AI failed:", str(e))

        # 🔥 SAFE FALLBACK
        fallback = [{
            "id": "Q1",
            "type": "mcq",
            "text": "Fallback: What is 2 + 2?",
            "options": ["1", "2", "3", "4"],
            "correctAnswer": 3,
            "explanation": "Basic sanity fallback",
        }]

        return {
            "practice": {
                "questions": fallback,
                "error": str(e),
            }
        }


def save_session(user_id: str, session_data: dict) -> str:
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": user_id,
        "session_type": "practice",
        "country": session_data.get("country"),
        "exam_type": session_data.get("exam_type"),
        "questions_attempted": int(session_data.get("questions_attempted", 0)),
        "total_questions": int(session_data.get("total_questions", 0)),
        "questions_correct": int(session_data.get("questions_correct", 0)),
        "time_taken_minutes": int(session_data.get("time_taken", 0)),
        "topics_covered": session_data.get("topics_covered", []),
        "answers": session_data.get("answers", {}),
        "score": 0,
        "exam_name": f"Practice – {session_data.get('country')} ({session_data.get('exam_type')})",
        "submitted_at": now,
        "is_unlimited_time": True,
    }

    result = mongo.db.test_results.insert_one(doc)
    return str(result.inserted_id)


def get_history(user_id: str, page: int = 1, limit: int = 10) -> dict:
    query = {"user_id": user_id, "session_type": "practice"}

    total = mongo.db.test_results.count_documents(query)

    docs = list(
        mongo.db.test_results.find(query)
        .sort("submitted_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    return {
        "sessions": doc_to_json(docs),
        "pagination": {
            "page": page,
            "total_pages": max(1, (total + limit - 1) // limit),
            "total": total,
        },
    }
