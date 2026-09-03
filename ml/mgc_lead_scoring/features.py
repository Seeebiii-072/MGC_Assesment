from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

MODEL_INPUT_COLUMNS = [
    "source",
    "city",
    "area",
    "property_type",
    "budget_pkr_lac",
    "bedrooms_cat",
    "is_overseas",
    "referred_by_existing_client",
    "has_financing_approved",
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
    "created_month",
    "created_dow",
    "created_hour",
]

NUMERIC_COLUMNS = ["budget_pkr_lac", "previous_inquiry_count", "created_hour"]
CATEGORICAL_COLUMNS = [
    "source",
    "city",
    "area",
    "property_type",
    "bedrooms_cat",
    "purchase_timeframe",
    "budget_inventory_match",
    "payment_method",
    "purpose",
    "selected_project_or_unit_type",
    "preferred_location_match",
    "contact_verified",
    "has_prior_mgc_relationship",
    "initial_intent_level",
    "created_month",
    "created_dow",
]
BINARY_COLUMNS = [
    "is_overseas",
    "referred_by_existing_client",
    "has_financing_approved",
]

CITY_ALIASES = {
    "isb": "Islamabad",
    "islamabad": "Islamabad",
    "rwp": "Rawalpindi",
    "rawalpindi": "Rawalpindi",
    "khi": "Karachi",
    "karachi": "Karachi",
    "lahore": "Lahore",
    "peshawar": "Peshawar",
    "faisalabad": "Faisalabad",
    "multan": "Multan",
    "gujranwala": "Gujranwala",
    "abbottabad": "Abbottabad",
}

# These fields must be captured when the lead is created, before any sales activity.
# Keeping a known "unknown" category avoids treating an unanswered question as "no".
INTAKE_CATEGORICAL_DEFAULTS = {
    "purchase_timeframe": "unknown",
    "budget_inventory_match": "unknown",
    "payment_method": "unknown",
    "purpose": "unknown",
    "selected_project_or_unit_type": "unknown",
    "preferred_location_match": "unknown",
    "contact_verified": "unknown",
    "has_prior_mgc_relationship": "unknown",
    "initial_intent_level": "unknown",
}


def normalize_city(value: Any) -> Any:
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    return CITY_ALIASES.get(cleaned.casefold(), cleaned.title())


def _bedrooms_as_category(value: Any) -> str:
    if pd.isna(value):
        return "__missing__"
    return str(int(float(value)))


def prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create only features that are intended to be available at lead intake."""
    data = frame.copy()

    # Older CRM exports will not contain newer intake questions. Leave those values
    # explicitly unknown so the same training command remains usable during rollout.
    for column, default in INTAKE_CATEGORICAL_DEFAULTS.items():
        if column not in data:
            data[column] = default
        else:
            data[column] = data[column].fillna(default)
    if "previous_inquiry_count" not in data:
        data["previous_inquiry_count"] = None

    data["city"] = data["city"].map(normalize_city)
    data["area"] = data["area"].where(data["area"].notna(), "__missing__")
    data["bedrooms_cat"] = data["bedrooms"].map(_bedrooms_as_category)

    created = pd.to_datetime(data["created_at"], errors="coerce")
    data["created_month"] = created.dt.month.astype("Int64").astype(str)
    data["created_dow"] = created.dt.dayofweek.astype("Int64").astype(str)
    data["created_hour"] = created.dt.hour.astype("float64")

    return data[MODEL_INPUT_COLUMNS]


def single_lead_frame(payload: dict[str, Any]) -> pd.DataFrame:
    record = payload.copy()
    record["created_at"] = record.get("created_at") or datetime.now(ZoneInfo("Asia/Karachi")).isoformat()
    return pd.DataFrame([record])
