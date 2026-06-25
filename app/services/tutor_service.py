"""
Tutor Service
Wraps AI calls for tutoring, concept explanation, and conversation management.
"""

from datetime import datetime
from ..models.database import mongo, doc_to_json
from .ai_service import ai_tutor_chat, explain_concept


def chat(messages: list, subject: str = "General") -> dict:
    """Run one turn of the AI tutor conversation."""
    return ai_tutor_chat(messages, subject)


def explain(concept: str, level: str = "intermediate") -> dict:
    """Get a deep explanation of a concept."""
    return explain_concept(concept, level)


def save_session(user_id: str, subject: str, messages: list, concepts: list) -> str:
    doc = {
        "user_id":    user_id,
        "subject":    subject,
        "messages":   messages,
        "concepts":   concepts,
        "msg_count":  len(messages),
        "session_at": datetime.utcnow(),
    }
    result = mongo.db.tutor_sessions.insert_one(doc)
    return str(result.inserted_id)


def get_sessions(user_id: str, limit: int = 10) -> list:
    docs = list(
        mongo.db.tutor_sessions
        .find({"user_id": user_id})
        .sort("session_at", -1)
        .limit(limit)
    )
    return doc_to_json(docs)