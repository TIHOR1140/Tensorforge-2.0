"""ML Model Training Pipeline for Multilingual Ticket Classification and Routing.

Trains:
1. Category Classifier (11 classes)
2. Secondary Category Classifier (11 classes + None)
3. Urgency Classifier (Binary)

Extracts n-gram TF-IDF representations suited for multilingual Latin/Sinhala/Tamil text
and trains calibrated models, exporting artifacts into ml/artifacts.
"""

import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, f1_score

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.models.preprocessor import TicketPreprocessor
from src.core.config import settings


def prepare_features(df: pd.DataFrame) -> list[str]:
    """Format and normalize tickets for feature extraction."""
    formatted = []
    for _, row in df.iterrows():
        channel = str(row.get("channel", "chat"))
        subject = str(row.get("subject", "")) if pd.notna(row.get("subject")) else ""
        text = str(row.get("text", "")) if pd.notna(row.get("text")) else ""
        formatted.append(TicketPreprocessor.format_ticket_input(channel, subject, text))
    return formatted


def train():
    print("=" * 60)
    print("TensorForge 2.0 - Starting Model Training Pipeline")
    print("=" * 60)

    train_path = settings.DATA_DIR / "raw" / "train.csv"
    val_path = settings.DATA_DIR / "raw" / "validation.csv"

    if not train_path.exists() or not val_path.exists():
        print(f"Error: Missing dataset at {train_path} or {val_path}")
        return

    print(f"Loading training data from {train_path}...")
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    print(f"Train samples: {len(train_df)}, Validation samples: {len(val_df)}")

    # 1. Prepare Text Features
    print("\n[1/4] Preprocessing and extracting multilingual text representations...")
    X_train_raw = prepare_features(train_df)
    X_val_raw = prepare_features(val_df)

    # Word and character n-grams to capture English, transliterated Sinhala/Tamil, and Unicode scripts
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=25000,
        sublinear_tf=True
    )
    X_train = vectorizer.fit_transform(X_train_raw)
    X_val = vectorizer.transform(X_val_raw)

    # 2. Train Primary Category Model
    print("\n[2/4] Training Primary Category Classifier (11 categories)...")
    y_cat_train = train_df["category"]
    y_cat_val = val_df["category"]

    cat_clf = LogisticRegression(C=2.5, max_iter=1000, class_weight="balanced")
    cat_model = CalibratedClassifierCV(estimator=cat_clf, cv=3)
    cat_model.fit(X_train, y_cat_train)

    val_cat_preds = cat_model.predict(X_val)
    cat_f1 = f1_score(y_cat_val, val_cat_preds, average="macro")
    print(f"Validation Primary Category Macro F1: {cat_f1:.4f}")

    # 3. Train Secondary Category Model
    print("\n[3/4] Training Secondary Category Classifier...")
    y_sec_train = train_df["secondary_category"].fillna("none")
    y_sec_val = val_df["secondary_category"].fillna("none")

    sec_clf = LogisticRegression(C=1.5, max_iter=1000, class_weight="balanced")
    sec_clf.fit(X_train, y_sec_train)
    val_sec_preds = sec_clf.predict(X_val)
    sec_f1 = f1_score(y_sec_val, val_sec_preds, average="macro")
    print(f"Validation Secondary Category Macro F1: {sec_f1:.4f}")

    # 4. Train Urgency Classifier
    print("\n[4/4] Training Urgency Flag Classifier (Binary)...")
    y_urg_train = train_df["is_urgent"].astype(bool)
    y_urg_val = val_df["is_urgent"].astype(bool)

    urg_clf = LogisticRegression(C=2.0, max_iter=1000, class_weight="balanced")
    urg_model = CalibratedClassifierCV(estimator=urg_clf, cv=3)
    urg_model.fit(X_train, y_urg_train)

    val_urg_preds = urg_model.predict(X_val)
    urg_f1 = f1_score(y_urg_val, val_urg_preds, average="binary")
    print(f"Validation Urgency Binary F1: {urg_f1:.4f}")

    # Export Artifacts
    artifacts_dir = settings.ARTIFACTS_DIR
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting model artifacts to {artifacts_dir}...")
    joblib.dump(vectorizer, artifacts_dir / "vectorizer.joblib")
    joblib.dump(cat_model, artifacts_dir / "category_model.joblib")
    joblib.dump(sec_clf, artifacts_dir / "secondary_model.joblib")
    joblib.dump(urg_model, artifacts_dir / "urgency_model.joblib")

    print("\nTraining completed successfully! Artifacts are ready for offline inference.")


if __name__ == "__main__":
    train()
