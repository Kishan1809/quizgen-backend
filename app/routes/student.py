"""Student Routes – Find exams, attempt, submit, view reports."""

from datetime import datetime
from flask import Blueprint, request, jsonify
from bson import ObjectId

from ..models.database import (
    InstituteExamModel, AttemptModel, ReportModel,
    CheatingLogModel, mongo, doc_to_json, to_oid
)
from ..services.ai_service import (
    generate_exam_report_insights, evaluate_descriptive_answer
)

student_bp = Blueprint("student", __name__)


# ── Search Exams by Institute ID / Name ─────────────────────

@student_bp.route("/exams/<institute_ref>", methods=["GET"])
def search_exams(institute_ref):
    query = {
        "$or": [
            {"institute_id":   institute_ref},
            {"institute_name": {"$regex": institute_ref, "$options": "i"}},
            {"exam_id":        {"$regex": institute_ref, "$options": "i"}},
        ],
        "published": True,
    }
    exams = InstituteExamModel.get_all(query)
    return jsonify(exams), 200


# ── Get Single Exam (public, no auth needed) ─────────────────

@student_bp.route("/exam/<exam_identifier>", methods=["GET"])
def get_exam(exam_identifier):
    exam = InstituteExamModel.find_by_exam_id(exam_identifier)
    if not exam:
        try:
            raw = mongo.db.institute_exams.find_one({"_id": to_oid(exam_identifier)})
            exam = doc_to_json(raw)
        except Exception:
            pass
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    return jsonify(exam), 200


# ── Start Attempt ────────────────────────────────────────────

@student_bp.route("/attempt/<exam_id>", methods=["POST"])
def start_attempt(exam_id):
    data = request.get_json(force=True) or {}
    student_id   = data.get("student_id", "anonymous")
    student_name = data.get("student_name", "Student")
    student_email= data.get("student_email", "")

    exam = InstituteExamModel.find_by_exam_id(exam_id)
    if not exam:
        return jsonify({"success": False, "error": "Exam not found"}), 404

    existing = AttemptModel.find_by_student_and_exam(student_id, exam_id)
    if existing:
        return jsonify({
            "success": False,
            "error": "Already attempted",
            "message": "You have already attempted this exam."
        }), 409

    attempt_doc = {
        "student_id":    student_id,
        "student_name":  student_name,
        "student_email": student_email,
        "exam_id":       exam_id,
        "exam_db_id":    exam.get("_id", ""),
        "exam_name":     exam.get("name", ""),
        "institute_name":exam.get("institute_name", ""),
        "started_at":    datetime.utcnow(),
        "status":        "in_progress",
        "answers":       [],
        "cheating_detected": False,
    }
    attempt_id = AttemptModel.create(attempt_doc)

    return jsonify({
        "success":    True,
        "attempt_id": attempt_id,
        "exam": {
            "id":          exam.get("exam_id"),
            "name":        exam.get("name"),
            "description": exam.get("description"),
            "type":        exam.get("type"),
            "duration":    exam.get("duration"),
            "total_marks": exam.get("total_marks"),
            "questions":   exam.get("questions", []),
        },
        "cheating_detection_enabled": exam.get("cheating_detection", False),
    }), 200


# ── Submit Attempt ───────────────────────────────────────────

@student_bp.route("/submit/<attempt_id>", methods=["POST"])
def submit_attempt(attempt_id):
    data    = request.get_json(force=True) or {}
    answers = data.get("answers", {})
    time_taken = data.get("time_taken", 0)

    attempt = AttemptModel.find_by_id(attempt_id)
    if not attempt:
        return jsonify({"success": False, "error": "Attempt not found"}), 404

    # Load exam
    exam = InstituteExamModel.find_by_exam_id(attempt["exam_id"])
    if not exam:
        return jsonify({"success": False, "error": "Exam not found"}), 404

    questions   = exam.get("questions", [])
    total_marks = exam.get("total_marks") or sum(q.get("marks", 1) for q in questions)
    passing     = exam.get("passing_marks", round(total_marks * 0.4))

    obtained     = 0
    answers_list = []
    descriptive_evals = []

    for i, q in enumerate(questions):
        qid          = q.get("id", str(i))
        correct_ans  = q.get("correctAnswer")
        marks        = q.get("marks", 1)
        student_ans  = answers.get(qid)
        qtype        = q.get("type", "mcq")

        is_correct = None
        marks_got  = 0

        if qtype == "mcq" and correct_ans is not None:
            if student_ans is not None:
                try:
                    is_correct = int(student_ans) == int(correct_ans)
                except Exception:
                    is_correct = str(student_ans).strip() == str(correct_ans).strip()
                marks_got = marks if is_correct else 0
                obtained += marks_got
        elif qtype == "descriptive":
            # AI evaluation of descriptive answers
            if student_ans and len(str(student_ans).strip()) > 5:
                eval_result = evaluate_descriptive_answer(q.get("text", ""), str(student_ans), marks)
                marks_got   = eval_result.get("score", 0)
                obtained   += marks_got
                descriptive_evals.append({
                    "question_number": i + 1,
                    "score":    marks_got,
                    "max_score": marks,
                    "feedback": eval_result.get("feedback", ""),
                })

        answers_list.append({
            "question_id":   qid,
            "question_text": q.get("text", ""),
            "student_answer":student_ans,
            "correct_answer":correct_ans,
            "is_correct":    is_correct,
            "marks_obtained":marks_got,
            "total_marks":   marks,
            "question_type": qtype,
        })

    percentage = round(obtained / total_marks * 100, 2) if total_marks else 0
    passed     = obtained >= passing
    now        = datetime.utcnow()

    AttemptModel.update(attempt_id, {
        "status":          "completed",
        "completed_at":    now,
        "answers":         answers_list,
        "obtained_marks":  obtained,
        "total_marks":     total_marks,
        "percentage":      percentage,
        "passed":          passed,
        "time_taken_minutes": time_taken,
    })

    # Generate report
    perf_data = {
        "marks_percentage": percentage,
        "correct_answers":  sum(1 for a in answers_list if a.get("is_correct")),
        "total_questions":  len(answers_list),
        "grade":            _grade(percentage),
        "time_efficiency":  min((time_taken / exam.get("duration", 60)) * 100, 100),
    }
    ai_insights = generate_exam_report_insights(
        exam.get("name", "Exam"), perf_data, answers_list
    )

    report_doc = {
        "report_id":         str(ObjectId()),
        "attempt_id":        attempt_id,
        "student_id":        attempt["student_id"],
        "student_name":      attempt.get("student_name", ""),
        "exam_id":           attempt["exam_id"],
        "exam_name":         exam.get("name", ""),
        "institute_name":    exam.get("institute_name", ""),
        "subject":           exam.get("subject", ""),
        "generated_at":      now,
        "exam_details": {
            "name":        exam.get("name"),
            "type":        exam.get("type"),
            "duration":    exam.get("duration"),
            "difficulty":  exam.get("difficulty"),
            "total_marks": total_marks,
            "passing_marks": passing,
            "total_questions": len(questions),
        },
        "performance": {
            **perf_data,
            "obtained_marks": obtained,
            "passed":          passed,
            "time_taken":      time_taken,
            "performance_level": ai_insights.get("performance_level", ""),
        },
        "answers_analysis":   answers_list,
        "descriptive_evals":  descriptive_evals,
        "insights":           ai_insights.get("insights", []),
        "strengths":          ai_insights.get("strengths", []),
        "weaknesses":         ai_insights.get("weaknesses", []),
        "recommendations":    ai_insights.get("recommendations", []),
        "study_plan":         ai_insights.get("study_plan", {}),
    }
    ReportModel.create(report_doc)

    return jsonify({
        "success":   True,
        "report_id": report_doc["report_id"],
        "score":     obtained,
        "percentage":percentage,
        "passed":    passed,
        "grade":     perf_data["grade"],
        "message":   "Exam submitted! Report generated.",
    }), 200


# ── Get Report ───────────────────────────────────────────────

@student_bp.route("/report/<report_id>", methods=["GET"])
def get_report(report_id):
    report = ReportModel.find_by_report_id(report_id)
    if not report:
        attempt = AttemptModel.find_by_id(report_id)
        if attempt:
            report = ReportModel.find_by_attempt(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    logs = CheatingLogModel.get_by_attempt(report.get("attempt_id", ""))
    report["cheating_logs"] = logs
    return jsonify(report), 200


# ── Student History ──────────────────────────────────────────

@student_bp.route("/history/<student_id>", methods=["GET"])
def get_history(student_id):
    attempts = AttemptModel.get_student_history(student_id)
    reports  = ReportModel.get_student_reports(student_id)
    return jsonify({"attempts": attempts, "reports": reports}), 200


# ── Helpers ──────────────────────────────────────────────────

def _grade(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B+"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    return "F"