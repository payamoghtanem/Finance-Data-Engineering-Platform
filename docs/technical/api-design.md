# API Design

**What this document answers:** exactly which endpoints exist, their request/response shape, authentication, and rate limits?
**How it differs from its neighbors:** `../requirements/FRD.md` FR-API-xxx states the API must be documented, versioned, authenticated, and must surface data quality; this document is that documentation.

## 1. Conventions

- Base path: `/v1/...` — a breaking change requires `/v2/...`, never an in-place breaking change to `/v1/...` (mirrors the data contract `change_policy` in `../architecture/solution-design-document.md` §4).
- All timestamps are ISO 8601 UTC.
- All monetary/price values are strings representing fixed-point decimals (never floating point) to avoid precision loss.
- Every response that includes a data value includes a `data_quality_status` field (FR-API-004).
- Authentication: `Authorization: Bearer <api_key>` header, required on every endpoint except `/v1/health`.
- Rate limiting: per-API-key, documented per endpoint; a `429` response includes a `Retry-After` header.

## 2. Endpoints

### `GET /v1/health`

Public, unauthenticated. Returns `{"status": "ok"}`. Used for uptime checks only — never returns data.

### `GET /v1/catalog/datasets`

List available datasets with metadata.

**Query params**: `domain` (macro|equity|fixed_income|trade|crypto|filings), `search`.

**Response** (200):
```json
{
  "datasets": [
    {
      "dataset_id": "fred_cpi_us",
      "domain": "macro",
      "source_id": "fred",
      "trust_tier": "official",
      "license_url": "https://...",
      "last_updated_at": "2026-01-15T22:00:00Z",
      "freshness_status": "ok"
    }
  ]
}
```

### `GET /v1/indicators/{indicator_id}`

Fetch an economic indicator's observations.

**Query params**: `geo_code`, `period_from`, `period_to`, `as_of` (point-in-time vintage selection, FR-API-002), `latest_only` (bool, default `false`).

**Response** (200):
```json
{
  "indicator_id": "cpi_us",
  "geo_code": "US",
  "unit": "index_1982_84_100",
  "seasonal_adjustment": "sa",
  "observations": [
    {
      "period": "2024-01",
      "value": "308.417",
      "vintage_date": "2024-02-13",
      "data_quality_status": "ok"
    }
  ]
}
```

**Errors**: `404` if `indicator_id` unknown; `400` if `as_of` is malformed.

### `GET /v1/instruments/{asset_class}/{symbol}/ohlcv`

Fetch OHLCV bars for an equity, ETF, index, or crypto instrument.

**Query params**: `interval` (1m|5m|1h|1d), `from`, `to`, `limit` (default 100, max 1000).

**Response** (200):
```json
{
  "instrument_id": "BTC",
  "asset_class": "crypto",
  "interval": "1d",
  "bars": [
    {
      "observed_at": "2026-01-15T00:00:00Z",
      "open": "42350.12000000",
      "high": "43100.00000000",
      "low": "42100.55000000",
      "close": "42980.30000000",
      "volume": "18234.56780000",
      "data_quality_status": "ok"
    }
  ]
}
```

**Errors**: `404` if instrument unknown; `422` if `interval` unsupported for that source (e.g., a free-tier source with daily-only granularity).

### `GET /v1/filings/{cik}`

Fetch corporate filing metadata (SEC EDGAR-backed).

**Query params**: `form_type`, `from`, `to`.

**Response** (200): list of filing records with `accession_number`, `form_type`, `filed_at`, `source_url`, and structured financial facts where available (XBRL-derived).

### `GET /v1/trade/observations`

**Query params**: `reporter`, `partner`, `commodity_code`, `period_from`, `period_to`.

**Response** (200): list of `fact_trade_observation` rows (see `data-model.md`).

### `POST /v1/agent/ask` (Phase 2+, gated feature)

Send a natural-language question to the scoped AI agent. See `../ai-agent/agentic-ai-design.md` for the full behavioral contract this endpoint must honor — this endpoint is a thin transport; it does not grant the agent any capability beyond what that document allows.

**Request**:
```json
{ "question": "Why does BTC's price look off on 2026-01-14?" }
```

**Response** (200):
```json
{
  "answer": "The 2026-01-14 close is flagged by the outlier-detection rule (>15% single-day move) and has not been confirmed invalid. Source: coingecko, retrieved 2026-01-15T00:05:00Z. Confidence: medium — this is a quality flag, not a confirmed error.",
  "sources": [{"source_id": "coingecko", "retrieved_at": "2026-01-15T00:05:00Z"}],
  "confidence": "medium",
  "action_taken": "none"
}
```

`action_taken` is always `"none"` or a description of a *read* action — this field exists specifically so a client can programmatically assert the agent never silently performed a write (see FR-AGENT-001).

## 3. Rate limits (Phase 1 defaults — tune per NFR-PERF-003 and upstream source limits)

| Endpoint group | Limit |
|---|---|
| `/v1/catalog/*`, `/v1/indicators/*`, `/v1/trade/*` | 60 requests/minute per API key |
| `/v1/instruments/*/ohlcv` | 60 requests/minute per API key |
| `/v1/filings/*` | 30 requests/minute per API key (mirrors SEC fair-access caution) |
| `/v1/agent/ask` | 10 requests/minute per API key (cost- and abuse-sensitive) |

## 4. Relationship to other documents

- Every field returned here has a canonical definition in `data-model.md` — do not introduce a response field that isn't backed by a documented column.
- Auth/rate-limit requirements are FR-API-003 in `../requirements/FRD.md`; latency targets are NFR-PERF-002 in `../requirements/NFR.md`.
- The `/v1/agent/ask` endpoint's behavior is governed by `../ai-agent/agentic-ai-design.md` — this file only defines its transport shape.
