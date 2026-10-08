"""Inference wrapper for the urgency classifier.

Keep this file and "urgency classifier.joblib" in the same Solver AI folder.

Inputs:
    complaint_text
    category          -> normally predicted by Model 1
    duration
    affected_count

Output:
    Low / Medium / High + confidence
"""

from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "urgency_classifier.joblib" if (BASE_DIR / "urgency_classifier.joblib").exists() else BASE_DIR / "urgency classifier.joblib"

_model = None


def load_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}\n"
                'Keep "urgency classifier.joblib" in the same folder as '
                '"urgency classifier.py".'
            )

        _model = joblib.load(MODEL_PATH)
        if hasattr(_model, "steps"):
            for _, step in _model.steps:
                if hasattr(step, "predict_proba") and not hasattr(step, "multi_class"):
                    step.multi_class = "auto"

    return _model


def _prepare_input(
    complaint_text: str,
    category: str,
    duration: str = "Not specified",
    affected_count: str = "Not specified",
) -> pd.DataFrame:
    complaint_text = complaint_text.strip()
    category = category.strip()
    duration = duration.strip()
    affected_count = affected_count.strip()

    if not complaint_text:
        raise ValueError("Complaint text cannot be empty.")

    if not category:
        raise ValueError("Category cannot be empty.")

    if not duration:
        duration = "Not specified"

    if not affected_count:
        affected_count = "Not specified"

    return pd.DataFrame(
        [
            {
                "complaint_text": complaint_text,
                "category": category,
                "duration_normalized": duration,
                "affected_count": affected_count,
            }
        ]
    )


def predict_urgency(
    complaint_text: str,
    category: str,
    duration: str = "Not specified",
    affected_count: str = "Not specified",
) -> str:
    model = load_model()

    row = _prepare_input(
        complaint_text,
        category,
        duration,
        affected_count,
    )

    return str(model.predict(row)[0])


def predict_urgency_with_confidence(
    complaint_text: str,
    category: str,
    duration: str = "Not specified",
    affected_count: str = "Not specified",
) -> dict:
    model = load_model()

    row = _prepare_input(
        complaint_text,
        category,
        duration,
        affected_count,
    )

    probabilities = model.predict_proba(row)[0]
    classes = model.classes_
    best_index = probabilities.argmax()

    return {
        "urgency": str(classes[best_index]),
        "confidence": float(probabilities[best_index]),
        "probabilities": {
            str(label): float(probability)
            for label, probability in zip(classes, probabilities)
        },
    }


if __name__ == "__main__":
    complaint_text = input("Complaint: ").strip()
    category = input("Category: ").strip()
    duration = input(
        "Duration [Not specified]: "
    ).strip() or "Not specified"
    affected_count = input(
        "Affected count [Not specified]: "
    ).strip() or "Not specified"

    result = predict_urgency_with_confidence(
        complaint_text=complaint_text,
        category=category,
        duration=duration,
        affected_count=affected_count,
    )

    print(f"Predicted Urgency: {result['urgency']}")
    print(f"Confidence: {result['confidence']:.2%}")
