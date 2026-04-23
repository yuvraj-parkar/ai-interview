"""
auth.py  —  Authentication Routes
Register / Login / Logout / Profile using JWT tokens
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from database import db, User
from datetime import timedelta
import re

auth_bp = Blueprint("auth", __name__)

# Simple email validator
def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


# ── REGISTER ──────────────────────────────────────────────────────────────────
@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    # Validation
    if not name or len(name) < 2:
        return jsonify({"success": False, "error": "Name must be at least 2 characters"}), 400
    if not valid_email(email):
        return jsonify({"success": False, "error": "Invalid email address"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Email already registered"}), 409

    # Pick avatar based on name initial
    avatars = ["🧑‍💻", "👩‍💼", "🧑‍🎓", "👨‍🔬", "👩‍🏫", "🧑‍🚀"]
    avatar  = avatars[ord(name[0].upper()) % len(avatars)]

    user = User(name=name, email=email, avatar=avatar)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(days=7)
    )

    return jsonify({
        "success": True,
        "message": "Account created successfully!",
        "token":   token,
        "user":    user.to_dict()
    }), 201


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(days=7)
    )

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name}!",
        "token":   token,
        "user":    user.to_dict()
    })


# ── PROFILE ───────────────────────────────────────────────────────────────────
@auth_bp.route("/api/auth/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)

    # Stats summary
    interviews = user.interviews
    avg_score  = (
        sum(i.overall_score for i in interviews) / len(interviews)
        if interviews else 0
    )
    best_score = max((i.overall_score for i in interviews), default=0)

    return jsonify({
        "success": True,
        "user":    user.to_dict(),
        "stats": {
            "total_interviews": len(interviews),
            "avg_score":        round(avg_score, 1),
            "best_score":       round(best_score, 1),
            "topics_practiced": list(set(i.topic for i in interviews))
        }
    })


# ── UPDATE PROFILE ────────────────────────────────────────────────────────────
@auth_bp.route("/api/auth/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    data    = request.get_json(silent=True) or {}

    if data.get("name"):
        user.name = data["name"].strip()
    if data.get("avatar"):
        user.avatar = data["avatar"]
    if data.get("new_password") and data.get("current_password"):
        if not user.check_password(data["current_password"]):
            return jsonify({"success": False, "error": "Current password incorrect"}), 400
        user.set_password(data["new_password"])

    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()})
