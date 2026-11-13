import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


MODEL_PATH = Path(__file__).resolve().parent / "data" / "complaint_classifier.joblib"

SYNTHETIC_TRAINING_DATA = [
    ("ROAD_DAMAGE", "Large pothole on main road near school making it unsafe for children and cyclists."),
    ("ROAD_DAMAGE", "Cracked asphalt on busy highway lane causing traffic jams and vehicle damage."),
    ("ROAD_DAMAGE", "Road surface broken near bus stop, vehicles bumping heavily during rain."),
    ("GARBAGE", "Garbage dumped near market square creating foul smell and attracting stray dogs."),
    ("GARBAGE", "Overflowing bins outside residential blocks and litter spread across pavement."),
    ("GARBAGE", "Uncollected waste in public park causing sanitation concerns after festival."),
    ("WATER_LEAKAGE", "Water pipe burst near apartment complex causing flooding and property damage."),
    ("WATER_LEAKAGE", "Leakage from underground water tank is wasting potable water and wetting road."),
    ("WATER_LEAKAGE", "Continuous water leak from street line creating puddles and possible contamination."),
    ("STREETLIGHT", "Streetlamp is not working near intersection and pedestrians feel unsafe at night."),
    ("STREETLIGHT", "Broken street light on residential street has been dark for several days."),
    ("STREETLIGHT", "Power outage in public lighting near bus stop leaving the area unsafe."),
    ("DRAINAGE", "Blocked drain overflowing on road and causing traffic disruption after rain."),
    ("DRAINAGE", "Open drain clogged with plastic and garbage causing sewage backup."),
    ("DRAINAGE", "Sewage water stagnant in neighborhood drain after heavy rainfall."),
    ("OTHER", "Damaged public bench at park entrance needs replacement."),
    ("OTHER", "Broken signboard near community center needs maintenance."),
    ("OTHER", "Public safety concern with fallen tree branch blocking path."),
]


class ComplaintClassifier:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.pipeline = None
        self.label_map = [
            "ROAD_DAMAGE",
            "GARBAGE",
            "WATER_LEAKAGE",
            "STREETLIGHT",
            "DRAINAGE",
            "OTHER",
        ]

    def train(self):
        labels = [category for category, _ in SYNTHETIC_TRAINING_DATA]
        texts = [description for _, description in SYNTHETIC_TRAINING_DATA]
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.25, random_state=42
        )

        model = Pipeline(
            steps=[
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "precision": round(float(precision_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=self.label_map).tolist(),
        }

        self.pipeline = model
        joblib.dump({"model": model, "metrics": metrics, "labels": self.label_map}, self.model_path)
        return metrics

    def load(self):
        if self.model_path.exists():
            payload = joblib.load(self.model_path)
            self.pipeline = payload["model"]
            return payload
        return None

    def ensure_trained(self):
        if self.pipeline is None:
            payload = self.load()
            if payload is None:
                self.train()
                payload = self.load()
            self.pipeline = payload["model"]
        return self.pipeline

    def predict(self, text):
        model = self.ensure_trained()
        prediction = model.predict([text])[0]
        probabilities = model.predict_proba([text])[0]
        confidence = float(np.max(probabilities))
        return {
            "category": prediction,
            "confidence": round(confidence, 4),
            "needs_human_review": confidence < 0.65,
        }

    def explain_priority(self, text, category, similar_reports=0, risk_keywords=None):
        risk_keywords = risk_keywords or []
        keyword_score = 0
        if category in {"ROAD_DAMAGE", "DRAINAGE", "WATER_LEAKAGE"}:
            keyword_score += 1
        if any(word.lower() in text.lower() for word in ["flood", "unsafe", "breach", "overflow", "danger", "crack"]):
            keyword_score += 2
        if similar_reports > 3:
            keyword_score += 1
        if risk_keywords:
            keyword_score += min(len(risk_keywords), 2)

        if keyword_score >= 4:
            priority = "CRITICAL"
        elif keyword_score >= 2:
            priority = "HIGH"
        elif keyword_score >= 1:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        reasons = []
        if category in {"ROAD_DAMAGE", "DRAINAGE", "WATER_LEAKAGE"}:
            reasons.append("Infrastructure category is safety-sensitive.")
        if any(word.lower() in text.lower() for word in ["unsafe", "danger", "flood", "overflow", "break"]):
            reasons.append("Risk keywords indicate a potentially hazardous condition.")
        if similar_reports > 3:
            reasons.append("Multiple similar complaints increase urgency.")
        if not reasons:
            reasons.append("Issue is logged and will be reviewed by the civic operations team.")

        return {
            "predicted_priority": priority,
            "reasons": reasons,
            "requires_human_review": priority in {"HIGH", "CRITICAL"},
        }

    def find_similar_complaints(self, complaint_text, complaints):
        if not complaints:
            return []
        texts = [item["description"] for item in complaints if item.get("description")]
        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform([complaint_text, *texts])
        similarities = matrix[0].dot(matrix[1:].T).toarray().ravel()
        results = []
        for index, score in enumerate(similarities):
            if score > 0.15:
                results.append({
                    "complaint_id": complaints[index].get("id"),
                    "title": complaints[index].get("title"),
                    "score": round(float(score), 4),
                })
        return sorted(results, key=lambda item: item["score"], reverse=True)
