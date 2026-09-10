# FRED Connector

**Owner:** `connectors.fred`  
**Purpose:** Ingest economic indicator data from Federal Reserve Economic Data (FRED) API  
**Trust Tier:** 1 (Official statistical/regulatory body)  
**License:** Public domain (U.S. government work)

## Data Contract

See `contract.yaml` for the full data contract specification.

## Supported Series

| Series ID | Title | Frequency | Units |
|-----------|-------|-----------|-------|
| CPIAUCSL | Consumer Price Index for All Urban Consumers | Monthly | Index 1982-1984=100 |

Add more series by updating the contract and orchestration configuration.

## Requirements

- FRED API key (free, obtainable from https://fred.stlouisfed.org/docs/api/api_key.html)
- Internet access to `api.stlouisfed.org`

## Usage

```python
from src.connectors.fred import FREDConnector
from src.common.config import PlatformConfig

# Load config from environment
config = PlatformConfig.from_env()

# Create connector
connector = FREDConnector.from_config(config)

# Run ingestion for CPI series
result = connector.run_ingestion(series_id="CPIAUCSL")
print(f"Ingestion completed: {result}")
```

## Retry Behavior

Per FR-ING-001 and docs/technical/technical-design-document.md §3:

- Retries up to 3 times on transient errors (5xx, timeout, connection reset)
- Uses exponential backoff: 2s, 4s, 8s
- Respects `Retry-After` header on 429 responses
- Does NOT retry on 4xx errors (except 429)

## Events Emitted

- `ingestion.started` - When ingestion begins
- `raw_data.received` - When raw response is stored (includes SHA-256 hash)
- `ingestion.completed` - When ingestion succeeds

On failure:
- `ingestion.failed` - When all retries are exhausted

## Testing

```bash
# Unit tests
pytest tests/unit/test_fred_connector.py

# Integration test (requires docker-compose up and valid API key)
pytest tests/integration/test_fred_integration.py -m integration
```

## Troubleshooting

### 403 Forbidden
- Verify your FRED API key is correct and active
- Check that your User-Agent header identifies your application

### 429 Too Many Requests
- The connector automatically respects rate limits
- If persistent, consider reducing ingestion frequency

### 500 Server Error
- The connector will automatically retry
- If persistent, check FRED service status at https://fred.stlouisfed.org/
