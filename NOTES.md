# Engineering Notes & Architectural Decisions (`NOTES.md`)

This document outlines the design decisions, data cleaning rationale, API architecture, and scalability analysis for the Coffee Health Take-Home project.

---

## 1. Database Schema Design

The schema is defined in [`db/init/002_coffee_records.sql`](file:///db/init/002_coffee_records.sql).

### Table: `public.coffee_records`

| Column | PostgreSQL Type | Constraints & Defaults | Design Rationale |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY` | Natural unique identifier for participants. |
| `age` | `SMALLINT` | `NOT NULL CHECK (age >= 18 AND age <= 120)` | `SMALLINT` saves 2 bytes per row over `INTEGER`. Constrained to adult biological limits. |
| `gender` | `VARCHAR(16)` | `NOT NULL CHECK (gender IN ('Male', 'Female', 'Other'))` | Canonical gender values. |
| `country` | `VARCHAR(64)` | `NOT NULL` | Standardized country name. |
| `coffee_intake` | `NUMERIC(4, 2)` | `NOT NULL CHECK (coffee_intake >= 0 AND coffee_intake <= 25)` | Exact decimal representation for daily cups (prevents floating-point precision drift). |
| `caffeine_mg` | `NUMERIC(6, 2)` | `NOT NULL CHECK (caffeine_mg >= 0 AND caffeine_mg <= 3000)` | Accurate milligram tracking up to lethal threshold. |
| `sleep_hours` | `NUMERIC(4, 2)` | `NOT NULL CHECK (sleep_hours >= 0 AND sleep_hours <= 24)` | Hours per night cannot exceed 24. |
| `sleep_quality` | `VARCHAR(16)` | `NOT NULL CHECK (sleep_quality IN ('Poor', 'Fair', 'Good', 'Excellent'))` | Validated categorical classification. |
| `bmi` | `NUMERIC(5, 2)` | `NOT NULL CHECK (bmi >= 10 AND bmi <= 70)` | Plausible human Body Mass Index bounds. |
| `heart_rate` | `SMALLINT` | `NOT NULL CHECK (heart_rate >= 35 AND heart_rate <= 220)` | Resting heart rate in beats per minute. |
| `stress_level` | `VARCHAR(16)` | `NOT NULL CHECK (stress_level IN ('Low', 'Medium', 'High'))` | Validated stress category. |
| `physical_activity_hours` | `NUMERIC(5, 2)` | `NOT NULL CHECK (physical_activity_hours >= 0 AND physical_activity_hours <= 168)` | Hours per week (max 168 hours in a 7-day week). |
| `health_issues` | `VARCHAR(16)` | `NOT NULL CHECK (health_issues IN ('None', 'Mild', 'Moderate', 'Severe'))` | Validated health status. |
| `occupation` | `VARCHAR(32)` | `NOT NULL CHECK (occupation IN ('Office', 'Healthcare', 'Service', 'Student', 'Other'))` | Validated job category. |
| `smoking` | `BOOLEAN` | `NOT NULL` | Native 1-byte boolean flag. |
| `alcohol_consumption` | `BOOLEAN` | `NOT NULL` | Native 1-byte boolean flag. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | Record ingestion audit timestamp. |

### Indexing Strategy
- `idx_coffee_country` on `(country)`: Accelerates country exact-match and multi-select filters.
- `idx_coffee_gender` on `(gender)`: Speeds up demographic grouping.
- `idx_coffee_stress_sleep` on `(stress_level, sleep_quality)`: Composite index targeting high-frequency correlated health filters.
- `idx_coffee_age` on `(age)` and `idx_coffee_intake` on `(coffee_intake)`: B-tree indexes supporting range scans (`min_age`, `max_age`, `min_coffee_intake`, `max_coffee_intake`).

---

## 2. Data Cleaning, Validation & Ingestion Pipeline

The pipeline is implemented across [`scripts/data_cleaner.py`](file:///scripts/data_cleaner.py) and [`scripts/load_data.py`](file:///scripts/load_data.py).

### Ingestion Results Breakdown
- **Total rows read from CSV:** `10,012`
- **Rows newly loaded into DB:** `9,975`
- **Rows normalized / fixed:** `31`
- **Rows rejected (corrupt/invalid):** `25`
- **Duplicate IDs identified:** `12`
  - *Exact duplicates (identical data):* `8`
  - *Conflicting duplicates (different data):* `4`
- **Accountability check:** $9{,}975 \text{ (loaded)} + 25 \text{ (rejected)} + 8 \text{ (exact dup)} + 4 \text{ (conflict dup)} = 10{,}012 \text{ rows} \ (100.0\%)$.

### Cleaning & Normalization Logic
1. **UTF-8 with BOM Handling:** The raw CSV begins with `\ufeffID`. Handled by opening the stream with `encoding="utf-8-sig"`.
2. **Whitespace and Casing:** Trailing whitespace, tabs (`\t`), and capitalization inconsistencies (`\tUSA `, `SWEDEN`, `belgium`, `LOW`, `Good  `) are stripped and canonicalized into standard title/uppercase/enums.
3. **Boolean Parsing:** Strings such as `"yes"`, `"no"`, `"true"`, `"false"`, `"y"`, `"n"`, `"1"`, `"0"` are normalized to native Python `bool`. Arbitrary values like `"-1"` or `"2"` are rejected.
4. **Duplicate ID Strategy:**
   - **Exact duplicates (e.g. IDs 555, 620, 4654, 4729, 5458, 5989, 6049, 8789):** The first occurrence is loaded; subsequent identical occurrences are marked as `exact_duplicates` and skipped.
   - **Conflicting duplicates (e.g. IDs 3338, 6115, 6748, 7494):** Different demographic/health data for the same ID indicates an ambiguous source anomaly. To protect clinical/health data integrity, we preserve the initial record and reject the conflicting record with a clear audit log reason.
   - **Idempotency:** The database query uses `ON CONFLICT (id) DO NOTHING`. Running `make load` multiple times inserts 0 new rows and keeps the total count at 9,975.

### Explanation of Rejected Rows (25 invalid rows):
- **Malformed CSV Columns (3 rows):**
  - Line 2659: Extra unexpected column in row.
  - Lines 4869 & 7174: Row ends prematurely, missing `Occupation`, `Smoking`, and `Alcohol_Consumption`.
- **Missing / Blank Required Fields (8 rows):**
  - Line 1154: Empty `Age`.
  - Line 1809: Empty `Sleep_Hours`.
  - Line 3240: `Age = 'unknown'`.
  - Line 3517: Empty `Gender`.
  - Line 4128: `Gender = '?'`.
  - Line 4380: `Gender = 'N/A'`.
  - Line 4880: Empty `BMI`.
  - Line 6987: Empty `Heart_Rate`.
  - Line 7901: `BMI = 'n/a'`.
- **Textual Typos & Words in Numeric Fields (3 rows):**
  - Line 816: `Age = 'thirty'`.
  - Line 1918: `Age = '4O'` (letter O typo for zero).
  - Line 7088: `Sleep_Hours = 'seven'`.
  *(Rejected to maintain strict mathematical parsing rather than guessing natural language variants).*
- **Physically Impossible Out-of-Range Bounds (8 rows):**
  - Lines 1114 & 2128: `Age` is 212 and 150 (exceeds human life expectancy).
  - Line 6605: `Age = -3` (negative age).
  - Line 107: `Sleep_Hours = -1.0` (negative sleep).
  - Line 3187: `Sleep_Hours = 25.0` (exceeds hours in a day).
  - Lines 5894 & 9871: `Heart_Rate` is 0 and 350 bpm.
  - Line 6802: `BMI = 0.0` (biologically impossible).
- **Invalid Boolean Codes (2 rows):**
  - Lines 3388 & 8225: `Smoking` is `-1` and `2`.

---

## 3. Filtering & Pagination Strategy

Implemented in [`app/routers/records.py`](file:///app/routers/records.py) and [`app/repositories/coffee_repository.py`](file:///app/repositories/coffee_repository.py).

### Endpoints
1. `GET /records`:
   - Supports multi-select list filters (`country`, `gender`, `sleep_quality`, `stress_level`, `occupation`, `health_issues`).
   - Supports numeric range filters (`min_age`, `max_age`, `min_coffee_intake`, `max_coffee_intake`, `min_bmi`, `max_bmi`, `min_sleep_hours`, `max_sleep_hours`).
   - Supports boolean flags (`smoking`, `alcohol_consumption`).
   - **Range Validation:** A Pydantic `@model_validator` asserts `min_* <= max_*`. Returns HTTP `422 Unprocessable Content` if violated.
   - **Pagination:** Offset/limit with metadata (`total`, `page`, `page_size`, `total_pages`, `has_next`, `has_previous`). Maximum page size capped at 100.
2. `GET /records/summary`:
   - Analytical endpoint providing aggregated health metrics (`avg_sleep_hours`, `avg_caffeine_mg`, `avg_bmi`, `avg_coffee_intake`, and `record_count`) grouped by `country`, `sleep_quality`, `stress_level`, `occupation`, or `gender`.
   - Aggregations are calculated natively in PostgreSQL using indexed grouping for high performance.
3. `GET /records/{record_id}`:
   - Fetches individual participant record by primary key; returns HTTP `404` if not found.

---

## 4. Scalability & Performance Analysis (Part 4)

### 1. Memory Efficiency & Streaming Large Files
- **Current implementation:** The loader operates as a generator pipeline (`process_csv` yields records on-the-fly and `chunked` groups them into batches of 1,000).
- **RAM footprint:** Independent of file size. Memory usage is $\mathcal{O}(\text{batch\_size})$ rather than $\mathcal{O}(N)$. A 50 GB CSV with 100 million records can be processed with under 100 MB of heap memory.
- **Throughput optimization:** For tens of millions of rows, replacing `cur.executemany` with `psycopg`'s native streaming `cursor.copy("COPY coffee_records FROM STDIN")` achieves $50{,}000\text{–}100{,}000 \text{ rows/sec}$, loading 10 million rows in under 2 minutes.

### 2. Index Design vs. Write Amplification
- **Index Cost:** Every B-tree index added incurs write amplification during inserts and increases WAL (Write-Ahead Logging) volume.
- **Bulk Ingestion Strategy at Scale:** When loading initial datasets of 10M+ rows, best practice is to:
  1. Drop secondary indexes prior to loading.
  2. Execute streaming `COPY`.
  3. Recreate indexes in parallel with `CREATE INDEX CONCURRENTLY`.
- **Query Indexes:** In production, composite indexes should match specific query patterns (e.g. `(country, stress_level, sleep_quality)`). Partial indexes (e.g. `WHERE smoking IS TRUE`) can further reduce index size by indexing only relevant subsets.

### 3. Deep Pagination (Page 1 vs. Page 50,000)
- **The Problem with `OFFSET / LIMIT`:** On page 50,000 with a page size of 20, PostgreSQL must scan 1,000,000 index entries and discard 999,980 rows before returning 20 records ($\mathcal{O}(N)$ complexity).
- **Production Solution — Keyset (Cursor-based) Pagination:**
  - Instead of `OFFSET 1000000 LIMIT 20`, queries utilize an indexed tuple comparison:
    ```sql
    SELECT * FROM coffee_records
    WHERE (created_at, id) < (%(cursor_timestamp)s, %(cursor_id)s)
    ORDER BY created_at DESC, id DESC
    LIMIT 20;
    ```
  - Keyset pagination runs in constant time $\mathcal{O}(1)$ via B-tree index lookups regardless of whether browsing page 1 or page 50,000.

### 4. Database Connection Pool Under Concurrent Load
- **Pool Management:** The API uses `psycopg_pool.ConnectionPool` with bounded connections (`min_size=1`, `max_size=10`).
- **Connection Borrowing:** FastAPI's `Depends(get_conn)` borrows a connection strictly during request execution and returns it to the pool upon completion via context managers.
- **Handling High Concurrency:** Under heavy load, increasing application processes can exhaust PostgreSQL's max connections. The production architecture introduces an intermediate connection pooler (**PgBouncer**) in transaction pooling mode (`pool_mode = transaction`). This multiplexes thousands of incoming HTTP requests across a lean pool of 20–50 actual PostgreSQL backend processes with minimal RAM and context-switching overhead.
