"""
app.py  —  AI Interview Backend (v2 with Login + MySQL + Media Storage)

Install all dependencies:
    pip install -r requirements.txt

Setup MySQL first, then run:
    python app.py

Environment variables (or edit config below):
    MYSQL_USER       = interviewuser
    MYSQL_PASSWORD   = interview@123
    MYSQL_HOST       = localhost
    MYSQL_DB         = ai_interview
    JWT_SECRET_KEY   = your-secret-key
    GROQ_API_KEY     = your-groq-key (free at console.groq.com)
"""

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta

from database import db, bcrypt, init_db
from auth import auth_bp
from interviews import interviews_bp
from emotion_detector import analyze_emotion
from nlp_analyzer import analyze_answer


# ═══════════════════════════════════════════════════════════════════════
#  APP FACTORY
# ═══════════════════════════════════════════════════════════════════════
def create_app():
    app = Flask(__name__)

    # ── Config ───────────────────────────────────────────────────────────
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASS = os.environ.get("MYSQL_PASSWORD", "yuvraj@04")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_DB   = os.environ.get("MYSQL_DB", "ai_interview")

    from urllib.parse import quote_plus
    app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASS)}@{MYSQL_HOST}/{MYSQL_DB}"

    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"]       = os.environ.get("JWT_SECRET_KEY", "ai-interview-secret-2024")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
    app.config["MAX_CONTENT_LENGTH"]   = 200 * 1024 * 1024   # 200 MB upload limit

    # ── Extensions ───────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    init_db(app)

    # ── Blueprints ────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(interviews_bp)

    return app


app = create_app()

# ═══════════════════════════════════════════════════════════════════════
#  GROQ LLM CONFIG (Free at console.groq.com)
# ═══════════════════════════════════════════════════════════════════════
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_FREE_GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-8b-8192"

QUESTION_BANK = {
    "python":           ["Explain list vs tuple.", "What is a decorator?", "Explain the GIL.", "What is a generator?", "Explain *args and **kwargs."],
    "machine learning": ["What is overfitting?", "Explain gradient descent.", "What is cross-validation?", "Explain the bias-variance tradeoff.", "What is regularization?"],
    "data structures":  ["Stack vs Queue?", "Explain hash tables.", "Binary search tree complexity?", "When to use linked list?", "Explain dynamic programming."],
    "javascript":       ["var vs let vs const?", "What is closure?", "Explain promises.", "What is the event loop?", "Explain async/await."],
    "system design":    ["How to design a URL shortener?", "Explain load balancing.", "What is CAP theorem?", "How does caching work?", "Explain microservices."],
    "general":          ["Tell me about yourself.", "Your greatest strength?", "Where in 5 years?", "Describe a challenge you overcame.", "Why should we hire you?"]
}


def call_groq(system_prompt, user_prompt, max_tokens=400):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=15)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM_ERROR:{e}]"


# ═══════════════════════════════════════════════════════════════════════
#  INTERVIEW AI ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/generate-question", methods=["POST"])
@jwt_required()
def generate_question():
    data       = request.get_json(silent=True) or {}
    topic      = data.get("topic", "general").lower()
    q_num      = data.get("question_number", 1)
    prev       = data.get("previous_answers", [])

    sys_prompt = (
        "You are a professional interviewer. Ask ONE clear interview question. "
        "No preamble. Just the question. Start easy, increase difficulty gradually."
    )
    ctx = "\n".join(f"A{i+1}: {a[:150]}" for i,a in enumerate(prev[-2:])) if prev else ""
    usr_prompt = f"Topic: {topic}\nQuestion #{q_num}\n{ctx}\nAsk the next question."

    question = call_groq(sys_prompt, usr_prompt, 80)
    if "[LLM_ERROR" in question:
        bank = QUESTION_BANK.get(topic, QUESTION_BANK["general"])
        question = bank[(q_num - 1) % len(bank)]

    return jsonify({"success": True, "question": question})


@app.route("/api/analyze-answer", methods=["POST"])
@jwt_required()
def api_analyze_answer():
    data     = request.get_json(silent=True) or {}
    answer   = data.get("answer", "")
    question = data.get("question", "")
    if not answer:
        return jsonify({"success": False, "error": "No answer"}), 400
    return jsonify(analyze_answer(answer, question))


@app.route("/api/analyze-emotion", methods=["POST"])
@jwt_required()
def api_analyze_emotion():
    data  = request.get_json(silent=True) or {}
    image = data.get("image", "")
    if not image:
        return jsonify({"success": False, "error": "No image"}), 400
    return jsonify(analyze_emotion(image))


@app.route("/api/final-report", methods=["POST"])
@jwt_required()
def api_final_report():
    data       = request.get_json(silent=True) or {}
    topic      = data.get("topic", "general")
    qa_pairs   = data.get("qa_pairs", [])
    avg_emotion= data.get("avg_emotion", "neutral")
    avg_score  = data.get("avg_nlp_score", 50)

    summary = "\n".join(
        f"Q{i+1}: {qa['question']}\nA: {str(qa.get('answer',''))[:200]}\nScore: {qa.get('score',0)}/100"
        for i,qa in enumerate(qa_pairs[:5])
    )
    sys_prompt = (
        "You are an expert interview coach. Write a detailed, constructive interview "
        "performance report. Include: strengths, areas to improve, and 3 action tips. "
        "Be encouraging. Use bullet points. Max 300 words."
    )
    usr_prompt = (
        f"Topic: {topic}\nAvg Score: {avg_score}/100\nDominant Emotion: {avg_emotion}\n\n"
        f"Interview:\n{summary}\n\nWrite the report."
    )
    report = call_groq(sys_prompt, usr_prompt, 500)
    if "[LLM_ERROR" in report:
        grade  = "Good" if avg_score >= 70 else "Average" if avg_score >= 50 else "Needs Work"
        report = (
            f"Performance: {grade}\n\n"
            f"• Overall Score: {avg_score}/100\n"
            f"• Emotion: {avg_emotion}\n\n"
            f"Tips:\n• Use STAR method\n• Give specific examples\n• Practice confident delivery"
        )

    return jsonify({"success": True, "report": report, "overall_score": avg_score})


@app.route("/api/topics", methods=["GET"])
def get_topics():
    return jsonify({"topics": [
        {"id": "general",          "label": "General HR",       "icon": "👤"},
        {"id": "python",           "label": "Python",           "icon": "🐍"},
        {"id": "machine learning", "label": "Machine Learning", "icon": "🤖"},
        {"id": "data structures",  "label": "Data Structures",  "icon": "🌳"},
        {"id": "javascript",       "label": "JavaScript",       "icon": "⚡"},
        {"id": "system design",    "label": "System Design",    "icon": "🏗️"},
    ]})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "AI Interview v2 Backend ✅", "version": "2.0"})


if __name__ == "__main__":
    print("🚀 AI Interview v2 starting → http://localhost:5000")
    print("📌 Set GROQ_API_KEY env variable (free at console.groq.com)")
    app.run(debug=True, host="0.0.0.0", port=5000)
