"""
QuizGen Platform – Flask Application Factory
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS

# ── Use RELATIVE imports ──────────
from .config import Config
from .models.database import configure_database, init_db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Warn about missing config ────────────────────────────
    warnings = config_class.validate()
    for w in warnings:
        print(f"[CONFIG] ⚠️  {w}")

    # ── CORS ─────────────────────────────────────────────────
    CORS(app, resources={
        r"/*": {
            "origins": [
                config_class.FRONTEND_URL,
                "http://localhost:3000",
                "http://localhost:5173",
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
        }
    })

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

    # ── Health Check (UPDATED FOR OPENROUTER) ─────────────────
    @app.route("/health")
    def health():
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip()

        return jsonify({
            "status": "healthy",
            "service": "QuizGen API",
            "version": "2.0.0",
            "ai_provider": "openrouter",
            "openrouter_configured": bool(api_key),
            "model": model or "not set",
        }), 200

    @app.route("/")
    def root():
        return jsonify({
            "name": "QuizGen Platform API",
            "version": "2.0.0",
            "docs": "/health",
        }), 200

    # ── Global Error Handlers ────────────────────────────────
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
