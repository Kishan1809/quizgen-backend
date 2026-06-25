"""
QuizGen Platform – Flask Application Factory
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import Config
from .models.database import configure_database, init_db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    warnings = config_class.validate()
    for w in warnings:
        print(f"[CONFIG] ⚠️  {w}")

    # ── CORS ─────────────────────────────────────────────────
    # supports_credentials=True requires explicit origins (not *)
    CORS(app,
         resources={r"/*": {"origins": "*"}},
         supports_credentials=False,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])

    # Handle OPTIONS preflight manually to ensure headers always sent
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            res = app.make_default_options_response()
            res.headers["Access-Control-Allow-Origin"]  = "*"
            res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return res

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    # ── Database ─────────────────────────────────────────────
    configure_database(app)
    with app.app_context():
        init_db()

    # ── Blueprints ───────────────────────────────────────────
    from .routes.auth      import auth_bp
    from .routes.quiz      import quiz_bp
    from .routes.institute import institute_bp
    from .routes.student   import student_bp
    from .routes.practice  import practice_bp
    from .routes.tutor     import tutor_bp

    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(quiz_bp,      url_prefix="/quiz")
    app.register_blueprint(institute_bp, url_prefix="/institute")
    app.register_blueprint(student_bp,   url_prefix="/student")
    app.register_blueprint(practice_bp,  url_prefix="/practice")
    app.register_blueprint(tutor_bp,     url_prefix="/tutor")

    # ── Health Check ─────────────────────────────────────────
    @app.route("/health")
    def health():
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model   = os.getenv("OPENROUTER_MODEL", "").strip()
        return jsonify({
            "status":                "healthy",
            "service":               "QuizGen API",
            "version":               "2.0.0",
            "ai_provider":           "openrouter",
            "openrouter_configured": bool(api_key),
            "model":                 model or "not set",
        }), 200

    @app.route("/")
    def root():
        return jsonify({
            "name":    "QuizGen Platform API",
            "version": "2.0.0",
            "docs":    "/health",
        }), 200

    # ── Error Handlers ────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"message": "Route not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"message": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def unhandled(e):
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

    return app
