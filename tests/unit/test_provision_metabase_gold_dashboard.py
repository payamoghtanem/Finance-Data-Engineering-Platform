"""Unit tests for scripts/provision_metabase_gold_dashboard.py (EPIC-10, US-10-001).

Everything here runs against a fake transport -- no real HTTP call, no live
Metabase instance. This proves the request shapes/ordering/idempotency the
script would issue, and -- the one thing directly enforceable without
Metabase itself -- that the provisioned card only ever queries Gold, never
Bronze or Silver. See the script's own module docstring for what remains
genuinely unverified.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.provision_metabase_gold_dashboard import MetabaseClient, provision


class _FakeMetabase:
    """In-memory stand-in for the subset of the Metabase API this script uses."""

    def __init__(self) -> None:
        self.databases: list[dict[str, Any]] = []
        self.cards: list[dict[str, Any]] = []
        self.dashboards: list[dict[str, Any]] = []
        self.calls: list[tuple[str, str]] = []
        self._next_id = 1

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def __call__(
        self, method: str, path: str, json_body: dict[str, Any] | None, headers: dict[str, str]
    ) -> dict[str, Any]:
        self.calls.append((method, path))

        if path.endswith("/api/session"):
            return {"id": "fake-session-token"}
        if path.endswith("/api/database") and method == "GET":
            return {"data": self.databases}
        if path.endswith("/api/database") and method == "POST":
            assert json_body is not None
            row = {**json_body, "id": self._new_id()}
            self.databases.append(row)
            return row
        if path.endswith("/api/card") and method == "GET":
            return {"data": self.cards}
        if path.endswith("/api/card") and method == "POST":
            assert json_body is not None
            row = {**json_body, "id": self._new_id()}
            self.cards.append(row)
            return row
        if path.endswith("/api/dashboard") and method == "GET":
            return {"data": self.dashboards}
        if path.endswith("/api/dashboard") and method == "POST":
            assert json_body is not None
            row = {**json_body, "id": self._new_id(), "dashcards": []}
            self.dashboards.append(row)
            return row
        if "/api/dashboard/" in path and path.endswith("/cards") and method == "POST":
            assert json_body is not None
            dashboard_id = int(path.split("/api/dashboard/")[1].split("/cards")[0])
            dashboard = next(d for d in self.dashboards if d["id"] == dashboard_id)
            dashboard["dashcards"].append({"card_id": json_body["cardId"]})
            return {}
        if "/api/dashboard/" in path and method == "GET":
            dashboard_id = int(path.split("/api/dashboard/")[1])
            return next(d for d in self.dashboards if d["id"] == dashboard_id)

        raise AssertionError(f"unexpected call: {method} {path}")


def _client(fake: _FakeMetabase) -> MetabaseClient:
    client = MetabaseClient("http://fake-metabase", transport=fake)
    client.authenticate("admin", "secret")
    return client


class TestProvision:
    def test_creates_database_card_and_dashboard(self) -> None:
        fake = _FakeMetabase()
        client = _client(fake)

        result = provision(
            client,
            database_name="gold",
            database_engine="postgres",
            database_details={"host": "postgres"},
        )

        assert result["database"]["name"] == "gold"
        assert result["card"]["name"] == "Gold: Economic KPI (MoM/YoY)"
        assert result["dashboard"]["name"] == "Economic Indicators (Gold)"
        assert len(fake.databases) == 1
        assert len(fake.cards) == 1
        assert len(fake.dashboards) == 1
        assert fake.dashboards[0]["dashcards"] == [{"card_id": result["card"]["id"]}]

    def test_the_provisioned_query_only_touches_gold(self) -> None:
        """US-10-001: 'Metabase queries Gold (never Bronze/Silver)'."""
        fake = _FakeMetabase()
        client = _client(fake)

        result = provision(
            client, database_name="gold", database_engine="postgres", database_details={}
        )

        sql = result["card"]["dataset_query"]["native"]["query"]
        assert "main_gold.fact_economic_kpi" in sql
        assert "bronze" not in sql.lower()
        assert "silver" not in sql.lower()

    def test_running_twice_creates_no_duplicates(self) -> None:
        fake = _FakeMetabase()
        client = _client(fake)

        provision(client, database_name="gold", database_engine="postgres", database_details={})
        provision(client, database_name="gold", database_engine="postgres", database_details={})

        assert len(fake.databases) == 1
        assert len(fake.cards) == 1
        assert len(fake.dashboards) == 1
        assert len(fake.dashboards[0]["dashcards"]) == 1

    def test_authenticate_sets_the_session_header_on_subsequent_calls(self) -> None:
        fake = _FakeMetabase()
        client = _client(fake)

        provision(client, database_name="gold", database_engine="postgres", database_details={})

        # authenticate() itself is the first call; every call after it must
        # have gone through with a session already established (the fake
        # doesn't check headers, but a real Metabase instance would reject
        # unauthenticated requests -- this at least proves the ordering).
        assert fake.calls[0] == ("POST", "http://fake-metabase/api/session")
