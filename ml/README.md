# ML Module

## Overview

This folder contains the lead conversion scoring system for the MGC AI Sales Assistant. It trains a binary classification model on historical CRM leads, saves the best model artifact, and exposes a small scoring wrapper used by the FastAPI app.

The runtime entry point used by the app is:

```python
from ml.scoring import load_metadata, score_lead
```

## Folder Structure

```text
ml/
  __init__.py
  scoring.py
  data/
  artifacts/
  mgc_lead_scoring/
    __init__.py
    features.py
    models.py
    schemas.py
    train.py
```

## Flow

```text
Historical leads CSV
  -> train.py loads and cleans data
  -> duplicate CRM records are removed with crm_record_hash
  -> features.py keeps only intake-time features
  -> models.py builds model candidates
  -> train.py selects the best model by validation Average Precision
  -> model.joblib and metadata.json are saved

New lead from web app
  -> app.py receives lead details
  -> scoring.py loads model.joblib
  -> single_lead_frame() creates a one-row DataFrame
  -> prepare_features() applies the same feature pipeline
  -> predict_proba() returns conversion probability
```

## Files

### `__init__.py`

Marks `ml/` as a Python package. It does not currently export any public functions.

### `scoring.py`

Runtime scoring wrapper used by `app.py`.

Main responsibilities:

- load saved model metadata from `ml/artifacts/metadata.json`
- load the trained model from `ml/artifacts/model.joblib`
- convert a single lead payload into model-ready features
- return conversion probability, score percentage, model name, metric, and user-facing note

Important constants:

- `ARTIFACT_DIR`: path to `ml/artifacts`
- `MODEL_PATH`: path to `model.joblib`
- `METADATA_PATH`: path to `metadata.json`

Important functions:

- `load_metadata()`: lazily loads model metadata and caches it.
- `load_model()`: lazily loads the saved Joblib model and caches it.
- `score_lead(payload)`: scores one lead and returns probability details.

Return format:

```python
{
    "conversion_probability": 0.0,
    "score_percent": 0.0,
    "model": "logistic_regression",
    "metric_name": "average_precision",
    "metric_value": 0.20834163505270975,
    "note": "Use this estimate to prioritize sales follow-up.",
}
```

### `data/`

Stores the leads CSV copy used inside the ML folder.

The main training command in the project README uses the root copy:

```text
data/leads.csv
```

This folder copy is useful when keeping ML data alongside the training package.

### `artifacts/`

Stores trained model outputs:

```text
model.joblib
metadata.json
```

`model.joblib` is the saved scikit-learn compatible model pipeline. `metadata.json` records model selection details, data split sizes, conversion rates, selected metric, and model comparison results.

Current saved artifact summary:

- selected model: `logistic_regression`
- selection rule: highest validation Average Precision on chronological validation data
- final untouched test Average Precision: `0.2083`
- rows after deduplication: `9000`
- duplicates removed: `160`

### `mgc_lead_scoring/__init__.py`

Marks `mgc_lead_scoring/` as the internal training package.

### `mgc_lead_scoring/features.py`

Contains the feature engineering shared by training and runtime scoring.

Main responsibilities:

- define the exact model input columns
- normalize city aliases like `ISB`, `Rwp`, and `khi`
- convert bedrooms into a categorical feature
- add time-based features from `created_at`
- fill missing newer intake fields as `unknown`
- keep only fields available at lead intake

Important constants:

- `MODEL_INPUT_COLUMNS`: final feature columns passed to the model
- `NUMERIC_COLUMNS`: numeric columns used by the preprocessor
- `CATEGORICAL_COLUMNS`: categorical columns used by the preprocessor
- `BINARY_COLUMNS`: boolean columns passed through to the model
- `CITY_ALIASES`: city normalization map
- `INTAKE_CATEGORICAL_DEFAULTS`: default `unknown` values for rollout intake fields

Important functions:

- `normalize_city(value)`: standardizes known city aliases.
- `_bedrooms_as_category(value)`: converts bedrooms to a stable category string.
- `prepare_features(frame)`: builds the final model input DataFrame.
- `single_lead_frame(payload)`: creates a one-row DataFrame for live scoring and adds `created_at` when missing.

### `mgc_lead_scoring/models.py`

Defines preprocessing and candidate models.

Main responsibilities:

- build a shared scikit-learn preprocessor
- impute and scale numeric values
- impute and one-hot encode categorical values
- pass binary values through unchanged
- compare multiple model families on the same feature set
- handle class imbalance with balanced sample weights

Important classes and functions:

- `CatBoostLeadModel`: sklearn-compatible wrapper around CatBoost with native categorical support.
- `BalancedPipeline`: scikit-learn pipeline that applies class-balanced sample weights during `fit()`.
- `build_preprocessor()`: creates the `ColumnTransformer` for numeric, categorical, and binary features.
- `sklearn_pipeline(classifier)`: wraps a classifier with preprocessing and balancing.
- `build_model_candidates()`: returns logistic regression, gradient boosting, XGBoost, and CatBoost candidates.

### `mgc_lead_scoring/schemas.py`

Defines Pydantic request and response schemas for lead scoring.

Main classes:

- `LeadScoreRequest`: validates lead-scoring input fields, allowed categories, numeric ranges, and optional `created_at`.
- `LeadScoreResponse`: describes the expected scoring output shape.

Note: `app.py` currently defines its own FastAPI request model, while this file provides reusable schemas for a cleaner API contract.

### `mgc_lead_scoring/train.py`

Training script for model comparison and artifact creation.

Main responsibilities:

- load the leads CSV
- validate required columns
- drop rows missing `created_at` or target
- sort by `created_at`
- remove duplicate CRM records using `crm_record_hash`
- split data chronologically into train, validation, and test
- select the best model using validation Average Precision
- refit the winner on all pre-test data
- evaluate once on the untouched test set
- save `model.joblib` and `metadata.json`

Important constants:

- `TARGET`: target column, `converted`
- `DUPLICATE_KEY`: duplicate key, `crm_record_hash`
- `NEW_INTAKE_COLUMNS`: newer intake fields that may be absent in older CRM exports

Important functions:

- `load_and_clean(path)`: reads and cleans the CSV before feature preparation.
- `train(data_path, artifact_dir)`: runs model selection, final fitting, evaluation, and artifact saving.
- `parse_args()`: parses CLI arguments.
- `main()`: CLI entry point.

## Training

From the project root:

```bash
python -m ml.mgc_lead_scoring.train --data data/leads.csv --artifacts ml/artifacts
```

This creates or replaces:

```text
ml/artifacts/model.joblib
ml/artifacts/metadata.json
```

## Scoring

Runtime scoring happens through `score_lead()`:

```python
from ml.scoring import score_lead

result = score_lead({
    "source": "Referral",
    "city": "Islamabad",
    "area": None,
    "property_type": "Apartment",
    "budget_pkr_lac": 220,
    "bedrooms": 2,
    "is_overseas": False,
    "referred_by_existing_client": True,
    "has_financing_approved": False,
})
```

The FastAPI app exposes this through:

```text
POST /api/score
```

## Metric

Average Precision is used because conversion is rare. Accuracy would reward a model for predicting most leads as non-converting, while Average Precision checks whether likely converters are ranked near the top for sales follow-up.

## Data Decisions

The model keeps only intake-time features. It drops post-contact leakage such as calls, WhatsApp replies, site visits, and token amount because those values are only known after sales activity begins.

Missing newer intake fields are treated as `unknown` so the same code works with older CRM exports. Once those fields are captured historically, retraining will automatically use their real values.
