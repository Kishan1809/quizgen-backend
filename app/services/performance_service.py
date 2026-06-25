"""
Performance Service
Handles student performance tracking, stats aggregation, and history.
"""

from datetime import datetime
from bson import ObjectId
from ..models.database import mongo, doc_to_json


def save_test_result(data: dict) -> str:
    """Persist a completed test result and return its ID."""
    data.setdefault("submitted_at", datetime.utcnow())
    result = mongo.db.test_results.insert_one(data)
    return str(result.inserted_id)


def get_user_results(user_id: str, limit: int = 50) -> list:
    docs = list(
        mongo.db.test_results
        .find({"user_id": user_id})
        .sort("submitted_at", -1)
        .limit(limit)
    )
    return doc_to_json(docs)


def get_user_stats(user_id: str) -> dict:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_exams":     {"$sum": 1},
            "avg_score":       {"$avg": "$score"},
            "best_score":      {"$max": "$score"},
            "worst_score":     {"$min": "$score"},
            "total_questions": {"$sum": "$total_questions"},
            "total_correct":   {"$sum": "$correct_answers"},
        }},
    ]
    rows = list(mongo.db.test_results.aggregate(pipeline))
    if not rows:
        return {}
    r = rows[0]
    r.pop("_id", None)
    r["avg_score"]  = round(r.get("avg_score") or 0, 2)
    r["best_score"] = round(r.get("best_score") or 0, 2)
    return r


def get_topic_breakdown(user_id: str) -> dict:
    """Return per-topic accuracy from question_breakdown arrays."""
    results = get_user_results(user_id, limit=100)
    topic_map = {}
    for r in results:
        for q in r.get("question_breakdown", []):
            t = q.get("topic") or "General"
            topic_map.setdefault(t, {"correct": 0, "total": 0})
            topic_map[t]["total"] += 1
            if q.get("is_correct"):
                topic_map[t]["correct"] += 1

    breakdown = []
    for topic, s in topic_map.items():
        pct = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0
        breakdown.append({
            "topic":    topic,
            "correct":  s["correct"],
            "total":    s["total"],
            "accuracy": pct,
            "mastery":  "high" if pct >= 75 else "medium" if pct >= 50 else "low",
        })
    return sorted(breakdown, key=lambda x: x["accuracy"])


def get_result_by_id(result_id: str) -> dict | None:
    try:
        doc = mongo.db.test_results.find_one({"_id": ObjectId(result_id)})
        return doc_to_json(doc)
    except Exception:
        return None