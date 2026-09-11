#!/usr/bin/env python3
"""Provisions a Metabase dashboard over Gold (EPIC-10, US-10-001).

**Never run or verified against a live Metabase instance in this session**
-- there is no Docker daemon here, so `infra/docker-compose.yml`'s
`metabase` service has never actually started. This is written and
unit-tested against a fake HTTP transport (`tests/unit/
test_provision_metabase_gold_dashboard.py`), which proves the request
*shapes and ordering* this script would issue, and -- the one thing
directly testable without Metabase itself -- that the SQL it provisions
only ever touches `main_gold.fact_economic_kpi`, never Bronze or Silver
(US-10-001's actual requirement). It has not been exercised against a real
Metabase API, so treat the endpoint shapes below as a documented starting
point to adjust once Docker is available, not a guarantee.

**An open architecture question this script does not resolve**: Metabase's
official image ships no DuckDB driver, and Gold currently lives only in
DuckDB (EPIC-05) -- `docs/architecture/solution-design-document.md`'s flow
diagram shows Metabase reading through a combined "PostgreSQL cache +
Trino/DuckDB" serving layer, but no Gold-to-Postgres sync job exists in
code, and ADR before this one (ARD.md's serving-database row) reserves
PostgreSQL for metadata/job-state/fast API reads, "never for the full
historical OHLCV volume" -- which argues against caching all of Gold into
Postgres too. This script is deliberately engine-agnostic about that: it
takes the Metabase database connection's engine/details as parameters
rather than assuming one, and provisioning a real connection still needs
that open question resolved by whoever runs this against a live instance
(see STATUS.md's EPIC-10 entry / DEBT-11).

Usage (once Docker is available):

    METABASE_URL=http://localhost:3001 \\
    METABASE_ADMIN_USERNAME=... METABASE_ADMIN_PASSWORD=... \\
    python scripts/provision_metabase_gold_dashboard.py \\
        --database-name gold --database-engine postgres \\
        --database-details '{"host": "postgres", "port": 5432, "dbname": "finance_platform", ...}'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

# (method, path, json_body, headers) -> parsed JSON response.
Transport = Callable[[str, str, dict[str, Any] | None, dict[str, str]], dict[str, Any]]

_CARD_NAME = "Gold: Economic KPI (MoM/YoY)"
_DASHBOARD_NAME = "Economic Indicators (Gold)"
_GOLD_QUERY = (
    "SELECT indicator_id, geo_code, period, value, mom_pct_change, yoy_pct_change "
    "FROM main_gold.fact_economic_kpi ORDER BY period"
)


def _http_transport(
    method: str, path: str, json_body: dict[str, Any] | None, headers: dict[str, str]
) -> dict[str, Any]:
    data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    request = urllib.request.Request(  # noqa: S310 -- fixed base_url path, never user input
        path, data=data, method=method, headers={**headers, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Metabase API {method} {path} failed: {exc.code} {exc.read()!r}"
        ) from exc
    return dict(json.loads(body)) if body else {}


class MetabaseClient:
    """Thin wrapper over the subset of the Metabase API this script needs.

    A `transport` other than the real HTTP one can be injected for testing
    (see the module docstring on why this has never been run against a
    real Metabase instance).
    """

    def __init__(self, base_url: str, transport: Transport = _http_transport) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._session_token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"X-Metabase-Session": self._session_token} if self._session_token else {}

    def _call(self, method: str, path: str, json_body: dict[str, Any] | None = None) -> Any:
        return self._transport(method, f"{self._base_url}{path}", json_body, self._headers())

    def authenticate(self, username: str, password: str) -> None:
        response = self._call("POST", "/api/session", {"username": username, "password": password})
        self._session_token = str(response["id"])

    def _find_by_name(self, path: str, name: str) -> dict[str, Any] | None:
        response = self._call("GET", path)
        items = response["data"] if isinstance(response, dict) and "data" in response else response
        for item in items:
            if item.get("name") == name:
                return dict(item)
        return None

    def ensure_database(self, name: str, engine: str, details: dict[str, Any]) -> dict[str, Any]:
        """Find-or-create the Gold data source connection, by name."""
        existing = self._find_by_name("/api/database", name)
        if existing is not None:
            return existing
        return dict(
            self._call(
                "POST", "/api/database", {"name": name, "engine": engine, "details": details}
            )
        )

    def ensure_card(self, name: str, database_id: int, sql: str) -> dict[str, Any]:
        """Find-or-create the Gold-only SQL question (US-10-001: Gold, never Bronze/Silver)."""
        existing = self._find_by_name("/api/card", name)
        if existing is not None:
            return existing
        return dict(
            self._call(
                "POST",
                "/api/card",
                {
                    "name": name,
                    "display": "table",
                    "visualization_settings": {},
                    "dataset_query": {
                        "type": "native",
                        "native": {"query": sql},
                        "database": database_id,
                    },
                },
            )
        )

    def ensure_dashboard(self, name: str) -> dict[str, Any]:
        existing = self._find_by_name("/api/dashboard", name)
        if existing is not None:
            return existing
        return dict(self._call("POST", "/api/dashboard", {"name": name}))

    def ensure_card_on_dashboard(self, dashboard_id: int, card_id: int) -> None:
        dashboard = self._call("GET", f"/api/dashboard/{dashboard_id}")
        existing_cards = dashboard.get("dashcards", []) if isinstance(dashboard, dict) else []
        if any(dc.get("card_id") == card_id for dc in existing_cards):
            return
        self._call(
            "POST",
            f"/api/dashboard/{dashboard_id}/cards",
            {"cardId": card_id, "row": 0, "col": 0, "sizeX": 12, "sizeY": 8},
        )


def provision(
    client: MetabaseClient,
    *,
    database_name: str,
    database_engine: str,
    database_details: dict[str, Any],
) -> dict[str, Any]:
    """Ensure the Gold database connection, card, and dashboard all exist.

    Idempotent throughout: every step is find-or-create by name, so running
    this twice against the same Metabase instance never creates duplicates.
    """
    database = client.ensure_database(database_name, database_engine, database_details)
    card = client.ensure_card(_CARD_NAME, database_id=database["id"], sql=_GOLD_QUERY)
    dashboard = client.ensure_dashboard(_DASHBOARD_NAME)
    client.ensure_card_on_dashboard(dashboard_id=dashboard["id"], card_id=card["id"])
    return {"database": database, "card": card, "dashboard": dashboard}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.environ.get("METABASE_URL", "http://localhost:3001")
    )
    parser.add_argument("--database-name", default="gold")
    parser.add_argument("--database-engine", required=True)
    parser.add_argument("--database-details", required=True, help="JSON object")
    args = parser.parse_args()

    username = os.environ.get("METABASE_ADMIN_USERNAME")
    password = os.environ.get("METABASE_ADMIN_PASSWORD")
    if not username or not password:
        print(
            "METABASE_ADMIN_USERNAME / METABASE_ADMIN_PASSWORD must be set "
            "(never pass credentials on the command line -- NFR-SEC-003)",
            file=sys.stderr,
        )
        sys.exit(1)

    client = MetabaseClient(args.base_url)
    client.authenticate(username, password)
    result = provision(
        client,
        database_name=args.database_name,
        database_engine=args.database_engine,
        database_details=json.loads(args.database_details),
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
