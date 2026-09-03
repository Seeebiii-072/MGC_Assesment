# MGC AI Engineer Assessment

## Overview

This is one integrated assessment project containing:

- Part 1: grounded MGC document assistant
- Part 2: SQLite schema and analysis queries
- Part 3: lead conversion scoring model

The single application entry point is:

```bash
streamlit run app.py
```

## Architecture

```text
MGC Markdown documents -> Chroma retrieval -> grounded assistant -> answer + sources
leads.csv -> cleaning/preprocessing -> logistic regression pipeline -> conversion probability
leads.csv -> SQLite database -> conversion analysis / duplicate detection
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` if you want LLM fallback answers for open-ended document questions. The five assessment questions are answered deterministically from the documents and do not require an API key.

Do not commit real API keys.

## Part 1 - Document Assistant

The assistant reuses the existing Part 1 implementation:

- deterministic handlers for the five assessment questions
- ChromaDB retrieval for other questions
- strict document-grounded LLM fallback
- source document and section reporting
- missing-information and conflicting-information handling

Build or refresh the vector database when documents change:

```bash
python -m assistant.ingest
```

Run the five test questions:

```bash
python tests/test_questions.py
```

Test questions:

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
```

The schema uses SQLite, keeps `lead_id` as the primary key, and prevents future duplicate logical leads with `UNIQUE (normalized_crm_record_hash)`.

Run:

```bash
sqlite3 leads.db < database/schema.sql
sqlite3 leads.db < database/queries.sql
```

The two required queries are:

- conversion rate by lead source for sources with 200 or more leads, highest first
- duplicate lead detection using `normalized_crm_record_hash`

## Part 3 - Lead Scoring

The lead scoring code reuses the existing Python package under `ml/mgc_lead_scoring/`.

Current saved artifact:

- selected model: logistic regression
- final metric: Average Precision
- final chronological-test Average Precision: `0.2081`
- rows after deduplication: `9000`
- duplicates removed using `crm_record_hash`: `160`

The app loads `ml/artifacts/model.joblib`, uses the same `prepare_features()` pipeline as training, and calls `predict_proba()` to produce the conversion probability.

To retrain:

```bash
python -m ml.mgc_lead_scoring.train --data data/leads.csv --artifacts ml/artifacts
```

## Running The Application

```bash
streamlit run app.py
```

The app has two tabs:

- Document Assistant: ask an MGC document question and see answer, status, calculation, and sources.
- Lead Scoring: enter intake-time lead details and receive a conversion probability.

## Data Cleaning Decisions

Part 3 keeps only features available at lead intake. It removes duplicate CRM records by `crm_record_hash`, normalizes city aliases such as `ISB`, `Rwp`, and `khi`, imputes missing numeric values, gives missing categorical values an explicit category, drops IDs, and excludes post-contact leakage such as calls, WhatsApp replies, site visits, and token amount.

## Metric

Average Precision is used because conversion is rare. Accuracy would reward predicting most leads as non-converting, while Average Precision measures whether likely converters are ranked near the top for sales follow-up.

## Limitations

The current historical CSV does not include some stronger intake questions supported by the scoring form, so those fields train as `unknown` until the CRM captures them historically. The score is useful for prioritization, not a guaranteed probability of sale.

## What I Would Improve With More Time

- Calibrate predicted probabilities after more labeled data is collected.
- Add automated tests around the Streamlit scoring wrapper.
- Add a small CSV-to-SQL loading script for Part 2.
