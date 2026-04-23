"""
nlp_analyzer.py  — NO SPACY VERSION
Analyzes interview answers using TextBlob + pure Python.
No spaCy needed! Works on Python 3.13.
"""

from textblob import TextBlob
import re

TECH_KEYWORDS = {
    "python","java","javascript","machine learning","deep learning","neural network",
    "database","sql","api","framework","algorithm","data structure","cloud","docker",
    "git","agile","software","development","testing","debugging","optimization"
}
SOFT_SKILL_KEYWORDS = {
    "team","leadership","communication","problem","solution","challenge","manage",
    "collaborate","responsible","initiative","creative","deadline","priority",
    "conflict","mentor"
}
FILLER_WORDS = ["um","uh","you know","basically","literally","actually",
                "honestly","sort of","kind of"]


def analyze_answer(answer_text: str, question: str = "") -> dict:
    if not answer_text or len(answer_text.strip()) < 5:
        return _empty_result("Answer is too short.")

    text       = answer_text.strip()
    lower_text = text.lower()
    blob       = TextBlob(text)

    # Word & sentence counts using pure Python
    words          = [w for w in re.findall(r'\b\w+\b', text)]
    word_count     = len(words)
    sentences      = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_count = max(len(sentences), 1)
    avg_words_per_s= word_count / sentence_count
    unique_words   = len(set(w.lower() for w in words))
    vocabulary_ratio = unique_words / max(word_count, 1)

    # Keyword hits
    tech_hits    = sum(1 for kw in TECH_KEYWORDS if kw in lower_text)
    soft_hits    = sum(1 for kw in SOFT_SKILL_KEYWORDS if kw in lower_text)
    filler_count = sum(lower_text.count(fw) for fw in FILLER_WORDS)

    # Sentiment via TextBlob
    polarity     = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    # Scores
    length_score    = _score_length(word_count)
    clarity_score   = _score_clarity(avg_words_per_s, filler_count, word_count)
    relevance_score = _score_relevance(tech_hits, soft_hits)
    confidence_score= _score_confidence(polarity, subjectivity)
    vocabulary_score= _score_vocabulary(vocabulary_ratio, unique_words)
    structure_score = _score_structure(sentence_count, word_count)

    overall = int(
        length_score     * 0.15 +
        clarity_score    * 0.25 +
        relevance_score  * 0.25 +
        confidence_score * 0.15 +
        vocabulary_score * 0.10 +
        structure_score  * 0.10
    )

    feedback = _generate_feedback(
        word_count, filler_count, tech_hits, soft_hits,
        polarity, sentence_count, vocabulary_ratio
    )

    return {
        "success":       True,
        "overall_score": overall,
        "grade":         _grade(overall),
        "scores": {
            "length":     length_score,
            "clarity":    clarity_score,
            "relevance":  relevance_score,
            "confidence": confidence_score,
            "vocabulary": vocabulary_score,
            "structure":  structure_score
        },
        "stats": {
            "word_count":     word_count,
            "sentence_count": sentence_count,
            "unique_words":   unique_words,
            "filler_words":   filler_count,
            "tech_keywords":  tech_hits,
            "soft_keywords":  soft_hits,
            "entities_found": 0,
            "sentiment":      round(polarity, 2)
        },
        "feedback": feedback
    }


def _score_length(wc):
    if wc < 20:   return 20
    if wc < 50:   return 45
    if wc < 80:   return 65
    if wc <= 200: return 100
    if wc <= 300: return 85
    return 60

def _score_clarity(avg, fillers, total):
    score = 100
    if avg > 30: score -= 20
    if avg < 5:  score -= 15
    score -= int((fillers / max(total, 1)) * 200)
    return max(0, min(100, score))

def _score_relevance(tech, soft):
    total = tech + soft
    if total == 0:  return 30
    if total <= 2:  return 55
    if total <= 5:  return 75
    if total <= 8:  return 90
    return 100

def _score_confidence(polarity, subjectivity):
    score = 60 + int(polarity * 30) - int(subjectivity * 15)
    return max(0, min(100, score))

def _score_vocabulary(ratio, unique):
    if unique < 10:  return 30
    if ratio > 0.7:  return 95
    if ratio > 0.5:  return 80
    if ratio > 0.35: return 65
    return 50

def _score_structure(sentences, words):
    if sentences < 2:   return 40
    if sentences <= 6:  return 90
    if sentences <= 10: return 75
    return 60

def _generate_feedback(wc, fillers, tech, soft, polarity, sentences, vocab_ratio):
    tips = []
    if wc < 50:
        tips.append("📝 Expand your answer — aim for at least 80 words with examples.")
    elif wc > 300:
        tips.append("✂️ Too long. Be more concise and focused.")
    else:
        tips.append("✅ Good answer length!")
    if fillers > 3:
        tips.append(f"🚫 Reduce filler words (um, uh, like). Found ~{fillers} instances.")
    else:
        tips.append("✅ Low use of filler words — sounds professional!")
    if tech + soft < 2:
        tips.append("🎯 Use more topic-specific keywords in your answer.")
    elif tech > 3:
        tips.append("💡 Great use of technical keywords!")
    if polarity < 0:
        tips.append("😊 Use more positive language to sound confident.")
    elif polarity > 0.3:
        tips.append("✅ Positive and confident tone!")
    if sentences < 2:
        tips.append("📋 Structure your answer in 2–4 clear sentences.")
    elif 2 <= sentences <= 5:
        tips.append("✅ Well-structured response.")
    if vocab_ratio < 0.35:
        tips.append("📚 Try using more varied vocabulary.")
    return tips

def _grade(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"

def _empty_result(msg):
    return {"success": False, "overall_score": 0, "grade": "F",
            "scores": {}, "stats": {}, "feedback": [msg]}
