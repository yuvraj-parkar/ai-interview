import cv2
import numpy as np
import base64
from deepface import DeepFace


def decode_image(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)


def get_confidence_score(dominant_emotion, scores):
    confidence_map = {
        "happy": 85, "neutral": 65, "surprise": 60,
        "fear": 30, "sad": 35, "angry": 40, "disgust": 25,
    }
    base_score = confidence_map.get(dominant_emotion, 50)
    if scores.get("happy", 0) > 70:
        base_score = min(100, base_score + 10)
    return base_score


def analyze_emotion(base64_image):
    try:
        img = decode_image(base64_image)
        result = DeepFace.analyze(
            img_path=img,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
        )
        face_data = result[0] if isinstance(result, list) else result
        emotion_scores = {k: round(v, 1) for k, v in face_data.get("emotion", {}).items()}
        dominant_emotion = face_data.get("dominant_emotion", "neutral")
        return {
            "success": True,
            "dominant_emotion": dominant_emotion,
            "scores": emotion_scores,
            "confidence_score": get_confidence_score(dominant_emotion, emotion_scores),
        }
    except Exception as e:
        return {
            "success": False,
            "dominant_emotion": "neutral",
            "scores": {},
            "confidence_score": 50,
            "error": str(e),
        }
