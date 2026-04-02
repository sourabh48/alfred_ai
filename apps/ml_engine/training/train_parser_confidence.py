from __future__ import annotations

import os

import joblib

from apps.ml_engine.inference_adapters.parser_confidence_calibrator import MODEL_PATH, ParserConfidenceCalibrator
from apps.ml_engine.models import DocumentParserLearningMemory
from .simple_models import accuracy_score, fit_binary_logistic_regression, random_train_test_split


def train_parser_confidence_model() -> dict:
    memories = list(DocumentParserLearningMemory.objects.all())
    sample_count = len(memories)
    if sample_count < 12:
        return _skip("Need at least 12 parser-learning memory rows before parser-confidence calibration is useful.", sample_count=sample_count)

    rows = [_memory_row(item) for item in memories]
    labels = [_memory_label(item) for item in memories]
    if len(set(labels)) < 2:
        return _skip("Parser-learning memory does not yet contain enough success/failure spread for calibration.", sample_count=sample_count)

    feature_names = ParserConfidenceCalibrator.FEATURE_NAMES
    X = [[row[name] for name in feature_names] for row in rows]
    y = labels

    test_size = 0.25 if sample_count >= 20 else 0.2
    X_train, X_test, y_train, y_test = random_train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )
    model = fit_binary_logistic_regression(X_train, y_train, iterations=1500, learning_rate=0.08)

    predictions = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))
    quality_score = round(max(0.0, min(100.0, accuracy * 100.0)), 2)
    coverage_score = min(100.0, (sample_count / 60.0) * 100.0)
    confidence_estimate = round(max(20.0, (quality_score * 0.65) + (coverage_score * 0.35)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_names": feature_names}, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": quality_score,
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Parser-confidence calibrator trained on {sample_count} parser-memory rows with holdout accuracy {accuracy:.2f}.",
    }


def _memory_row(item: DocumentParserLearningMemory) -> dict:
    return {
        "successful_count": float(item.successful_count),
        "review_count": float(item.review_count),
        "failed_count": float(item.failed_count),
        "correction_count": float(item.correction_count),
        "retry_success_count": float(item.retry_success_count),
        "retry_failure_count": float(item.retry_failure_count),
        "average_confidence": float(item.average_confidence or 0),
        "observed_fields_count": float(len(item.observed_fields or [])),
        "observed_keywords_count": float(len(item.observed_keywords or [])),
        "accepted_field_hints_count": float(len(item.accepted_field_hints or [])),
        "scope_hash": float(sum(ord(char) for char in (item.scope or "")) % 997),
        "extension_hash": float(sum(ord(char) for char in (item.file_extension or "")) % 97),
    }


def _memory_label(item: DocumentParserLearningMemory) -> int:
    success_weight = item.successful_count + item.retry_success_count + item.correction_count
    failure_weight = item.failed_count + item.retry_failure_count + item.review_count
    return 1 if success_weight >= max(failure_weight, 1) else 0


def _skip(message: str, *, sample_count: int = 0, details: str = "") -> dict:
    note = message if not details else f"{message} {details}"
    return {
        "status": "skipped",
        "sample_count": sample_count,
        "quality_score": 0.0,
        "confidence_estimate": 0.0,
        "artifact_path": "",
        "notes": note.strip(),
    }
