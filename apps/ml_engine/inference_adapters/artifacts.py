"""Serve only the exact artifact recorded training evidence names; model files are data, never pickles."""

from dataclasses import fields
from datetime import datetime
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
import tempfile

from django.conf import settings
import numpy as np

from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.quality import resolve_artifact_path
from apps.ml_engine.training.simple_models import BinaryLogisticClassifierModel, LinearRegressorModel


ARTIFACT_FORMAT = "alfred-model-json-v1"
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MODEL_KINDS = {"linear_regressor": LinearRegressorModel, "binary_logistic": BinaryLogisticClassifierModel}


def dump_artifact(payload, path):
    """Replace atomically, so a crash or a reader never sees a partial model."""
    model = payload["model"]
    kind = next(name for name, kind_type in MODEL_KINDS.items() if type(model) is kind_type)
    values = {field.name: np.asarray(getattr(model, field.name), dtype=float).tolist() for field in fields(model)}
    text = json.dumps(payload | {"format": ARTIFACT_FORMAT, "model": {"kind": kind, **values}}, allow_nan=False)
    target = resolve_artifact_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".model-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _reject_constant(name):
    raise ValueError(f"Non-finite model value: {name}")


def _parse_artifact(raw):
    payload = json.loads(raw, parse_constant=_reject_constant)
    names = payload["feature_names"]
    document = payload["model"]
    kind_type = MODEL_KINDS[document["kind"]]
    if payload["format"] != ARTIFACT_FORMAT or not names or any(not isinstance(name, str) for name in names):
        raise ValueError("Unsupported model artifact.")
    if set(document) != {"kind", *(field.name for field in fields(kind_type))}:
        raise ValueError("Unexpected model fields.")
    values = {}
    for field in fields(kind_type):
        value = np.asarray(document[field.name], dtype=float)
        if not np.isfinite(value).all() or value.shape != (() if field.name == "intercept" else (len(names),)):
            raise ValueError("Invalid model values.")
        values[field.name] = float(value) if field.name == "intercept" else value
    return payload | {"model": kind_type(**values)}


def _trusted_path(raw_path):
    """Only a regular file under the model root, reached without a link, may be read."""
    path = resolve_artifact_path(raw_path)
    root = Path(settings.BASE_DIR) / "ml_models" / "alfred"
    relative = os.path.relpath(path, root)
    expected = os.path.join(os.path.realpath(root), relative)
    if (relative.split(os.sep)[0] == os.pardir or os.path.isabs(relative)
            or os.path.normcase(os.path.realpath(path)) != os.path.normcase(expected)
            or not path.is_file() or path.stat().st_nlink != 1):
        raise ValueError("Untrusted model path.")
    return path


def _read_trusted(raw_path):
    path = _trusted_path(raw_path)
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("Model artifact exceeds its size limit.")
    return path.read_bytes()


def build_artifact_evidence(model_key, artifact_path, training_version):
    """Bind readiness to what the trainer just wrote; anything else earns no evidence."""
    try:
        raw = _read_trusted(artifact_path)
        schema = _parse_artifact(raw)["feature_names"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}
    return {"role": model_key, "sha256": sha256(raw).hexdigest(), "format": ARTIFACT_FORMAT,
            "schema": schema, "training_version": training_version}


def _evidence_matches(state, artifact_format, schema):
    evidence = state.artifact_evidence
    try:
        version = datetime.fromisoformat(evidence["training_version"])
        return (evidence["role"] == state.model_key and evidence["format"] == artifact_format
                and evidence["schema"] == list(schema) and version == state.last_finished_at)
    except (KeyError, TypeError, ValueError):
        return False


def _verified_payload(state, schema):
    """Digest and evidence are checked on the same bytes that are then parsed."""
    if not _evidence_matches(state, ARTIFACT_FORMAT, schema):
        return None
    try:
        raw = _read_trusted(state.artifact_path)
        if sha256(raw).hexdigest() != state.artifact_evidence["sha256"]:
            return None
        payload = _parse_artifact(raw)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
    return payload if payload["feature_names"] == list(schema) else None


def load_inference_artifact(model_key, model_path=None, *, schema):
    state = AdaptiveModelState.objects.filter(model_key=model_key).first()
    if state is None or not state.inference_ready:
        return None
    artifact_path = resolve_artifact_path(state.artifact_path)
    if model_path is not None and resolve_artifact_path(model_path).resolve() != artifact_path.resolve():
        return None
    return _verified_payload(state, schema)


def verified_model_file(state, artifact_format, schema):
    """For a large file its own safe loader reads, such as safetensors."""
    if not _evidence_matches(state, artifact_format, schema):
        return None
    try:
        path = _trusted_path(state.artifact_path)
        with path.open("rb") as stream:
            digest = file_digest(stream, "sha256").hexdigest()
    except (OSError, ValueError):
        return None
    return path if digest == state.artifact_evidence["sha256"] else None
