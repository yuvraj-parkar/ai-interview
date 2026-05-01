import requests
from backend.config import Config

QUESTION_BANK = {
    "python": ["Explain list vs tuple.", "What is a decorator?", "Explain the GIL.", "What is a generator?", "Explain *args and **kwargs."],
    "machine learning": ["What is overfitting?", "Explain gradient descent.", "What is cross-validation?", "Explain the bias-variance tradeoff.", "What is regularization?"],
    "data structures": ["Stack vs Queue?", "Explain hash tables.", "Binary search tree complexity?", "When to use linked list?", "Explain dynamic programming."],
    "javascript": ["var vs let vs const?", "What is closure?", "Explain promises.", "What is the event loop?", "Explain async/await."],
    "system design": ["How to design a URL shortener?", "Explain load balancing.", "What is CAP theorem?", "How does caching work?", "Explain microservices."],
    "general": ["Tell me about yourself.", "Your greatest strength?", "Where in 5 years?", "Describe a challenge you overcame.", "Why should we hire you?"],
}


def call_groq(system_prompt, user_prompt, max_tokens=400):
    headers = {"Authorization": f"Bearer {Config.GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": Config.GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        r = requests.post(Config.GROQ_URL, headers=headers, json=body, timeout=15)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM_ERROR:{e}]"
