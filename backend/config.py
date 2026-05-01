import os
from datetime import timedelta
from urllib.parse import quote_plus


class Config:
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASS = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_DB = os.environ.get("MYSQL_DB", "ai_interview")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASS)}@{MYSQL_HOST}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "ai-interview-secret-2024")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ["headers", "query_string"]
    JWT_QUERY_STRING_NAME = "token"

    MAX_CONTENT_LENGTH = 200 * 1024 * 1024

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL = "llama3-8b-8192"
