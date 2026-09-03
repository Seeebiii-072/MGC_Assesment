from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score

from .features import MODEL_INPUT_COLUMNS, prepare_features
from .models import build_model_candidates

TARGET = "converted"
DUPLICATE_KEY = "crm_record_hash"

# Optional during rollout: missing columns are represented as unknown by
# prepare_features. Once the CRM captures them historically, retraining will use
# their actual values without any code change.
NEW_INTAKE_COLUMNS = {
    "purchase_timeframe",
    "budget_inventory_match",
    "payment_method",
    "purpose",
    "selected_project_or_unit_type",
    "preferred_location_match",
    "contact_verified",
    "has_prior_mgc_relationship",
    "initial_intent_level",
    "previous_inquiry_count",
}


def load_and_clean(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        "created_at",
        "source",
        "city",
        "area",
        "property_type",
        "budget_pkr_lac",
        "bedrooms",
        "is_overseas",
        "referred_by_existing_client",
        "has_financing_approved",
        DUPLICATE_KEY,
        TARGET,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce")
    frame = frame.dropna(subset=["created_at", TARGET])

    # Same CRM lead may have been entered twice. Sort first so keep='first' is deterministic.
    frame = frame.sort_values("created_at")
    frame = frame.drop_duplicates(subset=[DUPLICATE_KEY], keep="first")
    return frame.reset_index(drop=True)


def train(data_path: Path, artifact_dir: Path) -> dict[str, object]:
    raw_row_count = len(pd.read_csv(data_path, usecols=[DUPLICATE_KEY]))
    frame = load_and_clean(data_path)
    unavailable_intake_columns = sorted(NEW_INTAKE_COLUMNS - set(frame.columns))
    if unavailable_intake_columns:
        print(
            "New intake columns unavailable in this export; treating them as unknown: "
            f"{', '.join(unavailable_intake_columns)}"
        )
    features = prepare_features(frame)
    target = frame[TARGET].astype(int)

    # Time-aware split: oldest 65% train, next 15% validation, newest 20% final test.
    # Models are selected on validation only; the final test remains untouched until selection.
    train_end = int(len(frame) * 0.65)
    validation_end = int(len(frame) * 0.80)
    if train_end <= 0 or validation_end <= train_end or validation_end >= len(frame):
        raise ValueError("Not enough rows for the chronological train/validation/test split.")

    x_train = features.iloc[:train_end]
    x_validation = features.iloc[train_end:validation_end]
    x_test = features.iloc[validation_end:]
    y_train = target.iloc[:train_end]
    y_validation = target.iloc[train_end:validation_end]
    y_test = target.iloc[validation_end:]

    candidates = build_model_candidates()
    comparison: list[dict[str, object]] = []

    print("\nModel selection on chronological validation data (higher AP is better)")
    print("-" * 76)

    for name, model in candidates.items():
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_validation)[:, 1]
        validation_ap = float(average_precision_score(y_validation, probabilities))
        comparison.append(
            {
                "model": name,
                "metric_name": "validation_average_precision",
                "metric_value": validation_ap,
            }
        )
        print(f"{name:<24} Validation Average Precision = {validation_ap:.4f}")

    comparison.sort(key=lambda item: float(item["metric_value"]), reverse=True)
    best_name = str(comparison[0]["model"])
    best_validation_ap = float(comparison[0]["metric_value"])

    # Rebuild the winner, refit on all pre-test data (65% + 15%), then evaluate once.
    x_pretest = features.iloc[:validation_end]
    y_pretest = target.iloc[:validation_end]
    best_model = build_model_candidates()[best_name]
    best_model.fit(x_pretest, y_pretest)
    test_probabilities = best_model.predict_proba(x_test)[:, 1]
    test_ap = float(average_precision_score(y_test, test_probabilities))

    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.joblib"
    metadata_path = artifact_dir / "metadata.json"
    joblib.dump(best_model, model_path)

    metadata: dict[str, object] = {
        "model": best_name,
        "selection_rule": "highest_average_precision_on_chronological_validation",
        "rows_after_deduplication": int(len(frame)),
        "duplicates_removed": int(raw_row_count - len(frame)),
        "initial_train_rows": int(len(x_train)),
        "validation_rows": int(len(x_validation)),
        "final_fit_rows": int(len(x_pretest)),
        "test_rows": int(len(x_test)),
        "initial_train_conversion_rate": float(y_train.mean()),
        "validation_conversion_rate": float(y_validation.mean()),
        "final_fit_conversion_rate": float(y_pretest.mean()),
        "test_conversion_rate": float(y_test.mean()),
        "selection_metric_name": "validation_average_precision",
        "selected_validation_metric": best_validation_ap,
        "metric_name": "average_precision",
        "metric_value": test_ap,
        "validation_start": frame.iloc[train_end]["created_at"].isoformat(),
        "test_start": frame.iloc[validation_end]["created_at"].isoformat(),
        "model_comparison": comparison,
        "model_input_columns": MODEL_INPUT_COLUMNS,
        "unavailable_intake_columns": unavailable_intake_columns,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("-" * 76)
    print(f"Selected model: {best_name} (validation AP = {best_validation_ap:.4f})")
    print(f"Final untouched test Average Precision = {test_ap:.4f}\n")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare four untuned lead-scoring models and save the best one"
    )
    parser.add_argument("--data", type=Path, required=True, help="Path to leads.csv")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "artifacts",
        help="Directory for model.joblib and metadata.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = train(args.data.resolve(), args.artifacts.resolve())
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
