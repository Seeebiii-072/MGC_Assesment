# MGC Leads — Database Solution (Part 2)

## Overview

A minimal SQLite database for the `leads.csv` CRM export (9,160 rows),
built directly around the columns that actually exist in that file — not
a generic CRM template. It stores leads in a single table, prevents future
duplicate inserts, and answers the two required questions: conversion
rate by lead source, and which leads are duplicates.

## Dataset Findings

- 9,160 rows, 20 columns. No email, phone, or name columns exist in this
  export — the schema and duplicate strategy are built around what's
  actually there instead of assuming those fields.
- `lead_id` (e.g. `MGC-104067`) is already unique across all 9,160 rows.
- `converted` is a clean 0/1 integer already (8,526 not converted, 634
  converted) — no format normalization needed.
- `source` and `property_type` are already clean and consistently
  spelled/cased.
- `city` has real inconsistencies — the same city appears as, e.g.,
  `Islamabad`, `ISLAMABAD`, and `ISB`. Not required for the two assessment
  queries, but should be normalized (e.g. a lookup/mapping table or a
  cleaning step) before using `city` for reporting.
- Several numeric columns have legitimate nulls (`area`, `budget_pkr_lac`,
  `bedrooms`, `first_response_minutes`, `agent_experience_years`) —
  consistent with fields not always captured at initial lead intake.
- **160 pairs of rows (320 rows total) share the same `crm_record_hash`.**
  Checked every one: in all 160 pairs, every other column is identical —
  the only difference is `lead_id`, where the duplicate has a `-B` suffix
  (e.g. `MGC-104974` / `MGC-104974-B`). These are re-submissions of the
  same lead, not coincidental hash collisions.

## Schema

One table (`leads`), because the data has no repeating groups — every
column is a single fact about a single lead. Splitting `source` or `city`
into separate lookup tables would only add joins without removing any
actual duplication, so it isn't justified here.

`lead_id` is kept as the primary key rather than adding a surrogate ID,
since it's already unique, stable, and business-meaningful.

## Duplicate Prevention

- **Identifier used:** `crm_record_hash` — an existing fingerprint column
  already present on every row of the export (not something invented for
  this task).
- **Why not name/email/phone/city:** those columns don't exist in this
  dataset, and even if they did, something like city or source is shared
  by thousands of unrelated leads — using a weak identifier like that
  would produce constant false positives.
- **Enforcement:** `schema.sql` adds `UNIQUE (crm_record_hash)` to the
  table, so the database itself will reject a second insert with a hash
  that's already present, going forward.
- **Important caveat:** the *current* CSV export already contains the 160
  known duplicate pairs described above. Loading it as-is with a plain
  `INSERT` will hit the `UNIQUE` constraint on those 160 rows. See "How to
  Run" below for the recommended way to load this specific file.

## Query 1 — Conversion Rate by Lead Source

Groups leads by `source`, keeps only sources with 200+ leads, and computes
`converted leads / total leads * 100`, guarded with `NULLIF` against
division by zero, sorted best-first. Run against the real data, all 9
sources clear 200 leads, and **Referral has the best conversion rate
(13.18%)**, Expo Stall the worst (2.95%).

## Query 2 — Duplicate Lead Detection

Groups rows by `crm_record_hash` and keeps only groups with more than one
row, returning the hash, how many times it occurs, and the specific
`lead_id`s involved (via `GROUP_CONCAT`) so the duplicates can be reviewed
or merged. Verified against the raw data: it correctly returns exactly the
160 known duplicate groups.

This is meant to run against raw/staging data (e.g. before applying the
`UNIQUE` constraint, or on a fresh export) — once data has been loaded
through `schema.sql`, this should return zero rows.

## SQL Dialect

**SQLite** — a single file, no server to set up, and everything used here
(`GROUP_CONCAT`, `NULLIF`, `CHECK` constraints) is supported natively.

## How to Run

```bash
# 1. Create the database and table
sqlite3 leads.db < schema.sql

# 2. Load the CSV. Because the raw export contains 160 known duplicate
#    rows (see above), import into a temporary table first, then insert
#    with "OR IGNORE" so the UNIQUE constraint keeps the first-seen copy
#    of each duplicate and silently skips the rest:
sqlite3 leads.db <<'SQL'
.mode csv
.import data/leads.csv leads_raw
INSERT OR IGNORE INTO leads
SELECT * FROM leads_raw;
DROP TABLE leads_raw;
SQL

# 3. Run the two required queries
sqlite3 leads.db < queries.sql
```

(`leads_raw` above is a plain staging table with the same column order and
no constraints, created automatically by `.import`; it's dropped after
the data is copied into the real, constrained `leads` table.)
