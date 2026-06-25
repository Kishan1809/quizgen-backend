"""Institute Routes – Exam creation, management, analytics."""

import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify
from bson import ObjectId

from ..models.database import (
    InstituteExamModel, AttemptModel, mongo, doc_to_json
)
from ..services.ai_service import generate_questions
from ..utils.auth import token_required

institute_bp = Blueprint("institute", __name__)


# ── Generate AI Questions ────────────────────────────────────

@institute_bp.route("/generate-questions", methods=["POST"])
@token_required
def generate_ai_questions(current_user):
    data = request.get_json(force=True) or {}
    topic       = data.get("topic") or data.get("description") or "General Knowledge"
    q_type      = data.get("type", "mcq").lower()
    difficulty  = data.get("difficulty", "medium")
    count       = min(int(data.get("count", data.get("num_questions", 5))), 30)
    extra       = data.get("prompt", "")

    questions = generate_questions(topic, q_type, difficulty, count, extra)
    return jsonify({"questions": questions, "count": len(questions)}), 200


# ── Create Exam ──────────────────────────────────────────────

@institute_bp.route("/create-exam", methods=["POST"])
@token_required
def create_exam(current_user):
    data = request.get_json(force=True) or {}

    required = ["name", "instituteName", "examId", "questions"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    exam_id = data["examId"].strip()
    if InstituteExamModel.find_by_exam_id(exam_id):
        return jsonify({
            "error": "Exam ID already exists",
            "message": f"An exam with ID '{exam_id}' already exists"
        }), 409

    # Compute total marks from questions if not provided
    questions   = data.get("questions", [])
    total_marks = data.get("totalMarks") or sum(q.get("marks", 1) for q in questions)
    passing     = data.get("passingMarks") or round(total_marks * 0.4)

    doc = {
        "name":              data["name"].strip(),
        "institute_name":    data["instituteName"].strip(),
        "institute_id":      data.get("instituteId") or str(current_user["_id"]),
        "created_by":        str(current_user["_id"]),
        "exam_id":           exam_id,
        "description":       data.get("description", "").strip(),
        "type":              data.get("type", "mcq"),
        "duration":          int(data.get("duration", 60)),
        "difficulty":        data.get("difficulty", "medium"),
        "subject":           data.get("subject", "").strip(),
        "questions":         questions,
        "total_marks":       total_marks,
        "passing_marks":     passing,
        "ai_generated":      data.get("aiGenerate", False),
        "cheating_detection":data.get("enableCheatingDetection", False),
        "published":         True,
        "created_at":        datetime.utcnow(),
        "updated_at":        datetime.utcnow(),
        "attempt_count":     0,
    }

    inserted_id = InstituteExamModel.create(doc)
    return jsonify({
        "status":   "success",
        "examId":   exam_id,
        "_id":      inserted_id,
        "message":  "Exam created and published successfully",
    }), 201


# ── List All Exams (for this institute) ──────────────────────

@institute_bp.route("/my-exams", methods=["GET"])
@token_required
def my_exams(current_user):
    exams = InstituteExamModel.get_by_institute(str(current_user["_id"]))
    return jsonify({"exams": exams, "count": len(exams)}), 200


@institute_bp.route("/list-exams", methods=["GET"])
def list_all_exams():
    institute_id = request.args.get("institute_id")
    query = {"institute_id": institute_id} if institute_id else {}
    exams = InstituteExamModel.get_all(query)
    return jsonify({"exams": exams, "count": len(exams)}), 200


# ── Check Exam Existence ─────────────────────────────────────

@institute_bp.route("/exam/<exam_id>/exists", methods=["GET"])
def check_exam_exists(exam_id):
    exam = InstituteExamModel.find_by_exam_id(exam_id)
    if exam:
        return jsonify({
            "exists": True,
            "exam_info": {
                "name": exam.get("name"),
                "institute_name": exam.get("institute_name"),
                "subject": exam.get("subject"),
                "type": exam.get("type"),
            }
        }), 200
    return jsonify({"exists": False}), 200


# ── Update Exam ──────────────────────────────────────────────

@institute_bp.route("/exam/<exam_id>", methods=["PUT"])
@token_required
def update_exam(current_user, exam_id):
    exam = InstituteExamModel.find_by_exam_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    if exam.get("created_by") != str(current_user["_id"]):
        return jsonify({"error": "Unauthorised"}), 403

    data = request.get_json() or {}
    allowed = {k: v for k, v in data.items()
               if k in ["name", "description", "questions", "duration", "total_marks",
                         "passing_marks", "published", "difficulty", "subject"]}
    allowed["updated_at"] = datetime.utcnow()
    InstituteExamModel.update(exam_id, allowed)
    return jsonify({"message": "Exam updated successfully"}), 200


# ── Delete Exam ──────────────────────────────────────────────

@institute_bp.route("/exam/<exam_id>", methods=["DELETE"])
@token_required
def delete_exam(current_user, exam_id):
    exam = InstituteExamModel.find_by_exam_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    if exam.get("created_by") != str(current_user["_id"]):
        return jsonify({"error": "Unauthorised"}), 403
    InstituteExamModel.delete(exam_id)
    return jsonify({"message": "Exam deleted"}), 200


# ── Analytics ────────────────────────────────────────────────

@institute_bp.route("/analytics/<exam_id>", methods=["GET"])
def get_analytics(exam_id):
    exam = InstituteExamModel.find_by_exam_id(exam_id)
    if not exam:
        return jsonify({"status": "error", "message": "Exam not found"}), 404

    attempts = list(mongo.db.exam_attempts.find({"exam_id": exam_id, "status": "completed"}))
    total    = len(attempts)

    if total == 0:
        return jsonify({"status": "success", "analytics": _empty_analytics(exam)}), 200

    total_marks  = exam.get("total_marks", 100)
    passing_marks = exam.get("passing_marks", 40)

    scores, processed = [], []
    for a in attempts:
        obtained = a.get("obtained_marks", 0)
        pct      = a.get("percentage") or (obtained / total_marks * 100 if total_marks else 0)
        scores.append(pct)
        status   = "pass" if obtained >= passing_marks else "fail"
        processed.append({
            "student_id":    a.get("student_id"),
            "student_name":  a.get("student_name", "Anonymous"),
            "student_email": a.get("student_email", ""),
            "score":         round(pct, 1),
            "obtained_marks":obtained,
            "status":        status,
            "time_taken":    a.get("time_taken_minutes", 0),
            "cheating":      a.get("cheating_detected", False),
            "submitted_at":  a.get("completed_at", ""),
        })

    pass_count = sum(1 for p in processed if p["status"] == "pass")
    avg        = sum(scores) / total

    score_dist = _score_distribution(scores, total)

    return jsonify({
        "status": "success",
        "analytics": {
            "exam_id":          exam_id,
            "exam_name":        exam.get("name"),
            "institute_name":   exam.get("institute_name"),
            "subject":          exam.get("subject"),
            "total_students":   total,
            "average_score":    round(avg, 2),
            "highest_score":    round(max(scores), 1),
            "lowest_score":     round(min(scores), 1),
            "pass_count":       pass_count,
            "fail_count":       total - pass_count,
            "pass_percentage":  round(pass_count / total * 100, 2),
            "score_distribution": score_dist,
            "student_results":  sorted(processed, key=lambda x: x["score"], reverse=True),
        }
    }), 200


def _empty_analytics(exam: dict) -> dict:
    return {
        "exam_id": exam.get("exam_id"),
        "exam_name": exam.get("name"),
        "institute_name": exam.get("institute_name"),
        "total_students": 0,
        "average_score": 0,
        "pass_percentage": 0,
        "student_results": [],
        "score_distribution": [],
    }


def _score_distribution(scores: list[float], total: int) -> list[dict]:
    ranges = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "0-49": 0}
    for s in scores:
        if s >= 90: ranges["90-100"] += 1
        elif s >= 80: ranges["80-89"] += 1
        elif s >= 70: ranges["70-79"] += 1
        elif s >= 60: ranges["60-69"] += 1
        elif s >= 50: ranges["50-59"] += 1
        else: ranges["0-49"] += 1
    return [{"range": r, "count": c, "pct": round(c / total * 100, 1) if total else 0}
            for r, c in ranges.items()]