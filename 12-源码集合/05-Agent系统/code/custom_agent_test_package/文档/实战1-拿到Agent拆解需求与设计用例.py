def score_emotion_recognition(self, output: str) -> float:
    """评估情绪识别能力"""
    empathy_keywords = ["抱歉", "理解", "抱歉", "升级", "转人工"]
    matched = sum(1 for kw in empathy_keywords if kw in output)
    return min(matched / len(empathy_keywords), 1.0)
