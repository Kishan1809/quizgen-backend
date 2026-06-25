"""Auth Routes – Register, Login, Logout, Profile."""

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..models.database import UserModel
from ..utils.auth import generate_token, token_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip() or None
    role = data.get("role", "student")  # student | institute

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if UserModel.find_by_username(username):
        return jsonify({"message": "Username already taken"}), 409

    uid = UserModel.create(username, generate_password_hash(password), email, role)
    token = generate_token(username, uid, role)

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user_id": uid,
        "username": username,
        "role": role,
        "email": email,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    user = UserModel.find_by_username(username)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid credentials"}), 401

    uid = str(user["_id"])
    role = user.get("role", "student")
    token = generate_token(username, uid, role)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user_id": uid,
        "username": username,
        "role": role,
        "email": user.get("email"),
        "profile": user.get("profile", {}),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_profile(current_user):
    from ..models.database import doc_to_json
    user = doc_to_json(current_user)
    user.pop("password", None)
    return jsonify(user), 200


@auth_bp.route("/me", methods=["PUT"])
@token_required
def update_profile(current_user):
    from ..models.database import mongo, to_oid
    data = request.get_json() or {}
    allowed = {k: v for k, v in data.items() if k in ["profile", "email"]}
    if not allowed:
        return jsonify({"message": "Nothing to update"}), 400
    mongo.db.users.update_one({"_id": current_user["_id"]}, {"$set": allowed})
    return jsonify({"message": "Profile updated"}), 200