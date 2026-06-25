"""
Quiz Routes - Countries, Exams, Test Generation, Submit, Performance.
UPDATED: Added offline sync support + duplicate protection
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from ..models.database import CountryModel, ExamModel
from ..services.exam_service import get_or_create_exams_for_country
from ..services.ai_service import (
    generate_full_test, generate_questions_for_exam,
    generate_exam_report_insights, explain_concept,
    analyse_performance_trends
)
from ..services.performance_service import (
    save_test_result, get_user_results, get_user_stats,
    get_topic_breakdown, get_result_by_id,
)
from ..utils.auth import token_required

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import random, string

quiz_bp = Blueprint("quiz", __name__)

# ===============================
# 🌍 COUNTRIES & EXAMS
# ===============================

@quiz_bp.route("/countries", methods=["GET"])
def get_countries():
    return jsonify(CountryModel.get_all()), 200


@quiz_bp.route("/exams/<country_id>", methods=["GET"])
def get_exams(country_id):
    return jsonify(get_or_create_exams_for_country(country_id)), 200


@quiz_bp.route("/exam/<exam_id>", methods=["GET"])
def get_exam(exam_id):
    exam = ExamModel.get_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    return jsonify(exam), 200


# ===============================
# 🧠 TEST GENERATION
# ===============================

@quiz_bp.route("/generate-test/<exam_id>", methods=["GET"])
@token_required
def generate_test(current_user, exam_id):
    exam = ExamModel.get_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    test = generate_full_test(exam["name"], exam.get("duration", 60))

    return jsonify({
        "exam": exam,
        "test_content": test
    }), 200


@quiz_bp.route("/questions/<exam_id>", methods=["GET"])
@token_required
def get_questions(current_user, exam_id):
    exam = ExamModel.get_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    count = min(int(request.args.get("count", 20)), 40)
    difficulty = request.args.get("difficulty", "medium")
    q_type = request.args.get("type", "mcq")

    country = CountryModel.get_by_id(exam.get("country_id")) or {}
    country_name = country.get("name", "")

    pack = generate_questions_for_exam(
        exam, country_name, q_type, difficulty, count
    )

    questions = pack.get("questions") or []

    return jsonify({
        "exam": exam,
        "questions": questions,
        "total": len(questions),
        "question_source": pack.get("source"),
        "ai_working": pack.get("source") == "openrouter",
        # FIX: previously missing entirely. The frontend timer was using
        # exam["duration"] (the exam's FULL official duration, e.g. NEET's
        # 200 min) for every test regardless of how many questions actually
        # came back. This is the per-question-scaled duration computed in
        # ai_service.generate_questions_for_exam — the frontend now reads
        # this first and only falls back to the full exam duration if it's
        # missing.
        "suggested_duration_minutes": pack.get("suggested_duration_minutes"),
        # FIX: was also missing — the frontend already has code that reads
        # `r.data.ai_error` to show a warning banner when AI generation
        # failed, but since this key was never sent, that banner could only
        # ever fire for the bank-fallback case, never for actual AI errors.
        "ai_error": pack.get("ai_error"),
    }), 200


# ===============================
# 🔥 SUBMIT (UPDATED)
# ===============================

@quiz_bp.route("/submit", methods=["POST"])
@token_required
def submit(current_user):
    data = request.get_json() or {}

    uid = str(current_user["_id"])

    # 🔥 NEW: offline support
    offline_id = data.get("offline_id")

    # 🛑 BASIC VALIDATION
    if not data.get("exam_id"):
        return jsonify({"error": "exam_id required"}), 400

    score = float(data.get("score", 0))
    total_q = int(data.get("total_questions", 0))
    correct = int(data.get("correct_answers", 0))

    # 🔥 DUPLICATE PROTECTION (IMPORTANT)
    if offline_id:
        existing = get_result_by_offline_id(uid, offline_id)
        if existing:
            return jsonify({
                "status": "duplicate",
                "message": "Already synced"
            }), 200

    doc = {
        "user_id": uid,
        "exam_id": data.get("exam_id"),
        "exam_name": data.get("exam_name", "Exam"),
        "score": score,
        "total_questions": total_q,
        "correct_answers": correct,
        "incorrect_answers": total_q - correct,
        "accuracy": round(correct / total_q * 100, 2) if total_q else 0,
        "time_taken": data.get("time_taken"),
        "question_breakdown": data.get("question_breakdown", []),
        "exam_type": data.get("exam_type", "online"),
        "difficulty": data.get("difficulty", "medium"),
        "offline_id": offline_id,  # 🔥 NEW FIELD
        "submitted_at": datetime.utcnow(),
    }

    rid = save_test_result(doc)

    return jsonify({
        "status": "success",
        "result_id": rid,
        "score": score,
        "accuracy": doc["accuracy"]
    }), 200


# ===============================
# 📊 PERFORMANCE
# ===============================

@quiz_bp.route("/performance/<user_id>", methods=["GET"])
@token_required
def performance(current_user, user_id):
    if str(current_user["_id"]) != user_id:
        return jsonify({"error": "Access denied"}), 403

    results = get_user_results(user_id, 50)
    stats = get_user_stats(user_id)
    breakdown = get_topic_breakdown(user_id)
    trends = analyse_performance_trends(results)

    return jsonify({
        "stats": stats,
        "trends": trends,
        "breakdown": breakdown,
        "history": results[:20]
    }), 200


# ===============================
# 📄 REPORT
# ===============================

@quiz_bp.route("/report/<result_id>", methods=["GET"])
@token_required
def get_report(current_user, result_id):
    result = get_result_by_id(result_id)

    if not result:
        return jsonify({"error": "Result not found"}), 404

    pct = result.get("score", 0)

    perf_data = {
        "marks_percentage": pct,
        "correct_answers": result.get("correct_answers", 0),
        "total_questions": result.get("total_questions", 0),
        "grade": _grade(pct),
        "time_efficiency": 80,
    }

    insights = generate_exam_report_insights(
        result.get("exam_name", "Exam"),
        perf_data,
        result.get("question_breakdown", [])
    )

    return jsonify({
        "result": result,
        "insights": insights
    }), 200


# ===============================
# 🧠 AI EXPLAIN
# ===============================

@quiz_bp.route("/explain", methods=["POST"])
@token_required
def explain(current_user):
    data = request.get_json() or {}
    concept = (data.get("concept") or "").strip()

    if not concept:
        return jsonify({"error": "concept required"}), 400

    return jsonify(
        explain_concept(concept, data.get("level", "intermediate"))
    ), 200


# ===============================
# 📥 OFFLINE QUIZ GENERATION
# ===============================

@quiz_bp.route("/generate-offline/<exam_id>", methods=["GET"])
@token_required
def generate_offline_quiz(current_user, exam_id):
    exam = ExamModel.get_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    pack = generate_questions_for_exam(
        exam, "", "mcq", "medium", 20
    )

    questions = pack.get("questions", [])

    quiz_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return jsonify({
        "quiz_code": quiz_code,
        "exam": exam,
        "questions": questions,
        "suggested_duration_minutes": pack.get("suggested_duration_minutes"),
        "ai_error": pack.get("ai_error"),
    }), 200


# ===============================
# 📄 DOWNLOAD PDF
# ===============================

@quiz_bp.route("/download-offline/<exam_id>", methods=["GET"])
def download_offline_quiz(exam_id):
    exam = ExamModel.get_by_id(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    pack = generate_questions_for_exam(
        exam, "", "mcq", "medium", 10
    )

    questions = pack.get("questions", [])

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, y, f"Exam: {exam.get('name')}")
    y -= 30

    for i, q in enumerate(questions):
        # FIX: question dicts use the key "text" (see ai_service.py's
        # _sanitize_questions, which always sets both "text" and
        # "question_text") — there is no "question" key, so this was
        # printing "Q1: None" for every single question in the PDF.
        q_text = q.get("text") or q.get("question_text") or ""
        pdf.drawString(50, y, f"Q{i+1}: {q_text}")
        y -= 20

        for opt in q.get("options", []):
            pdf.drawString(70, y, f"[ ] {opt}")
            y -= 15

        y -= 10

        if y < 100:
            pdf.showPage()
            y = 750

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="quiz.pdf",
                     mimetype='application/pdf')


# ===============================
# 🧠 HELPER
# ===============================

def _grade(pct):
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B+"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    return "F"


# 🔥 NEW FUNCTION (YOU MUST ADD IN DB LAYER)
def get_result_by_offline_id(user_id, offline_id):
    """
    Check if offline attempt already synced
    Implement this in your DB layer
    """
    return None  # replace with DB query
