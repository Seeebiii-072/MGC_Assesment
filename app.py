# from __future__ import annotations

# import streamlit as st

# from assistant import answer_question
# from ml.scoring import load_metadata, score_lead

# SOURCES = [
#     "Facebook Ads",
#     "Property Portal",
#     "Google Search",
#     "Instagram",
#     "Referral",
#     "Walk-in",
#     "WhatsApp Campaign",
#     "Expo Stall",
#     "Billboard",
# ]

# PROPERTY_TYPES = [
#     "Apartment",
#     "Plot",
#     "Villa",
#     "Commercial Shop",
#     "Penthouse",
#     "Farmhouse",
# ]

# AREAS = [
#     "",
#     "Blue World City",
#     "Gulberg Greens",
#     "Top City",
#     "B-17",
#     "Park View City",
#     "GT Road Corridor",
#     "Bahria Town",
#     "Bani Gala",
#     "Chakri Road",
#     "DHA",
# ]


# st.set_page_config(page_title="MGC AI Engineer Assessment", page_icon="MGC")
# st.title("MGC AI Engineer Assessment")

# assistant_tab, scoring_tab = st.tabs(["Document Assistant", "Lead Scoring"])

# with assistant_tab:
#     st.subheader("Ask an MGC document question")
#     question = st.text_input("Question", placeholder="What is the transfer fee?")

#     if st.button("Ask", type="primary") and question.strip():
#         result = answer_question(question)

#         st.markdown("### Answer")
#         st.write(result["answer"])

#         st.markdown("### Status")
#         st.write(result["status"])

#         if result.get("calculation"):
#             st.markdown("### Calculation")
#             st.code(result["calculation"])

#         st.markdown("### Sources")
#         if result["sources"]:
#             for source in result["sources"]:
#                 st.write(f"- {source}")
#         else:
#             st.write("- None")

#     with st.expander("Example questions"):
#         st.markdown(
#             "- What is the base price of a 2-bed in Block B?\n"
#             "- What is the total price for a Margalla-facing corner unit, floor 15, 2-bed Block B?\n"
#             "- What's the transfer fee?\n"
#             "- What is the rental yield on a 1-bed?\n"
#             "- Who is the anchor tenant?"
#         )

# with scoring_tab:
#     st.subheader("Score a new lead")
#     metadata = load_metadata()
#     if metadata:
#         metric = metadata.get("metric_value")
#         metric_text = f"{metric:.4f}" if isinstance(metric, (int, float)) else "unknown"
#         st.caption(f"Model: {metadata.get('model', 'unknown')} | Average Precision: {metric_text}")

#     with st.form("lead_score_form"):
#         col1, col2 = st.columns(2)
#         with col1:
#             source = st.selectbox("Lead source", SOURCES, index=4)
#             city = st.text_input("City", value="Islamabad")
#             area_choice = st.selectbox("Area", AREAS, index=0)
#             property_type = st.selectbox("Property type", PROPERTY_TYPES)
#             budget_pkr_lac = st.number_input("Budget (PKR lac)", min_value=0.0, value=220.0)
#             bedrooms = st.number_input("Bedrooms", min_value=0, max_value=20, value=2, step=1)
#         with col2:
#             is_overseas = st.checkbox("Overseas lead")
#             referred_by_existing_client = st.checkbox("Referred by existing client")
#             has_financing_approved = st.checkbox("Financing already approved")
#             purchase_timeframe = st.selectbox(
#                 "Purchase timeframe",
#                 ["unknown", "0_30_days", "1_3_months", "3_6_months"],
#             )
#             payment_method = st.selectbox("Payment method", ["unknown", "cash", "financing"])
#             purpose = st.selectbox("Purchase purpose", ["unknown", "investment", "own_use"])

#         with st.expander("Optional intake details"):
#             col3, col4 = st.columns(2)
#             with col3:
#                 budget_inventory_match = st.selectbox("Budget matches inventory", ["unknown", "yes", "no"])
#                 selected_project_or_unit_type = st.selectbox("Project or unit type selected", ["unknown", "yes", "no"])
#                 preferred_location_match = st.selectbox("Preferred location matches", ["unknown", "yes", "no"])
#             with col4:
#                 contact_verified = st.selectbox("Phone or email verified", ["unknown", "yes", "no"])
#                 has_prior_mgc_relationship = st.selectbox("Prior relationship with MGC", ["unknown", "yes", "no"])
#                 initial_intent_level = st.selectbox("Initial intent level", ["unknown", "low", "medium", "high"])
#                 previous_inquiry_count = st.number_input("Previous inquiries", min_value=0, value=0, step=1)

#         submitted = st.form_submit_button("Score Lead", type="primary")

#     if submitted:
#         payload = {
#             "source": source,
#             "city": city,
#             "area": area_choice or None,
#             "property_type": property_type,
#             "budget_pkr_lac": budget_pkr_lac,
#             "bedrooms": bedrooms,
#             "is_overseas": is_overseas,
#             "referred_by_existing_client": referred_by_existing_client,
#             "has_financing_approved": has_financing_approved,
#             "purchase_timeframe": purchase_timeframe,
#             "budget_inventory_match": budget_inventory_match,
#             "payment_method": payment_method,
#             "purpose": purpose,
#             "selected_project_or_unit_type": selected_project_or_unit_type,
#             "preferred_location_match": preferred_location_match,
#             "contact_verified": contact_verified,
#             "has_prior_mgc_relationship": has_prior_mgc_relationship,
#             "initial_intent_level": initial_intent_level,
#             "previous_inquiry_count": previous_inquiry_count,
#         }
#         try:
#             result = score_lead(payload)
#             st.metric("Conversion Probability", f"{result['score_percent']:.1f}%")
#             st.write(result["note"])
#         except Exception as exc:
#             st.error(f"Could not score lead: {exc}")

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from assistant import answer_question
from ml.scoring import load_metadata, score_lead


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="MGC AI Sales Assistant")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


class QuestionRequest(BaseModel):
    question: str


class LeadRequest(BaseModel):
    source: str
    city: str
    area: str | None = None
    property_type: str
    budget_pkr_lac: float
    bedrooms: int
    is_overseas: bool
    referred_by_existing_client: bool
    has_financing_approved: bool

    purchase_timeframe: str = "unknown"
    budget_inventory_match: str = "unknown"
    payment_method: str = "unknown"
    purpose: str = "unknown"
    selected_project_or_unit_type: str = "unknown"
    preferred_location_match: str = "unknown"
    contact_verified: str = "unknown"
    has_prior_mgc_relationship: str = "unknown"
    initial_intent_level: str = "unknown"
    previous_inquiry_count: int = 0


@app.get("/", response_class=HTMLResponse)
async def home():
    index_file = BASE_DIR / "templates" / "index.html"

    if not index_file.exists():
        return HTMLResponse(
            content="<h1>Error: templates/index.html not found</h1>",
            status_code=500,
        )

    return HTMLResponse(
        content=index_file.read_text(encoding="utf-8")
    )


@app.post("/api/ask")
async def ask_question(payload: QuestionRequest):
    if not payload.question.strip():
        return {
            "success": False,
            "error": "Please enter a question.",
        }

    try:
        result = answer_question(payload.question.strip())

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "status": result.get("status", ""),
            "calculation": result.get("calculation"),
            "sources": result.get("sources", []),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.post("/api/score")
async def score(payload: LeadRequest):
    try:
        lead = payload.model_dump()

        result = score_lead(lead)

        return {
            "success": True,
            "score_percent": result["score_percent"],
            "note": result.get("note", ""),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@app.get("/api/model-info")
async def model_info():
    try:
        metadata = load_metadata()

        return {
            "model": metadata.get("model", "unknown"),
            "average_precision": metadata.get("metric_value"),
        }

    except Exception as exc:
        return {
            "model": "unknown",
            "average_precision": None,
            "error": str(exc),
        }