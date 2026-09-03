-- ============================================================
-- queries.sql
-- Dialect: SQLite
-- ============================================================


-- ------------------------------------------------------------
-- QUERY 1: Conversion rate by lead source
--
-- Requirement: only sources with 200+ leads, best conversion first.
--
-- `converted` in this dataset is already a clean 0/1 integer (verified by
-- inspecting the actual CSV), so SUM(converted) directly gives the count
-- of converted leads per source - no CASE/WHEN mapping needed.
--
-- Conversion rate = converted leads / total leads * 100.
-- NULLIF(COUNT(*), 0) prevents a division-by-zero error, even though in
-- practice COUNT(*) can't be zero for a group that exists.
-- ------------------------------------------------------------
SELECT
    source,
    COUNT(*)                                              AS total_leads,
    SUM(converted)                                        AS converted_leads,
    ROUND(100.0 * SUM(converted) / NULLIF(COUNT(*), 0), 2) AS conversion_rate_pct
FROM leads
GROUP BY source                    -- compare performance across acquisition channels
HAVING COUNT(*) >= 200              -- ignore sources with too few leads to be a reliable sample
ORDER BY conversion_rate_pct DESC;  -- best-performing source first


-- ------------------------------------------------------------
-- QUERY 2: Find duplicate leads
--
-- Duplicate definition used here: two rows sharing the same
-- crm_record_hash. This dataset has no email/phone/name to key on, but
-- crm_record_hash is present on every row, and inspecting the real data
-- confirms that every pair of rows sharing a hash is identical on every
-- other field too (same source, city, budget, activity, converted
-- outcome) - the only difference is the lead_id, where the duplicate
-- copy has a "-B" suffix. That makes crm_record_hash a safe, specific
-- duplicate signal (unlike e.g. city or source, which many unrelated
-- leads legitimately share).
--
-- This query is meant to run against the RAW data (e.g. a staging table
-- before the UNIQUE constraint in schema.sql is applied, or on an export
-- that hasn't been deduplicated yet) - once data is loaded through
-- schema.sql's UNIQUE(crm_record_hash) constraint, this should return
-- zero rows going forward.
-- ------------------------------------------------------------
SELECT
    crm_record_hash,
    COUNT(*)               AS occurrences,
    GROUP_CONCAT(lead_id)   AS duplicate_lead_ids
FROM leads
GROUP BY crm_record_hash
HAVING COUNT(*) > 1        -- only groups that actually repeat are duplicates
ORDER BY occurrences DESC;
