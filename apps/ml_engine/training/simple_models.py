from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np


def _standardize_features(X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    matrix = np.asarray(X, dtype=float)
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale <= 1e-8, 1.0, scale)
    normalized = (matrix - mean) / scale
    return normalized, mean, scale


@dataclass
class LinearRegressorModel:
    coefficients: np.ndarray
    intercept: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray

    def predict(self, X):
        matrix = np.asarray(X, dtype=float)
        normalized = (matrix - self.feature_mean) / self.feature_scale
        return normalized @ self.coefficients + self.intercept


@dataclass
class BinaryLogisticClassifierModel:
    weights: np.ndarray
    intercept: float
    feature_mean: np.ndarray
    feature_scale: np.ndarray

    def _logits(self, X) -> np.ndarray:
        matrix = np.asarray(X, dtype=float)
        normalized = (matrix - self.feature_mean) / self.feature_scale
        return normalized @ self.weights + self.intercept

    def predict_proba(self, X):
        logits = np.clip(self._logits(X), -40.0, 40.0)
        positive = 1.0 / (1.0 + np.exp(-logits))
        return np.column_stack([1.0 - positive, positive])

    def predict(self, X):
        probabilities = self.predict_proba(X)
        return (probabilities[:, 1] >= 0.5).astype(int)


@lru_cache(maxsize=1)
def _sklearn_backends():
    try:
        from sklearn.linear_model import LogisticRegression, Ridge
    except Exception:
        return None, None
    return Ridge, LogisticRegression


def fit_linear_regression(X, y, *, ridge: float = 1e-4) -> LinearRegressorModel:
    normalized, feature_mean, feature_scale = _standardize_features(X)
    targets = np.asarray(y, dtype=float)
    ridge_backend, _ = _sklearn_backends()
    if ridge_backend is not None:
        estimator = ridge_backend(alpha=max(float(ridge), 1e-6), fit_intercept=True)
        estimator.fit(normalized, targets)
        return LinearRegressorModel(
            coefficients=np.asarray(estimator.coef_, dtype=float),
            intercept=float(estimator.intercept_),
            feature_mean=feature_mean,
            feature_scale=feature_scale,
        )

    design = np.column_stack([np.ones(len(normalized)), normalized])
    regularizer = np.eye(design.shape[1], dtype=float) * ridge
    regularizer[0, 0] = 0.0
    solution = np.linalg.pinv(design.T @ design + regularizer) @ design.T @ targets
    return LinearRegressorModel(
        coefficients=solution[1:],
        intercept=float(solution[0]),
        feature_mean=feature_mean,
        feature_scale=feature_scale,
    )


def fit_binary_logistic_regression(
    X,
    y,
    *,
    iterations: int = 1200,
    learning_rate: float = 0.08,
    l2: float = 1e-4,
) -> BinaryLogisticClassifierModel:
    normalized, feature_mean, feature_scale = _standardize_features(X)
    labels = np.asarray(y, dtype=float)
    _, logistic_backend = _sklearn_backends()
    if logistic_backend is not None:
        estimator = logistic_backend(
            max_iter=max(int(iterations), 300),
            solver="lbfgs",
            C=max(1e-6, 1.0 / max(float(l2), 1e-6)),
        )
        estimator.fit(normalized, labels.astype(int))
        return BinaryLogisticClassifierModel(
            weights=np.asarray(estimator.coef_[0], dtype=float),
            intercept=float(estimator.intercept_[0]),
            feature_mean=feature_mean,
            feature_scale=feature_scale,
        )

    weights = np.zeros(normalized.shape[1], dtype=float)
    intercept = 0.0

    for _ in range(int(iterations)):
        logits = np.clip(normalized @ weights + intercept, -40.0, 40.0)
        predictions = 1.0 / (1.0 + np.exp(-logits))
        error = predictions - labels
        grad_w = (normalized.T @ error) / len(normalized) + (l2 * weights)
        grad_b = float(error.mean())
        weights -= learning_rate * grad_w
        intercept -= learning_rate * grad_b

    return BinaryLogisticClassifierModel(
        weights=weights,
        intercept=float(intercept),
        feature_mean=feature_mean,
        feature_scale=feature_scale,
    )


def random_train_test_split(X, y, *, test_size: float = 0.25, random_state: int = 42, stratify=None):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    if len(X) != len(y):
        raise ValueError("X and y must have the same length.")
    if len(X) < 2:
        raise ValueError("Need at least two samples to split.")

    rng = np.random.default_rng(random_state)
    test_count = min(max(1, int(round(len(X) * test_size))), len(X) - 1)

    if stratify is None:
        indices = np.arange(len(X))
        rng.shuffle(indices)
        test_indices = indices[:test_count]
        train_indices = indices[test_count:]
    else:
        labels = np.asarray(stratify)
        train_indices = []
        test_indices = []
        for value in np.unique(labels):
            value_indices = np.flatnonzero(labels == value)
            rng.shuffle(value_indices)
            value_test_count = min(max(1, int(round(len(value_indices) * test_size))), max(len(value_indices) - 1, 1))
            test_indices.extend(value_indices[:value_test_count])
            train_indices.extend(value_indices[value_test_count:])
        train_indices = np.asarray(train_indices, dtype=int)
        test_indices = np.asarray(test_indices, dtype=int)
        if not len(train_indices) or not len(test_indices):
            raise ValueError("Stratified split could not produce both train and test sets.")

    return X[train_indices], X[test_indices], y[train_indices], y[test_indices]


def accuracy_score(y_true, y_pred) -> float:
    truth = np.asarray(y_true)
    predicted = np.asarray(y_pred)
    if not len(truth):
        return 0.0
    return float((truth == predicted).mean())


def mean_absolute_error(y_true, y_pred) -> float:
    truth = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if not len(truth):
        return 0.0
    return float(np.mean(np.abs(truth - predicted)))


def mean_absolute_percentage_error(y_true, y_pred) -> float:
    truth = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if not len(truth):
        return 1.0
    denominator = np.maximum(np.abs(truth), 1.0)
    return float(np.mean(np.abs(truth - predicted) / denominator))
