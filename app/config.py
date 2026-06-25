"""
QuizGen Platform Configuration
FILE LOCATION: quizgen/backend/app/config.py

Loads settings from backend/.env
"""

import os
from dotenv import load_dotenv

# Load .env from backend/ folder (parent of app/)
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_backend_dir, ".env"))


class Config:
    # ── Core Flask ──────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.getenv("FLASK_ENV", "production") == "development"
    PORT = int(os.getenv("PORT", 5000))

    # ── MongoDB Atlas ────────────────────────────────────────
    MONGO_URI = os.getenv(
        "MONGO_URL",  # aligned with your .env
        "mongodb://localhost:27017/quizgen"
    )

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))

    # ── AI (OpenRouter) ──────────────────────────────────────
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openchat/openchat-7b").strip()

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ── File Uploads ─────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(_backend_dir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    @classmethod
    def validate(cls):
        """Warn about missing critical env vars at startup."""
        warnings = []

        # AI validation
        if not cls.OPENROUTER_API_KEY:
            warnings.append(
                "OPENROUTER_API_KEY is not set. AI features will not work."
            )

        # Mongo validation
        if "localhost" in cls.MONGO_URI and cls.DEBUG is False:
            warnings.append("Using local MongoDB in production mode")

        return warnings
