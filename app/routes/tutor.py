"""Tutor Routes - uses tutor_service and recommendation_service."""

from flask import Blueprint, request, jsonify
from ..utils.auth import token_required
from ..services import tutor_service, recommendation_service
from ..services.ai_service import generate_adaptive_questions

tutor_bp = Blueprint("tutor", __name__)


@tutor_bp.route("/chat", methods=["POST"])
@token_required
def chat(current_user):
    data     = request.get_json() or {}
    messages = data.get("messages", [])
    subject  = data.get("subject", "General")
    if not messages:
        return jsonify({"error": "messages required"}), 400
    result = tutor_service.chat(messages, subject)
    return jsonify(result), 200


@tutor_bp.route("/explain", methods=["POST"])
@token_required
def explain(current_user):
    data    = request.get_json() or {}
    concept = (data.get("concept") or "").strip()
    level   = data.get("level", "intermediate")
    if not concept:
        return jsonify({"error": "concept required"}), 400
    return jsonify(tutor_service.explain(concept, level)), 200


@tutor_bp.route("/recommendations", methods=["POST"])
@token_required
def recommendations(current_user):
    data   = request.get_json() or {}
    uid    = str(current_user["_id"])
    recs   = recommendation_service.build_recommendations(
        uid,
        exam_type      = data.get("exam_type", "General Exam"),
        learning_style = data.get("learning_style", "visual"),
    )
    return jsonify(recs), 200


@tutor_bp.route("/risk", methods=["GET"])
@token_required
def risk(current_user):
    uid      = str(current_user["_id"])
    upcoming = request.args.get("exam", "")
    return jsonify(recommendation_service.get_risk_analysis(uid, upcoming)), 200


@tutor_bp.route("/adaptive", methods=["POST"])
@token_required
def adaptive(current_user):
    data     = request.get_json() or {}
    topic    = data.get("topic", "General Knowledge")
    answered = data.get("answered", [])
    count    = min(int(data.get("count", 5)), 10)
    questions = generate_adaptive_questions(topic, answered, count)
    return jsonify({"questions": questions, "count": len(questions)}), 200


@tutor_bp.route("/save-session", methods=["POST"])
@token_required
def save_session(current_user):
    data     = request.get_json() or {}
    uid      = str(current_user["_id"])
    sid      = tutor_service.save_session(
        uid,
        data.get("subject", "General"),
        data.get("messages", []),
        data.get("concepts", []),
    )
    return jsonify({"session_id": sid}), 200


@tutor_bp.route("/sessions", methods=["GET"])
@token_required
def sessions(current_user):
    uid = str(current_user["_id"])
    return jsonify(tutor_service.get_sessions(uid)), 200