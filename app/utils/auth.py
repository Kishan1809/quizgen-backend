"""
Authentication Utilities – JWT generation, verification, and decorators.
"""

import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from app.models.database import UserModel


def generate_token(username: str, user_id: str, role: str = "student") -> str:
    payload = {
        "username": username,
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(
            hours=current_app.config.get("JWT_EXPIRY_HOURS", 24)
        ),
        "iat": datetime.datetime.utcnow(),
    }
    secret = current_app.config.get("JWT_SECRET_KEY") or current_app.config["SECRET_KEY"]
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str):
    try:
        secret = current_app.config.get("JWT_SECRET_KEY") or current_app.config["SECRET_KEY"]
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _extract_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return auth_header or None


def token_required(f):
    """Protect a route – injects `current_user` as the first argument."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"message": "Authentication token missing"}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({"message": "Invalid or expired token"}), 401
        user = UserModel.find_by_username(payload["username"])
        if not user:
            return jsonify({"message": "User account not found"}), 401
        return f(user, *args, **kwargs)
    return decorated


def role_required(*roles):
    """Extend token_required to also check the user's role."""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user.get("role") not in roles:
                return jsonify({"message": "Insufficient permissions"}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator