"""Trains the 4 models used by ml_pipeline.py on a synthetic template dataset.
Run:  python -m backend.models.Solver_AI_ML_BACKEND.train_models
Replace generate_dataset() with a real CSV later; the saved filenames/columns stay the same.
"""
import random
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.svm import LinearSVC

OUT = Path(__file__).resolve().parent
R = random.Random(42)

ISSUES = {
    "Hostel": ["the water supply in the hostel block is not working", "my hostel room fan and light are broken",
               "the warden is not responding to room allotment requests", "hostel washrooms are dirty and the geyser is not working",
               "the hostel wifi is down in our wing", "bed and mattress in my hostel room are damaged",
               "there is no hot water in the hostel", "the hostel gate timings are unfair and rooms are overcrowded"],
    "Academic": ["the professor has not uploaded marks for the internal exam", "the timetable clashes for two subjects this semester",
                 "the syllabus was not completed before the exams", "attendance was wrongly marked absent in the class",
                 "the lab assignment evaluation is unfair and delayed", "course registration portal is not letting me enroll in the elective",
                 "the exam result has a wrong grade", "lectures are being cancelled repeatedly without replacement"],
    "Infrastructure": ["the projector in the classroom is not working", "the library air conditioning is broken",
                       "there is a big pothole and broken road near the main gate", "the lift in the academic block is stuck",
                       "the ceiling in the corridor is leaking and cracked", "streetlights near the parking are not working",
                       "the sparking electrical socket in the lab is dangerous", "benches in the lecture hall are broken"],
    "Mess": ["the food served in the mess was stale and undercooked", "found insects in the dinner at the mess",
             "the mess breakfast quality is very poor", "the drinking water at the mess tastes bad and dirty",
             "mess staff are rude and the food portions are small", "the dining hall utensils are not clean",
             "the mess menu is never followed and there is no variety", "rice and dal were raw and several students felt sick after eating"],
    "Harassment": ["a senior is ragging and threatening freshers", "I am being harassed and stalked by a student",
                   "a faculty member made inappropriate comments and I feel unsafe", "there is bullying and verbal abuse in our hostel",
                   "someone is sending threatening and abusive messages to me", "I faced discrimination and misbehaviour from a staff member",
                   "a group of students physically assaulted my friend", "I am being blackmailed and mentally harassed"],
    "Other": ["the campus bus timing is not convenient", "I lost my id card and need a replacement",
              "the stationery shop charges more than the printed price", "the fee payment receipt is not generated",
              "need a bonafide certificate from the office", "the sports ground booking process is confusing",
              "the canteen closing time should be extended", "suggestion to organise more cultural events on campus"],
}
DURATIONS = {  # label -> phrases
    "Not specified": [""],
    "Less than a day": ["since this morning", "since today", "for the last few hours", "since last night"],
    "1-3 days": ["since yesterday", "for 2 days", "for the past 3 days", "since two days"],
    "4-7 days": ["for 5 days", "for almost a week", "since 4 days", "for the past 6 days"],
    "More than a week": ["for more than a week", "for 2 weeks", "since last month", "for many weeks now"],
}
AFFECTED = {
    "Individual": ["I am", "only my room is", "it affects only me and", "personally I am"],
    "Small group": ["me and my roommates are", "around 5 students are", "our whole lab group is", "a few of us are"],
    "Large group": ["the entire hostel block is", "hundreds of students are", "all students of the campus are", "more than 100 students are"],
}
SUFFIX = ["Please look into it.", "Kindly resolve this soon.", "Request immediate action.", "", "This is a big problem."]
URGENT_WORDS = ["fire", "sparks", "shock", "injured", "unsafe", "sick", "threat", "assault", "blackmail", "danger"]


def urgency_label(cat, dur, aff, text):
    s = 0
    s += 2 if cat == "Harassment" else 0
    s += 4 if any(w in text for w in URGENT_WORDS) else 0
    s += {"Not specified": 0, "Less than a day": 0, "1-3 days": 1, "4-7 days": 2, "More than a week": 3}[dur]
    s += {"Individual": 0, "Small group": 1, "Large group": 2}[aff]
    s -= 2 if cat == "Other" else 0
    return "High" if s >= 4 else "Medium" if s >= 2 else "Low"


def generate_dataset(n=6000):
    rows = []
    for _ in range(n):
        cat = R.choice(list(ISSUES))
        issue = R.choice(ISSUES[cat])
        dur = R.choice(list(DURATIONS))
        aff = R.choice(list(AFFECTED))
        d = R.choice(DURATIONS[dur])
        who = R.choice(AFFECTED[aff])
        style = R.randint(0, 2)
        if style == 0:
            text = f"{issue} {d}. {R.choice(SUFFIX)}"
        elif style == 1:
            text = f"{who} facing a problem: {issue} {d}. {R.choice(SUFFIX)}"
        else:
            text = f"{R.choice(SUFFIX)} {issue} {d}, {who} affected."
        text = " ".join(text.split())
        rows.append({"complaint_text": text, "category": cat, "duration_normalized": dur, "affected_count": aff,
                     "urgency": urgency_label(cat, dur, aff, text)})
    return pd.DataFrame(rows)


def text_model(clf):
    return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)), ("clf", clf)])


def svm():
    return CalibratedClassifierCV(LinearSVC(), cv=3)


def main():
    df = generate_dataset()
    X = df["complaint_text"]
    for col, fname in [("category", "category_classifier"), ("duration_normalized", "duration_extractor"),
                       ("affected_count", "affected_count_extractor")]:
        m = text_model(svm())
        acc = cross_val_score(m, X, df[col], cv=3).mean()
        m.fit(X, df[col])
        joblib.dump(m, OUT / f"{fname}.joblib")
        print(f"{fname}: cv acc {acc:.3f}")
    cols = ["complaint_text", "category", "duration_normalized", "affected_count"]
    pre = ColumnTransformer([("t", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), "complaint_text"),
                             ("c", OneHotEncoder(handle_unknown="ignore"), cols[1:])])
    u = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000, C=10))])
    acc = cross_val_score(u, df[cols], df["urgency"], cv=3).mean()
    u.fit(df[cols], df["urgency"])
    joblib.dump(u, OUT / "urgency_classifier.joblib")
    print(f"urgency_classifier: cv acc {acc:.3f}")


if __name__ == "__main__":
    main()
