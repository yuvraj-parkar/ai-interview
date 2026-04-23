"""
database.py  —  MySQL Database Setup & Models
Run this file ONCE to create all tables:  python database.py

Requirements:
    pip install flask-sqlalchemy pymysql flask-bcrypt flask-jwt-extended

MySQL setup:
    CREATE DATABASE ai_interview;
    CREATE USER 'interviewuser'@'localhost' IDENTIFIED BY 'interview@123';
    GRANT ALL PRIVILEGES ON ai_interview.* TO 'interviewuser'@'localhost';
    FLUSH PRIVILEGES;
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()


# ── USERS ────────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    avatar     = db.Column(db.String(10), default="👤")   # emoji avatar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    interviews = db.relationship("Interview", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw):
        self.password = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password, raw)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "avatar":     self.avatar,
            "created_at": self.created_at.isoformat(),
            "total_interviews": len(self.interviews)
        }


# ── INTERVIEWS ────────────────────────────────────────────────────────────────
class Interview(db.Model):
    __tablename__ = "interviews"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic           = db.Column(db.String(100), nullable=False)
    overall_score   = db.Column(db.Float, default=0)
    nlp_score       = db.Column(db.Float, default=0)
    confidence_score= db.Column(db.Float, default=0)
    clarity_score   = db.Column(db.Float, default=0)
    dominant_emotion= db.Column(db.String(50), default="neutral")
    grade           = db.Column(db.String(5), default="—")
    ai_report       = db.Column(db.Text)
    video_path      = db.Column(db.String(500))   # relative path to saved video
    audio_path      = db.Column(db.String(500))   # relative path to saved audio
    duration_secs   = db.Column(db.Integer, default=0)
    questions_count = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user      = db.relationship("User", back_populates="interviews")
    qa_pairs  = db.relationship("QAPair", back_populates="interview", cascade="all, delete-orphan")
    emotions  = db.relationship("EmotionLog", back_populates="interview", cascade="all, delete-orphan")

    def to_dict(self, include_qa=False):
        d = {
            "id":               self.id,
            "topic":            self.topic,
            "overall_score":    round(self.overall_score, 1),
            "nlp_score":        round(self.nlp_score, 1),
            "confidence_score": round(self.confidence_score, 1),
            "clarity_score":    round(self.clarity_score, 1),
            "dominant_emotion": self.dominant_emotion,
            "grade":            self.grade,
            "ai_report":        self.ai_report,
            "video_path":       self.video_path,
            "audio_path":       self.audio_path,
            "duration_secs":    self.duration_secs,
            "questions_count":  self.questions_count,
            "created_at":       self.created_at.isoformat(),
        }
        if include_qa:
            d["qa_pairs"] = [q.to_dict() for q in self.qa_pairs]
            d["emotions"]  = [e.to_dict() for e in self.emotions]
        return d


# ── Q&A PAIRS ─────────────────────────────────────────────────────────────────
class QAPair(db.Model):
    __tablename__ = "qa_pairs"

    id              = db.Column(db.Integer, primary_key=True)
    interview_id    = db.Column(db.Integer, db.ForeignKey("interviews.id"), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    question        = db.Column(db.Text, nullable=False)
    answer          = db.Column(db.Text)
    overall_score   = db.Column(db.Float, default=0)
    clarity_score   = db.Column(db.Float, default=0)
    relevance_score = db.Column(db.Float, default=0)
    confidence_score= db.Column(db.Float, default=0)
    word_count      = db.Column(db.Integer, default=0)
    filler_words    = db.Column(db.Integer, default=0)
    sentiment       = db.Column(db.Float, default=0)
    feedback        = db.Column(db.Text)   # JSON list stored as text

    interview = db.relationship("Interview", back_populates="qa_pairs")

    def to_dict(self):
        import json
        return {
            "question_number":  self.question_number,
            "question":         self.question,
            "answer":           self.answer,
            "overall_score":    round(self.overall_score, 1),
            "clarity_score":    round(self.clarity_score, 1),
            "relevance_score":  round(self.relevance_score, 1),
            "confidence_score": round(self.confidence_score, 1),
            "word_count":       self.word_count,
            "filler_words":     self.filler_words,
            "sentiment":        self.sentiment,
            "feedback":         json.loads(self.feedback) if self.feedback else []
        }


# ── EMOTION LOG ───────────────────────────────────────────────────────────────
class EmotionLog(db.Model):
    __tablename__ = "emotion_logs"

    id           = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interviews.id"), nullable=False)
    emotion      = db.Column(db.String(50))
    confidence   = db.Column(db.Float, default=0)
    timestamp    = db.Column(db.Integer, default=0)   # seconds into interview

    interview = db.relationship("Interview", back_populates="emotions")

    def to_dict(self):
        return {
            "emotion":    self.emotion,
            "confidence": self.confidence,
            "timestamp":  self.timestamp
        }


# ── CREATE TABLES ─────────────────────────────────────────────────────────────
def init_db(app):
    db.init_app(app)
    bcrypt.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ All MySQL tables created successfully!")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    init_db(app)
