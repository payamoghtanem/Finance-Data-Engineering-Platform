# Data Model

**What this document answers:** exactly which tables exist, in which layer, with which columns, keys, and types?
**How it differs from its neighbors:** `../architecture/ARD.md` says "Bronze/Silver/Gold on a Lakehouse"; this document is the literal schema that instantiates that pattern.

## 1. Layer summary

| Layer | Storage | Format | Mutability |
|---|---|---|---|
| Raw | Object storage (`MinIO`/S3) | Original bytes (JSON/CSV/XML) + metadata sidecar | Immutable, append-only |
| Bronze | Iceberg tables on object storage | Parquet | Append-only (new snapshots on change) |
| Silver | Iceberg tables on object storage | Parquet | Upsert via merge, keyed by primary key |
| Gold | Iceberg tables (+ PostgreSQL cache for low-latency serving) | Parquet / relational | Upsert, business-key based |

## 2. Dimension tables

### `dim_source`

| Column | Type | Notes |
|---|---|---|
| `source_id` | string (PK) | e.g., `fred`, `worldbank`, `eurostat`, `sec_edgar`, `coingecko` |
| `publisher` | string | Actual publishing entity, e.g., "Federal Reserve Bank of St. Louis" |
| `license_url` | string | Link to the source's license/terms of use |
| `terms_version` | string | Version/date of the terms captured |
| `redistribution_allowed` | boolean | Whether storage + redistribution is permitted |
| `attribution_text` | string | Required attribution text, if any |
| `trust_tier` | enum(`official`, `licensed_commercial`, `reputable_media_analytics`, `community_unofficial`) | See `../00-glossary.md` |
| `rate_limit_notes` | string | Documented API rate limits |
| `source_retrieved_at` | timestamp | When this catalog entry was last verified against the source's actual terms |

### `dim_dataset`

| Column | Type | Notes |
|---|---|---|
| `dataset_id` | string (PK) | e.g., `fred_cpi_us`, `coingecko_market_daily` |
| `source_id` | string (FK → `dim_source`) | |
| `frequency` | enum(`realtime`,`daily`,`weekly`,`monthly`,`quarterly`,`annual`) | |
| `update_policy` | string | How/when the dataset is refreshed |
| `owner` | string | Domain owner (see `../architecture/ARD.md` §4.3 Data Mesh discussion) |
| `contract_version` | string | Current data contract version (see `../architecture/solution-design-document.md` §4) |

### `dim_instrument`

| Column | Type | Notes |
|---|---|---|
| `instrument_id` | string (PK) | Internal stable identifier |
| `symbol` | string | Ticker/trading symbol |
| `isin` | string, nullable | International Securities Identification Number, where known |
| `asset_class` | enum(`equity`,`etf`,`index`,`fx`,`crypto`,`bond`) | |
| `exchange_code` | string, nullable | |

### `dim_indicator`

| Column | Type | Notes |
|---|---|---|
| `indicator_id` | string (PK) | e.g., `cpi_us`, `hicp_eurozone` |
| `name` | string | Human-readable name |
| `unit` | string | e.g., `index_1982_84_100`, `percent` |
| `seasonal_adjustment` | enum(`sa`,`nsa`,`unknown`) | Must never be `unknown` in Silver/Gold (FR-QUAL-009) |
| `methodology_url` | string | Link to the publishing agency's methodology documentation |

## 3. Fact tables

### `fact_market_ohlcv` (Silver/Gold)

| Column | Type | Notes |
|---|---|---|
| `source_id` | string (FK) | Part of primary key |
| `instrument_id` | string (FK) | Part of primary key |
| `interval` | enum(`1m`,`5m`,`1h`,`1d`) | Part of primary key |
| `observed_at` | timestamp (UTC) | Part of primary key |
| `open`, `high`, `low`, `close` | decimal(20,8) | |
| `volume` | decimal(28,8) | Must be ≥ 0 (FR-QUAL-005) |
| `data_quality_status` | enum(`ok`,`flagged`,`quarantined`) | Surfaced to API consumers (FR-API-004) |

Primary key: `(source_id, instrument_id, interval, observed_at)` — matches the sample data contract in `../architecture/solution-design-document.md` §4.

### `fact_economic_observation` (Silver/Gold)

| Column | Type | Notes |
|---|---|---|
| `indicator_id` | string (FK) | Part of primary key |
| `geo_code` | string | ISO country/region code; part of primary key |
| `period` | string | e.g., `2024-01` for monthly; part of primary key |
| `period_start` / `period_end` | date | First/last calendar day the `period` label covers — kept as literal columns, never derived from `period` at query time (FR-MODEL-002) |
| `vintage_date` | date | The revision date of this value; part of primary key |
| `value` | decimal(28,8) | |
| `unit` | string | Denormalized from `dim_indicator` for query convenience |
| `published_at` | timestamp, nullable | When the source officially released this value. Nullable because not every source's ingestion exposes this distinct from `vintage_date`/`retrieved_at` — see the model's own docs (`../../src/transform/dbt_project/models/silver/schema.yml`) before assuming it's populated |
| `retrieved_at` | timestamp | When the connector fetched the payload this row was conformed from — copied from Bronze, never recomputed |
| `processed_at` | timestamp | When the Silver transform that produced this row ran — distinct from `retrieved_at` by construction (EPIC-05) |

Primary key: `(indicator_id, geo_code, period, vintage_date)` — this is what makes point-in-time queries (FR-API-002) correct: querying `as_of` a date selects the newest `vintage_date` that is ≤ that date.

This table's six time fields (`observed_at`'s role is split into `period_start`/`period_end` for period-based indicators — see `../00-glossary.md`) must never collapse into one another; `../../src/transform/dbt_project/tests/assert_fact_economic_observation_time_fields_distinct.sql` enforces this per FR-MODEL-002.

### `fact_trade_observation` (Silver/Gold)

| Column | Type | Notes |
|---|---|---|
| `reporter` | string | Reporting country/entity; part of primary key |
| `partner` | string | Trade partner country; part of primary key |
| `commodity_code` | string | Harmonized System (HS) code or equivalent; part of primary key |
| `period` | string | Part of primary key |
| `trade_value` | decimal(28,2) | |
| `trade_flow` | enum(`import`,`export`) | |

### `fact_crypto_market` (Silver/Gold)

| Column | Type | Notes |
|---|---|---|
| `asset_id` | string (FK → `dim_instrument`) | Part of primary key |
| `observed_at` | timestamp (UTC) | Part of primary key |
| `price` | decimal(28,10) | |
| `market_cap` | decimal(28,2) | |
| `volume_24h` | decimal(28,2) | |
| `data_quality_status` | enum(`ok`,`flagged`,`quarantined`) | |

## 4. Operational tables

### `ingestion_run`

| Column | Type | Notes |
|---|---|---|
| `run_id` | string (PK) | |
| `dataset_id` | string (FK → `dim_dataset`) | |
| `connector_version` | string | Code version that executed the run |
| `started_at` / `finished_at` | timestamp | |
| `status` | enum(`success`,`failed`,`partial`,`quarantined`) | |
| `request_hash` | string | Hash of the exact request made, for provenance/reproducibility |
| `retry_count` | integer | |
| `raw_storage_path` | string | Pointer into Raw Object Storage for this run's response(s) |

### `data_quality_result`

| Column | Type | Notes |
|---|---|---|
| `test_id` | string (PK, part of) | Identifies the specific quality rule, e.g., `nonnegative_volume` |
| `table_name` | string | Part of primary key |
| `run_id` | string (FK → `ingestion_run`) | |
| `status` | enum(`pass`,`fail`,`warn`) | |
| `failed_rows` | integer | |
| `evaluated_at` | timestamp | |

## 5. Time-field discipline (see `../00-glossary.md` and FR-MODEL-002)

No fact table collapses time into a single `date` column. At minimum: `observed_at` (or `period` for indicators) is kept distinct from `published_at`, `retrieved_at`, `processed_at`, and (for revisable series) `vintage_date`. This is what makes `fact_economic_observation`'s primary key include `vintage_date` rather than overwriting history on every revision.

## 6. Relationship to other documents

- License/trust metadata in `dim_source` is populated from `../data-sources/catalog.md` — that document is the source of truth for *which* sources exist and their terms; this table is where that information is queryable by the pipeline and API.
- `data_quality_result` rows are produced by the FR-QUAL-xxx requirements in `../requirements/FRD.md`.
- Every column here that appears in an API response is documented again, in response-shape form, in `api-design.md` — don't let the two drift; if a column is renamed here, rename it there in the same change.
