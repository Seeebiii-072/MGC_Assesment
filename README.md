# MGC AI Sales Assistant

## Overview

This project is an integrated MGC AI Engineer assessment application with three parts:

- Part 1: a grounded MGC document assistant
- Part 2: SQLite schema and analysis queries for leads data
- Part 3: a lead conversion scoring model

The current application flow is a FastAPI backend with a plain HTML/CSS/JavaScript frontend:

```text
Browser UI -> FastAPI app.py -> document assistant / lead scoring model
```

## Application Flow

```text
User opens the web app
  -> Document Assistant tab
     -> POST /api/ask
     -> deterministic assessment answers or Chroma retrieval
     -> optional OpenAI grounded fallback
     -> answer, status, calculation, and sources

  -> Lead Scoring tab
     -> GET /api/model-info
     -> user enters intake-time lead details
     -> POST /api/score
     -> trained model returns conversion probability
```

## Architecture

```text
data/*.md -> assistant.ingest -> chroma_db -> assistant.answer_question()
data/leads.csv -> database/schema.sql + database/queries.sql
data/leads.csv -> ml training pipeline -> ml/artifacts/model.joblib
templates/index.html + static/* -> FastAPI routes in app.py
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The app is served with FastAPI/Uvicorn. If those packages are not already installed in your environment, install them as well:

```bash
python -m pip install fastapi uvicorn
```

## Environment

Copy `.env.example` to `.env` if you want LLM fallback answers for open-ended document questions.

The five assessment questions are answered deterministically from the documents and do not require an API key. Do not commit real API keys.

## Running The Application

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The web app has two tabs:

- Document Assistant: ask an MGC document question and see the answer, status, calculation, and sources.
- Lead Scoring: enter intake-time lead details and receive a conversion probability.

## API Endpoints

```text
GET  /                 Serves the frontend from templates/index.html
POST /api/ask          Answers a document question
POST /api/score        Scores a lead conversion probability
GET  /api/model-info   Returns saved model metadata
```

Example document request:

```bash
curl -X POST http://127.0.0.1:8000/api/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What is the transfer fee?\"}"
```

## Part 1 - Document Assistant

The assistant supports:

- deterministic handlers for the five assessment questions
- ChromaDB retrieval for other document questions
- strict document-grounded LLM fallback when an OpenAI API key is available
- source document and section reporting
- missing-information and conflicting-information handling

Build or refresh the vector database when documents change:

```bash
python -m assistant.ingest
```

Run the five assessment questions:

```bash
python tests/test_questions.py
```

Assessment questions:

```text
What is the base price of a 2-bed in Block B?
What is the total price for a Margalla-facing corner unit, floor 15, 2-bed Block B?
What's the transfer fee?
What is the rental yield on a 1-bed?
Who is the anchor tenant?
```

## Part 2 - Database

The database files are in `database/`:

```text
database/schema.sql
database/queries.sql
database/README.md
```

The schema uses SQLite, keeps `lead_id` as the primary key, and prevents future duplicate logical leads with `UNIQUE (crm_record_hash)`.

The two required queries are:

- conversion rate by lead source for sources with 200 or more leads, highest first
- duplicate lead detection using `crm_record_hash`

See `database/README.md` for the full loading notes, including how to handle the 160 duplicate CRM record hashes in the raw CSV export.

## Part 3 - Lead Scoring

The lead scoring code lives under `ml/mgc_lead_scoring/`.

Current saved artifact:

- selected model: logistic regression
- final metric: Average Precision
- final chronological-test Average Precision: `0.2083`
- rows after deduplication: `9000`
- duplicates removed using `crm_record_hash`: `160`

The app loads `ml/artifacts/model.joblib`, uses the same `prepare_features()` pipeline as training, and calls `predict_proba()` to produce the conversion probability.

To retrain:

```bash
python -m ml.mgc_lead_scoring.train --data data/leads.csv --artifacts ml/artifacts
```

## Data Cleaning Decisions

Part 3 keeps only features available at lead intake. It removes duplicate CRM records by `crm_record_hash`, normalizes city aliases such as `ISB`, `Rwp`, and `khi`, imputes missing numeric values, gives missing categorical values an explicit category, drops IDs, and excludes post-contact leakage such as calls, WhatsApp replies, site visits, and token amount.

## Metric

Average Precision is used because conversion is rare. Accuracy would reward predicting most leads as non-converting, while Average Precision measures whether likely converters are ranked near the top for sales follow-up.

## Limitations

The current historical CSV does not include some stronger intake questions supported by the scoring form, so those fields train as `unknown` until the CRM captures them historically. The score is useful for prioritization, not a guaranteed probability of sale.

## What I Would Improve With More Time

- Add `fastapi` and `uvicorn` to `requirements.txt` so the runtime dependencies are complete.
- Calibrate predicted probabilities after more labeled data is collected.
- Add automated tests around the FastAPI endpoints and browser flow.
- Add a small CSV-to-SQL loading script for Part 2.
