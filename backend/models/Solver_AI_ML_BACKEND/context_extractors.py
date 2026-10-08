"""Internal context extraction from complaint text.

The student does NOT enter duration or affected count.
Both are predicted automatically from complaint_text.

Keep this file beside:
    duration extractor.joblib
    affected count extractor.joblib
"""

from pathlib import Path
import joblib


BASE_DIR = Path(__file__).resolve().parent

DURATION_MODEL_PATH = BASE_DIR / "duration_extractor.joblib" if (BASE_DIR / "duration_extractor.joblib").exists() else BASE_DIR / "duration extractor.joblib"
AFFECTED_MODEL_PATH = BASE_DIR / "affected_count_extractor.joblib" if (BASE_DIR / "affected_count_extractor.joblib").exists() else BASE_DIR / "affected count extractor.joblib"

_duration_model = None
_affected_model = None


def load_extractors():
    global _duration_model, _affected_model

    if _duration_model is None:
        _duration_model = joblib.load(DURATION_MODEL_PATH)

    if _affected_model is None:
        _affected_model = joblib.load(AFFECTED_MODEL_PATH)

    return _duration_model, _affected_model


def _predict_with_confidence(model, complaint_text: str) -> dict:
    probabilities = model.predict_proba([complaint_text])[0]
    classes = model.classes_
    best_index = probabilities.argmax()

    return {
        "value": str(classes[best_index]),
        "confidence": float(probabilities[best_index]),
    }


def extract_context(complaint_text: str) -> dict:
    complaint_text = complaint_text.strip()

    if not complaint_text:
        raise ValueError("Complaint text cannot be empty.")

    duration_model, affected_model = load_extractors()

    duration = _predict_with_confidence(
        duration_model,
        complaint_text,
    )

    affected = _predict_with_confidence(
        affected_model,
        complaint_text,
    )

    return {
        "duration": duration["value"],
        "duration_confidence": duration["confidence"],
        "affected_count": affected["value"],
        "affected_count_confidence": affected["confidence"],
    }


if __name__ == "__main__":
    complaint = input("Complaint: ").strip()
    print(extract_context(complaint))
