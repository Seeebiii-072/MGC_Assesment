-- ============================================================
-- schema.sql
-- Dialect: SQLite
--
-- ONE TABLE DESIGN
-- The source data (leads.csv) has no repeating groups - each row is a
-- single, self-contained lead with no child records (no multiple phone
-- numbers, no multiple site visits stored as separate rows, etc). Splitting
-- this into several tables (e.g. a separate "sources" or "cities" table)
-- would only add joins without removing any real duplication, so a single
-- table is the simplest correct design here.
-- ============================================================

CREATE TABLE IF NOT EXISTS leads (

    -- PRIMARY KEY
    -- The CSV already contains "lead_id" (e.g. "MGC-104067"), and it is
    -- unique across all 9,160 rows. Since it's already reliable, stable,
    -- and meaningful to the business, we keep it as-is instead of adding
    -- a separate auto-generated surrogate key - that would just be an
    -- extra column pointing at the same thing.
    lead_id                         TEXT PRIMARY KEY,

    created_at                      TEXT NOT NULL,   -- ISO-format timestamp, stored as TEXT (SQLite has no native datetime type)
    source                          TEXT NOT NULL,   -- e.g. "Facebook Ads", "Referral" - already clean in the source data
    city                            TEXT NOT NULL,   -- NOTE: raw data has casing/abbreviation inconsistencies (e.g. "Islamabad" vs "ISLAMABAD" vs "ISB") - normalize before insert, see README
    area                            TEXT,             -- nullable: ~5% of rows have no area recorded
    property_type                   TEXT NOT NULL,

    budget_pkr_lac                  REAL,             -- nullable: budget not always captured at lead stage
    bedrooms                        INTEGER,          -- nullable: not applicable to every property type (e.g. Plot, Commercial Shop)
    first_response_minutes          REAL,
    calls_made                      INTEGER NOT NULL DEFAULT 0,
    total_call_seconds              REAL    NOT NULL DEFAULT 0,
    whatsapp_replies                INTEGER NOT NULL DEFAULT 0,
    site_visits                     INTEGER NOT NULL DEFAULT 0,
    agent_experience_years          REAL,             -- nullable: agent not always assigned yet

    is_overseas                     INTEGER NOT NULL DEFAULT 0 CHECK (is_overseas IN (0, 1)),
    referred_by_existing_client     INTEGER NOT NULL DEFAULT 0 CHECK (referred_by_existing_client IN (0, 1)),
    has_financing_approved          INTEGER NOT NULL DEFAULT 0 CHECK (has_financing_approved IN (0, 1)),

    token_amount_received_pkr       REAL    NOT NULL DEFAULT 0,

    -- crm_record_hash is an existing fingerprint column already present in
    -- every row of the source export (not something we invented). See the
    -- DUPLICATE PREVENTION comment below for why this is what we key on.
    crm_record_hash                 INTEGER NOT NULL,

    converted                       INTEGER NOT NULL DEFAULT 0 CHECK (converted IN (0, 1)),

    -- ------------------------------------------------------------------
    -- DUPLICATE PREVENTION
    --
    -- What makes a lead unique here?
    -- This dataset has no email, phone, or name column to key on. What it
    -- does have is `crm_record_hash` on every row. Inspecting the actual
    -- data: 160 pairs of rows share the same crm_record_hash, and in
    -- EVERY one of those 160 pairs, every other column (source, city,
    -- area, budget, call activity, converted, etc.) is identical too -
    -- the only difference is the lead_id, where the duplicate copy has a
    -- "-B" suffix (e.g. "MGC-104974" and "MGC-104974-B"). That is a
    -- textbook duplicate re-submission, and crm_record_hash is clearly
    -- functioning as a reliable identity fingerprint for a lead.
    --
    -- Why not use city, source, or property_type for this? Because many
    -- genuinely different leads legitimately share the same city (e.g.
    -- thousands of leads from Islamabad) or the same source - those are
    -- not duplicates, they're just leads from the same channel/area.
    -- Weak identifiers like that would produce massive false positives.
    --
    -- This UNIQUE constraint means a second insert with the same
    -- crm_record_hash will be rejected by the database going forward.
    -- NOTE: because the *current* CSV export already contains 160 known
    -- duplicate pairs, loading the raw file as-is will hit this
    -- constraint on those 160 rows - that is intentional. See the
    -- "How to Run" section of README.md for the recommended way to load
    -- data (INSERT OR IGNORE), which keeps the first-seen copy of each
    -- duplicate and silently skips the rest.
    -- ------------------------------------------------------------------
    UNIQUE (crm_record_hash)
);

-- Helpful indexes for the two required queries and general reporting.
-- (SQLite already indexes UNIQUE columns automatically, so no separate
-- index is needed for crm_record_hash.)
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads (source);
CREATE INDEX IF NOT EXISTS idx_leads_converted ON leads (converted);
