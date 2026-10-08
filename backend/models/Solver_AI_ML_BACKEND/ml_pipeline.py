"""Final complaint-only ML pipeline.

PUBLIC INPUT:
    complaint_text

The student enters nothing else.

Internal flow:
    complaint text
        -> category classifier
        -> duration extractor
        -> affected-count extractor
        -> urgency classifier

Keep this file beside the four .joblib files:
    category classifier.joblib
    duration extractor.joblib
    affected count extractor.joblib
    urgency classifier.joblib
"""

from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

def _resolve_model_path(space_name: str, underscore_name: str) -> Path:
    p_under = BASE_DIR / underscore_name
    if p_under.exists():
        return p_under
    return BASE_DIR / space_name

CATEGORY_MODEL_PATH = _resolve_model_path("category classifier.joblib", "category_classifier.joblib")
DURATION_MODEL_PATH = _resolve_model_path("duration extractor.joblib", "duration_extractor.joblib")
AFFECTED_MODEL_PATH = _resolve_model_path("affected count extractor.joblib", "affected_count_extractor.joblib")
URGENCY_MODEL_PATH = _resolve_model_path("urgency classifier.joblib", "urgency_classifier.joblib")

_category_model = None
_duration_model = None
_affected_model = None
_urgency_model = None


def load_models():
    global _category_model
    global _duration_model
    global _affected_model
    global _urgency_model

    if _category_model is None:
        _category_model = joblib.load(CATEGORY_MODEL_PATH)

    if _duration_model is None:
        _duration_model = joblib.load(DURATION_MODEL_PATH)

    if _affected_model is None:
        _affected_model = joblib.load(AFFECTED_MODEL_PATH)

    if _urgency_model is None:
        _urgency_model = joblib.load(URGENCY_MODEL_PATH)
        if hasattr(_urgency_model, "steps"):
            for _, step in _urgency_model.steps:
                if hasattr(step, "predict_proba") and not hasattr(step, "multi_class"):
                    step.multi_class = "auto"

    return (
        _category_model,
        _duration_model,
        _affected_model,
        _urgency_model,
    )


def _predict_text_model(model, complaint_text: str) -> dict:
    probabilities = model.predict_proba([complaint_text])[0]
    classes = model.classes_
    best_index = probabilities.argmax()

    return {
        "value": str(classes[best_index]),
        "confidence": float(probabilities[best_index]),
    }


def analyze_complaint(complaint_text: str) -> dict:
    """Analyze one complaint using complaint text as the ONLY input."""

    complaint_text = complaint_text.strip()

    if not complaint_text:
        raise ValueError("Complaint text cannot be empty.")

    (
        category_model,
        duration_model,
        affected_model,
        urgency_model,
    ) = load_models()

    # Model 1: category
    category_result = _predict_text_model(
        category_model,
        complaint_text,
    )

    # Internal context extraction
    duration_result = _predict_text_model(
        duration_model,
        complaint_text,
    )

    affected_result = _predict_text_model(
        affected_model,
        complaint_text,
    )

    # Model 2: urgency
    urgency_input = pd.DataFrame(
        [
            {
                "complaint_text": complaint_text,
                "category": category_result["value"],
                "duration_normalized": duration_result["value"],
                "affected_count": affected_result["value"],
            }
        ]
    )

    urgency_probabilities = urgency_model.predict_proba(
        urgency_input
    )[0]

    urgency_classes = urgency_model.classes_
    urgency_index = urgency_probabilities.argmax()

    return {
        "category": category_result["value"],
        "category_confidence": category_result["confidence"],

        "duration": duration_result["value"],
        "duration_confidence": duration_result["confidence"],

        "affected_count": affected_result["value"],
        "affected_count_confidence": affected_result["confidence"],

        "urgency": str(urgency_classes[urgency_index]),
        "urgency_confidence": float(
            urgency_probabilities[urgency_index]
        ),
    }


if __name__ == "__main__":
    complaint = input("Enter complaint: ").strip()

    result = analyze_complaint(complaint)

    print("\n=== Automated Complaint Analysis ===")
    print(f"Category: {result['category']}")
    print(
        f"Category confidence: "
        f"{result['category_confidence']:.2%}"
    )
    print(f"Duration: {result['duration']}")
    print(
        f"Duration confidence: "
        f"{result['duration_confidence']:.2%}"
    )
    print(f"Affected Count: {result['affected_count']}")
    print(
        f"Affected confidence: "
        f"{result['affected_count_confidence']:.2%}"
    )
    print(f"Urgency: {result['urgency']}")
    print(
        f"Urgency confidence: "
        f"{result['urgency_confidence']:.2%}"
    )
