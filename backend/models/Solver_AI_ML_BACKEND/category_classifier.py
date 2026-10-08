"""Inference wrapper for the category classifier.

Expected project folder:
    dataset.csv
    category calibrated svm.py
    category classifier.joblib
    category classifier.py

All paths are resolved relative to this file, so the whole project folder can
be moved or renamed without breaking the model path.
"""

from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "category_classifier.joblib" if (BASE_DIR / "category_classifier.joblib").exists() else BASE_DIR / "category classifier.joblib"

_model = None


def load_model():
    """Load the trained category model from the same folder as this script."""
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}\n"
                'Keep "category classifier.joblib" in the same folder as '
                '"category classifier.py".'
            )
        _model = joblib.load(MODEL_PATH)

    return _model


def predict_category(complaint_text: str) -> str:
    """Return only the predicted complaint category."""
    complaint_text = complaint_text.strip()
    if not complaint_text:
        raise ValueError("Complaint text cannot be empty.")

    model = load_model()
    return str(model.predict([complaint_text])[0])


def predict_category_with_confidence(complaint_text: str) -> dict:
    """Return the predicted category and calibrated confidence score."""
    complaint_text = complaint_text.strip()
    if not complaint_text:
        raise ValueError("Complaint text cannot be empty.")

    model = load_model()
    probabilities = model.predict_proba([complaint_text])[0]
    classes = model.classes_
    best_index = probabilities.argmax()

    return {
        "category": str(classes[best_index]),
        "confidence": float(probabilities[best_index]),
    }


if __name__ == "__main__":
    complaint = input("Enter complaint: ").strip()
    result = predict_category_with_confidence(complaint)

    print(f"Predicted Category: {result['category']}")
    print(f"Confidence: {result['confidence']:.2%}")
