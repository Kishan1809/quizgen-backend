"""
Recommendation Service
Generates personalised study resources, weekly plans, and learning strategies.
"""

from .performance_service import get_user_results, get_user_stats, get_topic_breakdown
from .ai_service import generate_smart_recommendations, predict_performance_risk


def build_recommendations(user_id: str, exam_type: str, learning_style: str) -> dict:
    """Full recommendation pipeline for a student."""
    stats      = get_user_stats(user_id)
    avg_score  = float(stats.get("avg_score") or 0)
    breakdown  = get_topic_breakdown(user_id)

    weak_topics   = [t["topic"] for t in breakdown if t["mastery"] == "low"][:5]
    strong_topics = [t["topic"] for t in breakdown if t["mastery"] == "high"][:3]

    recs = generate_smart_recommendations(
        weak_topics    = weak_topics,
        strong_topics  = strong_topics,
        exam_type      = exam_type,
        avg_score      = avg_score,
        learning_style = learning_style,
    )
    recs["weak_topics"]   = weak_topics
    recs["strong_topics"] = strong_topics
    recs["avg_score"]     = avg_score
    return recs


def get_risk_analysis(user_id: str, upcoming_exam: str = "") -> dict:
    results = get_user_results(user_id, limit=20)
    return predict_performance_risk(results, upcoming_exam)