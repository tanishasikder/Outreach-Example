'''
Cleans the raw CSVs with SQL and writes the results into data/data.duckdb,
replacing the accounts, deals and events tables.

Always rebuilds from the CSVs in data/, so it is safe to run again.
Run from the project root:
    python src/clean_data.py

The automated pipeline uses the same rules in dbt/ instead (dbt/models/staging/).
If you change a rule here, change it there too.

Stop the FastAPI server first: DuckDB only allows one writer at a time.
'''

import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "data.duckdb"
CSV = lambda name: (ROOT / "data" / f"{name}.csv").as_posix()

# Allowed category values. Must match the enums in src/schemas/validate.py
INDUSTRIES = ["logistics", "healthcare", "education", "manufacturing", "software",
              "media", "retail", "fintech", "energy"]
REGIONS = ["europe", "north_america", "latam", "apac"]
FUNDING_STAGES = ["series_c_plus", "series_b", "seed", "bootstrapped", "public", "series_a"]
LEAD_SOURCES = ["outbound", "inbound", "event", "referral"]
STATUSES = ["won", "lost", "open"]
EVENT_TYPES = ["site_visit", "pricing_page_view", "email_open", "email_click",
               "webinar_attend", "demo_request"]

sql_list = lambda values: ", ".join(f"'{v}'" for v in values)

# 1. Load raw CSVs (all as text, so bad values don't crash the load)
LOAD_RAW = f"""
CREATE OR REPLACE TEMP TABLE raw_accounts AS SELECT * FROM read_csv('{CSV("accounts")}', header=true, all_varchar=true);
CREATE OR REPLACE TEMP TABLE raw_deals    AS SELECT * FROM read_csv('{CSV("deals")}',    header=true, all_varchar=true);
CREATE OR REPLACE TEMP TABLE raw_events   AS SELECT * FROM read_csv('{CSV("events")}',   header=true, all_varchar=true);
"""

# 2. Accounts: trim + lowercase categories, cast types, out-of-range -> NULL,
#    drop rows missing required fields, one row per account_id
CLEAN_ACCOUNTS = f"""
CREATE OR REPLACE TABLE accounts AS
WITH typed AS (
    SELECT
        upper(trim(account_id))                         AS account_id,
        trim(name)                                      AS name,
        lower(trim(industry))                           AS industry,
        TRY_CAST(employee_count AS INTEGER)             AS employee_count,
        TRY_CAST(annual_revenue_musd AS DOUBLE)         AS annual_revenue_musd,
        lower(trim(region))                             AS region,
        lower(trim(funding_stage))                      AS funding_stage,
        TRY_CAST(growth_rate_yoy AS DOUBLE)             AS growth_rate_yoy,
        TRY_CAST(hiring_velocity AS DOUBLE)             AS hiring_velocity,
        TRY_CAST(tech_stack_score AS DOUBLE)            AS tech_stack_score,
        TRY_CAST(founded_year AS INTEGER)               AS founded_year
    FROM raw_accounts
),
ranged AS (
    SELECT
        account_id, name, industry, employee_count,
        CASE WHEN annual_revenue_musd >= 0 THEN annual_revenue_musd END              AS annual_revenue_musd,
        region, funding_stage,
        CASE WHEN growth_rate_yoy BETWEEN -1 AND 2 THEN growth_rate_yoy END          AS growth_rate_yoy,
        CASE WHEN hiring_velocity BETWEEN 0 AND 1 THEN hiring_velocity END           AS hiring_velocity,
        tech_stack_score, founded_year
    FROM typed
),
valid AS (
    SELECT *, row_number() OVER (PARTITION BY account_id) AS rn
    FROM ranged
    WHERE account_id IS NOT NULL
      AND industry IN ({sql_list(INDUSTRIES)})
      AND region IN ({sql_list(REGIONS)})
      AND funding_stage IN ({sql_list(FUNDING_STAGES)})
      AND employee_count > 0
      AND tech_stack_score BETWEEN 0 AND 1
      AND founded_year BETWEEN 1900 AND year(current_date)
)
SELECT * EXCLUDE (rn) FROM valid WHERE rn = 1;  -- one row per account_id
"""

# 3. Deals: same idea, plus date logic. Open deals have no close_date
CLEAN_DEALS = f"""
CREATE OR REPLACE TABLE deals AS
WITH typed AS (
    SELECT
        upper(trim(deal_id))                AS deal_id,
        upper(trim(account_id))             AS account_id,
        TRY_CAST(created_date AS DATE)      AS created_date,
        TRY_CAST(close_date AS DATE)        AS close_date,
        lower(trim(status))                 AS status,
        TRY_CAST(amount AS DOUBLE)          AS amount,
        lower(trim(lead_source))            AS lead_source
    FROM raw_deals
),
valid AS (
    SELECT
        deal_id, account_id, created_date,
        CASE WHEN status = 'open' THEN NULL ELSE close_date END AS close_date,
        status, amount, lead_source,
        row_number() OVER (PARTITION BY deal_id ORDER BY created_date) AS rn
    FROM typed
    WHERE deal_id IS NOT NULL
      AND account_id IN (SELECT account_id FROM accounts)
      AND status IN ({sql_list(STATUSES)})
      AND lead_source IN ({sql_list(LEAD_SOURCES)})
      AND amount > 0
      AND created_date IS NOT NULL
      AND (status = 'open' OR close_date >= created_date)
)
SELECT * EXCLUDE (rn) FROM valid WHERE rn = 1;  -- one row per deal_id
"""

# 4. Events: remove exact duplicates and events for unknown accounts
CLEAN_EVENTS = f"""
CREATE OR REPLACE TABLE events AS
SELECT DISTINCT
    upper(trim(account_id))             AS account_id,
    TRY_CAST(event_date AS DATE)        AS event_date,
    lower(trim(event_type))             AS event_type
FROM raw_events
WHERE TRY_CAST(event_date AS DATE) IS NOT NULL
  AND lower(trim(event_type)) IN ({sql_list(EVENT_TYPES)})
  AND upper(trim(account_id)) IN (SELECT account_id FROM accounts)
ORDER BY account_id, event_date;
"""

# Checks that must all return 0 after cleaning
CHECKS = {
    "duplicate account_id": "SELECT count(*) - count(DISTINCT account_id) FROM accounts",
    "duplicate deal_id":    "SELECT count(*) - count(DISTINCT deal_id) FROM deals",
    "duplicate events":     "SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM events)) FROM events",
    "orphan deals":         "SELECT count(*) FROM deals WHERE account_id NOT IN (SELECT account_id FROM accounts)",
    "open deals with close_date": "SELECT count(*) FROM deals WHERE status = 'open' AND close_date IS NOT NULL",
}


def clean(db_path: Path = DB_PATH) -> dict:
    con = duckdb.connect(str(db_path))
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute(LOAD_RAW)
        con.execute(CLEAN_ACCOUNTS)
        con.execute(CLEAN_DEALS)
        con.execute(CLEAN_EVENTS)

        failed = {name: n for name, q in CHECKS.items() if (n := con.execute(q).fetchone()[0])}
        if failed:
            raise ValueError(f"Data checks failed, nothing was written: {failed}")

        report = {}
        for t in ["accounts", "deals", "events"]:
            raw = con.execute(f"SELECT count(*) FROM raw_{t}").fetchone()[0]
            kept = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            report[t] = {"raw": raw, "clean": kept, "removed": raw - kept}

        con.execute("COMMIT")
        return report
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    for table, r in clean().items():
        print(f"{table:<9} raw={r['raw']:>6}  clean={r['clean']:>6}  removed={r['removed']:>5}")
