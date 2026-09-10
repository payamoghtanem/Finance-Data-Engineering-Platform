#!/usr/bin/env python3
"""Automated acceptance check for EPIC-05's Silver/Gold dbt project.

This is the "verified by an automated test" half of two EPIC-02 stories that
EPIC-05 was built to unblock (docs/backlog/user-stories.md):

  US-02-004 (idempotent re-run): running `dbt build` twice against identical
  Bronze data must not change fact_economic_observation's row count -- a
  backfill can't double-count.

  US-02-006 (vintage awareness): a later revision of an already-ingested
  period must land as an ADDITIONAL row (distinct vintage_date), never an
  overwrite -- the prior vintage must remain queryable -- and Gold's KPI
  model must pick the latest vintage.

Seeds synthetic Bronze data through the real RawStorage/BronzeWriter code
path (never hand-crafts a Bronze row), then drives `dbt build` via
subprocess exactly as a human or CI would. Used by CI's dbt-transform job;
runnable the same way locally.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from src.bronze.writer import BronzeWriter
from src.common.raw_storage import LocalRawStorage, build_object_key, compute_sha256

_INITIAL_PAYLOAD = {
    "realtime_start": "2024-02-01",
    "realtime_end": "2024-02-01",
    "observations": [
        {"realtime_start": "2024-02-01", "date": "2023-11-01", "value": "307.671"},
        {"realtime_start": "2024-02-01", "date": "2023-12-01", "value": "306.746"},
        {"realtime_start": "2024-02-01", "date": "2024-01-01", "value": "308.417"},
    ],
}

# A later revision of the same November value -- FRED's realtime_start moves
# forward, which is what should make this a NEW vintage row, not an overwrite.
_REVISION_PAYLOAD = {
    "realtime_start": "2024-03-01",
    "realtime_end": "2024-03-01",
    "observations": [
        {"realtime_start": "2024-03-01", "date": "2023-11-01", "value": "307.900"},
    ],
}


def _seed(
    raw_store: str, bronze_db: str, payload: Mapping[str, object], retrieved_at: datetime
) -> None:
    raw_bytes = json.dumps(payload).encode("utf-8")
    raw_storage = LocalRawStorage(raw_store)
    sha256 = compute_sha256(raw_bytes)
    key = build_object_key("fred", "CPIAUCSL", retrieved_at, sha256)
    raw_storage.put(key, raw_bytes)
    writer = BronzeWriter(raw_storage, db_path=bronze_db)
    try:
        writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key=key,
            raw_sha256=sha256,
            retrieved_at=retrieved_at,
            code_version="0.0.0-ci-fixture",
        )
    finally:
        writer.close()


def _dbt_build(project_dir: str, profiles_dir: str) -> None:
    dbt_executable = shutil.which("dbt")
    if dbt_executable is None:
        raise RuntimeError("dbt is not on PATH -- install the 'transform' extra (pyproject.toml)")
    # Fixed argv built from this script's own argparse defaults/flags, never
    # from unsanitized external input -- a full resolved path replaces the
    # bare "dbt" name so this isn't a partial-executable-path lookup either.
    subprocess.run(  # noqa: S603
        [dbt_executable, "build", "--project-dir", project_dir, "--profiles-dir", profiles_dir],
        check=True,
    )


def _silver_rows(transform_db: str) -> list[tuple[object, ...]]:
    con = duckdb.connect(transform_db, read_only=True)
    try:
        return con.execute(
            "SELECT period, vintage_date, value FROM main_silver.fact_economic_observation "
            "ORDER BY period, vintage_date"
        ).fetchall()
    finally:
        con.close()


def _kpi_value(transform_db: str, period: str) -> float | None:
    con = duckdb.connect(transform_db, read_only=True)
    try:
        row = con.execute(
            "SELECT value FROM main_gold.fact_economic_kpi WHERE period = ?", [period]
        ).fetchone()
        return float(row[0]) if row else None
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", default="raw_store")
    parser.add_argument("--bronze-db", default="bronze_store/bronze.duckdb")
    parser.add_argument("--transform-db", default="transform_store/transform.duckdb")
    parser.add_argument("--project-dir", default="src/transform/dbt_project")
    parser.add_argument("--profiles-dir", default="src/transform/dbt_project")
    args = parser.parse_args()

    Path(args.transform_db).parent.mkdir(parents=True, exist_ok=True)

    _seed(args.raw_store, args.bronze_db, _INITIAL_PAYLOAD, datetime(2024, 2, 1, 9, 0, tzinfo=UTC))
    _dbt_build(args.project_dir, args.profiles_dir)
    rows_first = _silver_rows(args.transform_db)
    print(f"After first build: {len(rows_first)} Silver rows")

    _dbt_build(args.project_dir, args.profiles_dir)
    rows_second = _silver_rows(args.transform_db)
    print(f"After identical re-run: {len(rows_second)} Silver rows")
    if rows_first != rows_second:
        print(
            "FAIL (US-02-004): re-running dbt build against identical Bronze data "
            "changed Silver's rows -- a backfill would double-count",
            file=sys.stderr,
        )
        sys.exit(1)

    _seed(args.raw_store, args.bronze_db, _REVISION_PAYLOAD, datetime(2024, 3, 1, 9, 0, tzinfo=UTC))
    _dbt_build(args.project_dir, args.profiles_dir)
    rows_third = _silver_rows(args.transform_db)
    nov_vintages = [row for row in rows_third if row[0] == "2023-11"]
    print(f"After a later revision: {len(nov_vintages)} vintage(s) for 2023-11: {nov_vintages}")
    if len(nov_vintages) != 2:
        print(
            f"FAIL (US-02-006): expected 2 vintages for 2023-11 (prior still queryable "
            f"+ new revision), got {len(nov_vintages)}",
            file=sys.stderr,
        )
        sys.exit(1)

    kpi_value = _kpi_value(args.transform_db, "2023-11")
    if kpi_value is None or kpi_value != 307.9:
        print(
            f"FAIL (US-02-006): Gold's KPI model should select the latest vintage "
            f"(307.9) for 2023-11, got {kpi_value}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "PASS: US-02-004 (idempotent re-run) and US-02-006 (vintage awareness) "
        "both verified against real Bronze data."
    )


if __name__ == "__main__":
    main()
