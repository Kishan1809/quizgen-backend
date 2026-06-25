import pytesseract
from PIL import Image
from flask import Blueprint, request, jsonify, send_file
from ..utils.auth import token_required
from ..models.database import ExamModel, mongo, doc_to_json
from ..services.ai_service import generate_questions_for_exam, generate_personalised_practice
from ..services.exam_service import get_or_create_exams_for_country
from ..services.performance_service import get_user_results, get_topic_breakdown
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

practice_bp = Blueprint("practice", __name__)

CHUNK_SIZE = 5


# ============================================================
# 🔥 FIXED PDF DOWNLOAD ROUTE
# ============================================================

@practice_bp.route("/download-pdf", methods=["POST"])
@token_required
def download_pdf(current_user):
    try:
        data = request.get_json() or {}

        questions = data.get("questions", [])
        exam_name = data.get("exam_name", "Quiz")

        if not questions:
            return jsonify({"error": "No questions provided"}), 400

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)

        width, height = letter
        y = height - 50

        pdf.setFont("Helvetica", 12)

        # Title
        pdf.drawString(50, y, f"Exam: {exam_name}")
        y -= 30

        for i, q in enumerate(questions):
            # 🔥 FIX: support both 'text' and 'question'
            question_text = (
                q.get("text")
                or q.get("question")
                or q.get("question_text")
                or ""
            )

            pdf.drawString(50, y, f"Q{i+1}: {question_text[:100]}")
            y -= 20

            options = q.get("options", [])

            for opt in options:
                pdf.drawString(70, y, f"- {str(opt)[:80]}")
                y -= 15

            y -= 10

            # Page break
            if y < 100:
                pdf.showPage()
                pdf.setFont("Helvetica", 12)
                y = height - 50

        pdf.save()

        # 🔥 CRITICAL FIX
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{exam_name}.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("PDF ERROR:", e)
        return jsonify({"error": "PDF generation failed", "debug": str(e)}), 500


# ============================================================
# GET EXAMS
# ============================================================

@practice_bp.route("/exams/<country_id>", methods=["GET"])
@token_required
def get_exams(current_user, country_id):
    if not country_id:
        return jsonify({"error": "country_id is required"}), 400

    exams = get_or_create_exams_for_country(country_id)

    return jsonify({
        "exams": [
            {
                "id": str(e.get("_id", "")),
                "name": e.get("name", ""),
                "description": e.get("description", ""),
                "duration": e.get("duration", 60),
                "difficulty": e.get("difficulty", "medium"),
            }
            for e in exams
        ]
    }), 200


# ============================================================
# GENERATE QUESTIONS
# ============================================================

@practice_bp.route("/generate", methods=["POST"])
@token_required
def generate(current_user):
    data = request.get_json() or {}

    country_id = (data.get("country_id") or "").strip()
    exam_name  = (data.get("exam_name") or "").strip()
    exam_type  = (data.get("exam_type") or "mcq").lower()
    difficulty = (data.get("difficulty") or "medium").lower()
    count      = min(int(data.get("count", 10)), 20)

    exams = get_or_create_exams_for_country(country_id)
    exam = exams[0] if exams else {}

    all_questions = []

    for _ in range(count):
        try:
            pack = generate_questions_for_exam(
                exam=exam,
                country_name="",
                q_type=exam_type,
                difficulty=difficulty,
                count=1
            )

            qs = pack.get("questions", []) if isinstance(pack, dict) else []

            for q in qs:
                q["id"] = f"q{len(all_questions)+1}"

            all_questions.extend(qs)

        except Exception as e:
            print("GEN ERROR:", e)
            continue

    if not all_questions:
        return jsonify({"error": "No questions generated"}), 500

    return jsonify({
        "practice": {
            "questions": all_questions,
            "total_questions": len(all_questions)
        }
    }), 200


# ============================================================
# SAVE SESSION
# ============================================================

@practice_bp.route("/save", methods=["POST"])
@token_required
def save(current_user):
    data = request.get_json() or {}

    session = {
        "user_id": str(current_user["_id"]),
        "exam_name": data.get("exam_name", ""),
        "questions_attempted": data.get("questions_attempted", 0),
        "total_questions": data.get("total_questions", 0),
        "questions_correct": data.get("questions_correct", 0),
        "score_pct": (
            round(data.get("questions_correct", 0) /
                  max(data.get("total_questions", 1), 1) * 100)
        ),
        "created_at": datetime.utcnow().isoformat(),
    }

    mongo.db.practice_sessions.insert_one(session)

    return jsonify({"success": True}), 200


@practice_bp.route("/adaptive-next", methods=["POST"])
@token_required
def adaptive_next(current_user):
    try:
        data = request.get_json()

        accuracy = data.get("accuracy", 50)
        exam_name = data.get("exam_name", "JEE Main")

        # 🎯 Decide difficulty
        if accuracy >= 80:
            difficulty = "hard"
        elif accuracy >= 50:
            difficulty = "medium"
        else:
            difficulty = "easy"

        # 🔥 Generate 1 question
        pack = generate_questions_for_exam(
            exam={"name": exam_name},
            country_name="",
            q_type="mcq",
            difficulty=difficulty,
            count=1
        )

        questions = pack.get("questions", [])

        return jsonify({
            "question": questions[0] if questions else None,
            "difficulty": difficulty
        })

    except Exception as e:
        print("ADAPTIVE ERROR:", e)
        return jsonify({"error": "Failed to generate adaptive question"}), 500

@practice_bp.route("/scan", methods=["POST"])
@token_required
def scan_image(current_user):
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]
        img = Image.open(file)

        text = pytesseract.image_to_string(img)

        return jsonify({"text": text.strip()})

    except Exception as e:
        print("SCAN ERROR:", e)
        return jsonify({"error": "Scan failed"}), 500
