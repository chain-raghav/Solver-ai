"""AI Service Module
Encapsulates Model 1 (Category Classification) & Model 2 (Urgency Detection),
along with duration and affected count context extractors.
"""

import logging
from backend.models.Solver_AI_ML_BACKEND.ml_pipeline import analyze_complaint

logger = logging.getLogger("ai_service")


def predict_complaint_attributes(complaint_text: str) -> dict:
    """Analyze a complaint text and return predicted category, urgency, duration,

    and affected count along with confidence scores.
    """
    clean_text = (complaint_text or "").strip()
    if not clean_text:
        return {
            "category": "Other",
            "category_confidence": 0.50,
            "urgency": "Low",
            "urgency_confidence": 0.50,
            "duration": "Not specified",
            "duration_confidence": 0.50,
            "affected_count": "Individual",
            "affected_count_confidence": 0.50,
        }

    try:
        raw_result = analyze_complaint(clean_text)
        return {
            "category": raw_result.get("category", "Other"),
            "category_confidence": round(float(raw_result.get("category_confidence", 0.75)), 4),
            "urgency": raw_result.get("urgency", "Medium"),
            "urgency_confidence": round(float(raw_result.get("urgency_confidence", 0.75)), 4),
            "duration": raw_result.get("duration", "Not specified"),
            "duration_confidence": round(float(raw_result.get("duration_confidence", 0.50)), 4),
            "affected_count": raw_result.get("affected_count", "Individual"),
            "affected_count_confidence": round(float(raw_result.get("affected_count_confidence", 0.50)), 4),
        }
    except Exception as e:
        logger.error(f"Error during AI complaint analysis: {e}")
        # Graceful fallback
        return {
            "category": "Other",
            "category_confidence": 0.60,
            "urgency": "Medium",
            "urgency_confidence": 0.60,
            "duration": "Not specified",
            "duration_confidence": 0.50,
            "affected_count": "Individual",
            "affected_count_confidence": 0.50,
        }
