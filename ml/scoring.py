from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from .mgc_lead_scoring.features import prepare_features, single_lead_frame

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"

_model = None
_metadata: dict[str, Any] | None = None


def load_metadata() -> dict[str, Any]:
    global _metadata
    if _metadata is None:
        _metadata = (
            json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            if METADATA_PATH.exists()
            else {}
        )
    return _metadata


def load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(
                "Model artifact not found. Run: python -m ml.mgc_lead_scoring.train "
                "--data data/leads.csv --artifacts ml/artifacts"
            )
        _model = joblib.load(MODEL_PATH)
        classifier = getattr(_model, "named_steps", {}).get("classifier")
        if classifier is not None and not hasattr(classifier, "multi_class"):
            # The saved artifact was produced by the original Part 3 project with
            # a newer sklearn build. sklearn 1.7 still reads it, but expects this
            # legacy attribute during predict_proba().
            classifier.multi_class = "auto"
    return _model


def score_lead(payload: dict[str, Any]) -> dict[str, Any]:
    model = load_model()
    metadata = load_metadata()
    raw = single_lead_frame(payload)
    features = prepare_features(raw)
    probability = float(model.predict_proba(features)[0, 1])
    return {
        "conversion_probability": probability,
        "score_percent": round(probability * 100, 1),
        "model": str(metadata.get("model", "unknown")),
        "metric_name": metadata.get("metric_name"),
        "metric_value": metadata.get("metric_value"),
        "note": "Use this estimate to prioritize sales follow-up.",
    }
