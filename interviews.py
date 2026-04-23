"""
interviews.py  —  Interview Routes
Save interviews, retrieve history, serve video/audio recordings
"""

import os
import json
import base64
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, Interview, QAPair, EmotionLog, User
from datetime import datetime

interviews_bp = Blueprint("interviews", __name__)

# Where video/audio files are stored
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
os.makedirs(os.path.join(MEDIA_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "audios"), exist_ok=True)


# ── SAVE INTERVIEW (called at end of interview) ───────────────────────────────
@interviews_bp.route("/api/interviews/save", methods=["POST"])
@jwt_required()
def save_interview():
    """
    Save a completed interview including Q&A, emotion log, scores, video & audio.
    Body: {
      topic, overall_score, nlp_score, confidence_score, clarity_score,
      dominant_emotion, grade, ai_report, duration_secs,
      qa_pairs: [{question, answer, overall_score, clarity_score,
                  relevance_score, confidence_score, word_count,
                  filler_words, sentiment, feedback}],
      emotion_log: [{emotion, confidence, timestamp}],
      video_blob: "base64...",   ← optional
      audio_blob: "base64..."    ← optional
    }
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    # ── Create interview record ───────────────────────────────────────────────
    interview = Interview(
        user_id          = user_id,
        topic            = data.get("topic", "general"),
        overall_score    = data.get("overall_score", 0),
        nlp_score        = data.get("nlp_score", 0),
        confidence_score = data.get("confidence_score", 0),
        clarity_score    = data.get("clarity_score", 0),
        dominant_emotion = data.get("dominant_emotion", "neutral"),
        grade            = data.get("grade", "—"),
        ai_report        = data.get("ai_report", ""),
        duration_secs    = data.get("duration_secs", 0),
        questions_count  = len(data.get("qa_pairs", []))
    )
    db.session.add(interview)
    db.session.flush()   # Get interview.id before committing

    # ── Save Q&A pairs ────────────────────────────────────────────────────────
    for i, qa in enumerate(data.get("qa_pairs", []), start=1):
        pair = QAPair(
            interview_id    = interview.id,
            question_number = i,
            question        = qa.get("question", ""),
            answer          = qa.get("answer", ""),
            overall_score   = qa.get("overall_score", 0),
            clarity_score   = qa.get("clarity_score", 0),
            relevance_score = qa.get("relevance_score", 0),
            confidence_score= qa.get("confidence_score", 0),
            word_count      = qa.get("word_count", 0),
            filler_words    = qa.get("filler_words", 0),
            sentiment       = qa.get("sentiment", 0),
            feedback        = json.dumps(qa.get("feedback", []))
        )
        db.session.add(pair)

    # ── Save emotion log ──────────────────────────────────────────────────────
    for em in data.get("emotion_log", []):
        log = EmotionLog(
            interview_id = interview.id,
            emotion      = em.get("emotion", "neutral"),
            confidence   = em.get("confidence", 0),
            timestamp    = em.get("timestamp", 0)
        )
        db.session.add(log)

    # ── Save video blob ───────────────────────────────────────────────────────
    video_blob = data.get("video_blob")
    if video_blob:
        try:
            video_data = base64.b64decode(
                video_blob.split(",")[1] if "," in video_blob else video_blob
            )
            filename  = f"interview_{interview.id}_{user_id}.webm"
            filepath  = os.path.join(MEDIA_DIR, "videos", filename)
            with open(filepath, "wb") as f:
                f.write(video_data)
            interview.video_path = f"videos/{filename}"
        except Exception as e:
            print(f"Video save error: {e}")

    # ── Save audio blob ───────────────────────────────────────────────────────
    audio_blob = data.get("audio_blob")
    if audio_blob:
        try:
            audio_data = base64.b64decode(
                audio_blob.split(",")[1] if "," in audio_blob else audio_blob
            )
            filename  = f"interview_{interview.id}_{user_id}.webm"
            filepath  = os.path.join(MEDIA_DIR, "audios", filename)
            with open(filepath, "wb") as f:
                f.write(audio_data)
            interview.audio_path = f"audios/{filename}"
        except Exception as e:
            print(f"Audio save error: {e}")

    db.session.commit()

    return jsonify({
        "success":      True,
        "message":      "Interview saved successfully!",
        "interview_id": interview.id
    }), 201


# ── GET HISTORY (list of all past interviews) ─────────────────────────────────
@interviews_bp.route("/api/interviews/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = int(get_jwt_identity())
    page    = request.args.get("page", 1, type=int)
    per_page= request.args.get("per_page", 10, type=int)
    topic   = request.args.get("topic")   # optional filter

    query = Interview.query.filter_by(user_id=user_id).order_by(Interview.created_at.desc())
    if topic:
        query = query.filter_by(topic=topic)

    total      = query.count()
    interviews = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "success":    True,
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "interviews": [i.to_dict() for i in interviews]
    })


# ── GET SINGLE INTERVIEW (full detail) ───────────────────────────────────────
@interviews_bp.route("/api/interviews/<int:interview_id>", methods=["GET"])
@jwt_required()
def get_interview(interview_id):
    user_id   = int(get_jwt_identity())
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()

    if not interview:
        return jsonify({"success": False, "error": "Interview not found"}), 404

    return jsonify({
        "success":   True,
        "interview": interview.to_dict(include_qa=True)
    })


# ── DELETE INTERVIEW ──────────────────────────────────────────────────────────
@interviews_bp.route("/api/interviews/<int:interview_id>", methods=["DELETE"])
@jwt_required()
def delete_interview(interview_id):
    user_id   = int(get_jwt_identity())
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()

    if not interview:
        return jsonify({"success": False, "error": "Interview not found"}), 404

    # Delete media files
    for path in [interview.video_path, interview.audio_path]:
        if path:
            full = os.path.join(MEDIA_DIR, path)
            if os.path.exists(full):
                os.remove(full)

    db.session.delete(interview)
    db.session.commit()
    return jsonify({"success": True, "message": "Interview deleted"})


# ── SERVE VIDEO FILE ──────────────────────────────────────────────────────────
@interviews_bp.route("/api/media/video/<int:interview_id>", methods=["GET"])
@jwt_required()
def serve_video(interview_id):
    user_id   = int(get_jwt_identity())
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()

    if not interview or not interview.video_path:
        return jsonify({"error": "Video not found"}), 404

    filepath = os.path.join(MEDIA_DIR, interview.video_path)
    if not os.path.exists(filepath):
        return jsonify({"error": "Video file missing"}), 404

    return send_file(filepath, mimetype="video/webm")


# ── SERVE AUDIO FILE ──────────────────────────────────────────────────────────
@interviews_bp.route("/api/media/audio/<int:interview_id>", methods=["GET"])
@jwt_required()
def serve_audio(interview_id):
    user_id   = int(get_jwt_identity())
    interview = Interview.query.filter_by(id=interview_id, user_id=user_id).first()

    if not interview or not interview.audio_path:
        return jsonify({"error": "Audio not found"}), 404

    filepath = os.path.join(MEDIA_DIR, interview.audio_path)
    if not os.path.exists(filepath):
        return jsonify({"error": "Audio file missing"}), 404

    return send_file(filepath, mimetype="audio/webm")


# ── DASHBOARD STATS ───────────────────────────────────────────────────────────
@interviews_bp.route("/api/interviews/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id    = int(get_jwt_identity())
    interviews = Interview.query.filter_by(user_id=user_id).order_by(Interview.created_at).all()

    if not interviews:
        return jsonify({"success": True, "stats": {}})

    scores_over_time = [
        {"date": i.created_at.strftime("%b %d"), "score": round(i.overall_score, 1)}
        for i in interviews
    ]

    topic_counts = {}
    for i in interviews:
        topic_counts[i.topic] = topic_counts.get(i.topic, 0) + 1

    emotion_totals = {}
    for i in interviews:
        e = i.dominant_emotion
        emotion_totals[e] = emotion_totals.get(e, 0) + 1

    avg_score = sum(i.overall_score for i in interviews) / len(interviews)

    return jsonify({
        "success": True,
        "stats": {
            "total":            len(interviews),
            "avg_score":        round(avg_score, 1),
            "best_score":       round(max(i.overall_score for i in interviews), 1),
            "scores_over_time": scores_over_time,
            "topic_counts":     topic_counts,
            "emotion_totals":   emotion_totals,
            "recent":           [i.to_dict() for i in interviews[-3:]]
        }
    })
