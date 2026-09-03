# from __future__ import annotations

# from typing import Any

# import pandas as pd
# from catboost import CatBoostClassifier
# from sklearn.base import BaseEstimator, ClassifierMixin
# from sklearn.compose import ColumnTransformer
# from sklearn.ensemble import GradientBoostingClassifier
# from sklearn.impute import SimpleImputer
# from sklearn.linear_model import LogisticRegression
# from sklearn.pipeline import Pipeline
# from sklearn.preprocessing import OneHotEncoder, StandardScaler
# from xgboost import XGBClassifier

# from .features import BINARY_COLUMNS, CATEGORICAL_COLUMNS, NUMERIC_COLUMNS

# RANDOM_STATE = 42


# class CatBoostLeadModel(BaseEstimator, ClassifierMixin):
#     """Small sklearn-compatible wrapper that lets CatBoost use native categories."""

#     def __init__(
#         self,
#         iterations: int = 300,
#         depth: int = 6,
#         learning_rate: float = 0.05,
#         random_state: int = RANDOM_STATE,
#     ) -> None:
#         self.iterations = iterations
#         self.depth = depth
#         self.learning_rate = learning_rate
#         self.random_state = random_state
#         self.model_: CatBoostClassifier | None = None

#     @staticmethod
#     def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
#         data = frame.copy()
#         for column in CATEGORICAL_COLUMNS:
#             data[column] = data[column].fillna("__missing__").astype(str)
#         for column in BINARY_COLUMNS:
#             data[column] = data[column].fillna(0).astype(int)
#         for column in NUMERIC_COLUMNS:
#             data[column] = pd.to_numeric(data[column], errors="coerce")
#         return data

#     def fit(self, x: pd.DataFrame, y: pd.Series) -> "CatBoostLeadModel":
#         prepared = self._prepare(x)
#         self.model_ = CatBoostClassifier(
#             iterations=self.iterations,
#             depth=self.depth,
#             learning_rate=self.learning_rate,
#             loss_function="Logloss",
#             eval_metric="PRAUC",
#             random_seed=self.random_state,
#             verbose=False,
#             allow_writing_files=False,
#         )
#         self.model_.fit(prepared, y, cat_features=CATEGORICAL_COLUMNS)
#         return self

#     def predict_proba(self, x: pd.DataFrame) -> Any:
#         if self.model_ is None:
#             raise RuntimeError("CatBoostLeadModel has not been fitted.")
#         return self.model_.predict_proba(self._prepare(x))


# def build_preprocessor() -> ColumnTransformer:
#     numeric_pipeline = Pipeline(
#         steps=[
#             # Retain an all-missing rollout column (for example a newly added
#             # CRM field) as a neutral constant instead of dropping it with a warning.
#             ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
#             ("scaler", StandardScaler()),
#         ]
#     )
#     categorical_pipeline = Pipeline(
#         steps=[
#             ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
#             (
#                 "onehot",
#                 OneHotEncoder(handle_unknown="ignore", sparse_output=False),
#             ),
#         ]
#     )

#     return ColumnTransformer(
#         transformers=[
#             ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
#             ("categorical", categorical_pipeline, CATEGORICAL_COLUMNS),
#             ("binary", "passthrough", BINARY_COLUMNS),
#         ],
#         remainder="drop",
#     )


# def sklearn_pipeline(classifier: BaseEstimator) -> Pipeline:
#     return Pipeline(
#         steps=[
#             ("preprocessor", build_preprocessor()),
#             ("classifier", classifier),
#         ]
#     )


# def build_model_candidates() -> dict[str, BaseEstimator]:
#     """Fixed, untuned candidates evaluated on exactly the same holdout."""
#     return {
#         "logistic_regression": sklearn_pipeline(
#             LogisticRegression(max_iter=1000, solver="liblinear", random_state=RANDOM_STATE)
#         ),
#         "gradient_boosting": sklearn_pipeline(
#             GradientBoostingClassifier(random_state=RANDOM_STATE)
#         ),
#         "xgboost": sklearn_pipeline(
#             XGBClassifier(
#                 n_estimators=300,
#                 max_depth=6,
#                 learning_rate=0.05,
#                 subsample=1.0,
#                 colsample_bytree=1.0,
#                 objective="binary:logistic",
#                 eval_metric="logloss",
#                 random_state=RANDOM_STATE,
#                 n_jobs=-1,
#             )
#         ),
#         "catboost": CatBoostLeadModel(),
#     }

from __future__ import annotations

from typing import Any

import pandas as pd
from catboost import CatBoostClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from .features import BINARY_COLUMNS, CATEGORICAL_COLUMNS, NUMERIC_COLUMNS

RANDOM_STATE = 42


class CatBoostLeadModel(BaseEstimator, ClassifierMixin):
    """Small sklearn-compatible wrapper that lets CatBoost use native categories."""

    def __init__(
        self,
        iterations: int = 300,
        depth: int = 6,
        learning_rate: float = 0.05,
        random_state: int = RANDOM_STATE,
    ) -> None:
        self.iterations = iterations
        self.depth = depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.model_: CatBoostClassifier | None = None

    @staticmethod
    def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        for column in CATEGORICAL_COLUMNS:
            data[column] = data[column].fillna("__missing__").astype(str)
        for column in BINARY_COLUMNS:
            data[column] = data[column].fillna(0).astype(int)
        for column in NUMERIC_COLUMNS:
            data[column] = pd.to_numeric(data[column], errors="coerce")
        return data

    def fit(self, x: pd.DataFrame, y: pd.Series) -> "CatBoostLeadModel":
        prepared = self._prepare(x)
        self.model_ = CatBoostClassifier(
            iterations=self.iterations,
            depth=self.depth,
            learning_rate=self.learning_rate,
            loss_function="Logloss",
            eval_metric="PRAUC",
            random_seed=self.random_state,
            verbose=False,
            allow_writing_files=False,
            # Converted leads are only ~7% of this dataset. Without this,
            # CatBoost minimizes loss by leaning toward "not converted" almost
            # everywhere, which makes every predicted probability look low
            # regardless of how promising the lead actually is. This reweights
            # the rare "converted" class internally so probabilities reflect
            # each lead's relative risk instead of just the overall base rate.
            auto_class_weights="Balanced",
        )
        self.model_.fit(prepared, y, cat_features=CATEGORICAL_COLUMNS)
        return self

    def predict_proba(self, x: pd.DataFrame) -> Any:
        if self.model_ is None:
            raise RuntimeError("CatBoostLeadModel has not been fitted.")
        return self.model_.predict_proba(self._prepare(x))


def build_preprocessor() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            # Retain an all-missing rollout column (for example a newly added
            # CRM field) as a neutral constant instead of dropping it with a warning.
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, CATEGORICAL_COLUMNS),
            ("binary", "passthrough", BINARY_COLUMNS),
        ],
        remainder="drop",
    )


def sklearn_pipeline(classifier: BaseEstimator) -> Pipeline:
    return BalancedPipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("classifier", classifier),
        ]
    )


class BalancedPipeline(Pipeline):
    """A normal sklearn Pipeline that automatically upweights the rare
    "converted" class at fit time.

    Why this is needed: only ~7% of leads convert in this dataset. A model
    trained without any correction for that naturally learns that predicting
    a low probability almost everywhere is the safest bet - it still gets
    ~93% accuracy that way, but every score comes out low, even for leads
    that are relatively much more promising than average. Passing a
    class-balanced sample_weight at fit time corrects for this, without
    changing anything about how train.py calls model.fit(x, y) or how
    scoring.py calls predict_proba().
    """

    def fit(self, X, y=None, **fit_params):
        if y is not None:
            sample_weight = compute_sample_weight(class_weight="balanced", y=y)
            classifier_step_name = self.steps[-1][0]
            fit_params[f"{classifier_step_name}__sample_weight"] = sample_weight
        return super().fit(X, y, **fit_params)


def build_model_candidates() -> dict[str, BaseEstimator]:
    """Fixed, untuned candidates evaluated on exactly the same holdout."""
    return {
        "logistic_regression": sklearn_pipeline(
            LogisticRegression(max_iter=1000, solver="liblinear", random_state=RANDOM_STATE)
        ),
        "gradient_boosting": sklearn_pipeline(
            GradientBoostingClassifier(random_state=RANDOM_STATE)
        ),
        "xgboost": sklearn_pipeline(
            XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=1.0,
                colsample_bytree=1.0,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
        ),
        "catboost": CatBoostLeadModel(),
    }