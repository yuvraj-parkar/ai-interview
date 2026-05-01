from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.services.groq_client import call_groq, QUESTION_BANK
from backend.services.nlp_analyzer import analyze_answer
from backend.services.emotion_detector import analyze_emotion

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/api/generate-question", methods=["POST"])
@jwt_required()
def generate_question():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "general").lower()
    q_num = data.get("question_number", 1)
    prev = data.get("previous_answers", [])

    sys_prompt = (
        "You are a professional interviewer. Ask ONE clear interview question. "
        "No preamble. Just the question. Start easy, increase difficulty gradually."
    )
    ctx = "\n".join(f"A{i+1}: {a[:150]}" for i, a in enumerate(prev[-2:])) if prev else ""
    usr_prompt = f"Topic: {topic}\nQuestion #{q_num}\n{ctx}\nAsk the next question."

    question = call_groq(sys_prompt, usr_prompt, 80)
    if "[LLM_ERROR" in question:
        bank = QUESTION_BANK.get(topic, QUESTION_BANK["general"])
        question = bank[(q_num - 1) % len(bank)]

    return jsonify({"success": True, "question": question})


@ai_bp.route("/api/analyze-answer", methods=["POST"])
@jwt_required()
def api_analyze_answer():
    data = request.get_json(silent=True) or {}
    answer = data.get("answer", "")
    question = data.get("question", "")
    if not answer:
        return jsonify({"success": False, "error": "No answer"}), 400
    return jsonify(analyze_answer(answer, question))


@ai_bp.route("/api/analyze-emotion", methods=["POST"])
@jwt_required()
def api_analyze_emotion():
    data = request.get_json(silent=True) or {}
    image = data.get("image", "")
    if not image:
        return jsonify({"success": False, "error": "No image"}), 400
    return jsonify(analyze_emotion(image))


@ai_bp.route("/api/final-report", methods=["POST"])
@jwt_required()
def api_final_report():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "general")
    qa_pairs = data.get("qa_pairs", [])
    avg_emotion = data.get("avg_emotion", "neutral")
    avg_score = data.get("avg_nlp_score", 50)

    summary = "\n".join(
        f"Q{i+1}: {qa['question']}\nA: {str(qa.get('answer', ''))[:200]}\nScore: {qa.get('score', 0)}/100"
        for i, qa in enumerate(qa_pairs[:5])
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
        grade = "Good" if avg_score >= 70 else "Average" if avg_score >= 50 else "Needs Work"
        report = (
            f"Performance: {grade}\n\n"
            f"• Overall Score: {avg_score}/100\n"
            f"• Emotion: {avg_emotion}\n\n"
            f"Tips:\n• Use STAR method\n• Give specific examples\n• Practice confident delivery"
        )

    return jsonify({"success": True, "report": report, "overall_score": avg_score})


@ai_bp.route("/api/topics", methods=["GET"])
def get_topics():
    return jsonify({"topics": [
        {"id": "general", "label": "General HR", "icon": "👤"},
        {"id": "python", "label": "Python", "icon": "🐍"},
        {"id": "machine learning", "label": "Machine Learning", "icon": "🤖"},
        {"id": "data structures", "label": "Data Structures", "icon": "🌳"},
        {"id": "javascript", "label": "JavaScript", "icon": "⚡"},
        {"id": "system design", "label": "System Design", "icon": "🏗️"},
    ]})
