from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LeadScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    city: str = Field(min_length=1)
    area: str | None = None
    property_type: str = Field(min_length=1)
    budget_pkr_lac: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    is_overseas: bool = False
    referred_by_existing_client: bool = False
    has_financing_approved: bool = False
    purchase_timeframe: Literal["0_30_days", "1_3_months", "3_6_months", "unknown"] = "unknown"
    budget_inventory_match: Literal["yes", "no", "unknown"] = "unknown"
    payment_method: Literal["cash", "financing", "unknown"] = "unknown"
    purpose: Literal["investment", "own_use", "unknown"] = "unknown"
    selected_project_or_unit_type: Literal["yes", "no", "unknown"] = "unknown"
    preferred_location_match: Literal["yes", "no", "unknown"] = "unknown"
    contact_verified: Literal["yes", "no", "unknown"] = "unknown"
    has_prior_mgc_relationship: Literal["yes", "no", "unknown"] = "unknown"
    initial_intent_level: Literal["low", "medium", "high", "unknown"] = "unknown"
    previous_inquiry_count: int | None = Field(default=None, ge=0)
    created_at: datetime | None = None


class LeadScoreResponse(BaseModel):
    conversion_probability: float
    score_percent: float
    model: str
    note: str
