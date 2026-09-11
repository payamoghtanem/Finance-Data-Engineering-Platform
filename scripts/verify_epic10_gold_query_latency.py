#!/usr/bin/env python3
"""Automated latency check for EPIC-10 / NFR-PERF-001.

NFR-PERF-001: "Typical Gold-layer dashboard query latency < 5 seconds."
US-10-001 (EPIC-10): "Metabase queries Gold, never Bronze/Silver; p50 < 5s."

This proves the query-latency *mechanism*, not the full production metric:
it seeds a small, synthetic multi-year fixture through the real
RawStorage/BronzeWriter/dbt path (same discipline as
verify_epic05_acceptance.py), runs `dbt build`, then times the same
representative "Gold dashboard" query Metabase would issue against
`fact_economic_kpi` (never Bronze/Silver) repeatedly and checks the median
latency against NFR-PERF-001's 5-second target.

**Honest scope limit**: this is a synthetic fixture on a laptop-sized
DuckDB file, not real production data volumes (no capacity model exists yet
-- see STATUS.md's DEBT-03) and it measures only the SQL query itself, not
Metabase's own dashboard-rendering overhead on top of it (untestable
without a live Metabase instance -- see STATUS.md's EPIC-10 entry). What
this *does* prove: the query shape a Gold dashboard would use is fast
against DuckDB by construction, and never touches Bronze or Silver.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from src.bronze.writer import BronzeWriter
from src.common.raw_storage import LocalRawStorage, build_object_key, compute_sha256

# Two years of monthly observations -- enough for the KPI model's MoM/YoY
# lag windows to produce real (non-null) values, still tiny by design: this
# checks the query shape, not throughput at scale (see module docstring).
_PERIODS = [(2022, m) for m in range(1, 13)] + [(2023, m) for m in range(1, 13)] + [(2024, 1)]
_OBSERVATIONS = [
    {"realtime_start": "2024-01-01", "date": f"{year}-{month:02d}-01", "value": f"{300 + i}.0"}
    for i, (year, month) in enumerate(_PERIODS)
]
_PAYLOAD = {
    "realtime_start": "2024-01-01",
    "realtime_end": "2024-01-01",
    "observations": _OBSERVATIONS,
}

_QUERY = """
    SELECT indicator_id, geo_code, period, value, mom_pct_change, yoy_pct_change
    FROM main_gold.fact_economic_kpi
    ORDER BY period
"""

_REPEATS = 20
_NFR_PERF_001_TARGET_SECONDS = 5.0


def _seed(raw_store: str, bronze_db: str) -> None:
    raw_bytes = json.dumps(_PAYLOAD).encode("utf-8")
    raw_storage = LocalRawStorage(raw_store)
    sha256 = compute_sha256(raw_bytes)
    key = build_object_key("fred", "CPIAUCSL", datetime(2024, 1, 1, 9, 0, tzinfo=UTC), sha256)
    raw_storage.put(key, raw_bytes)
    writer = BronzeWriter(raw_storage, db_path=bronze_db)
    try:
        writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key=key,
            raw_sha256=sha256,
            retrieved_at=datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
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


def _measure_query_latencies(transform_db: str, repeats: int) -> list[float]:
    con = duckdb.connect(transform_db, read_only=True)
    try:
        latencies = []
        for _ in range(repeats):
            started = time.perf_counter()
            con.execute(_QUERY).fetchall()
            latencies.append(time.perf_counter() - started)
        return latencies
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

    _seed(args.raw_store, args.bronze_db)
    _dbt_build(args.project_dir, args.profiles_dir)

    latencies = _measure_query_latencies(args.transform_db, _REPEATS)
    median = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]  # ~p95 of 20 samples
    print(
        f"Gold query latency over {_REPEATS} runs: "
        f"median={median * 1000:.2f}ms p95={p95 * 1000:.2f}ms "
        f"(target: median < {_NFR_PERF_001_TARGET_SECONDS}s)"
    )

    if median >= _NFR_PERF_001_TARGET_SECONDS:
        print(
            f"FAIL (NFR-PERF-001): median Gold query latency {median:.3f}s "
            f"exceeds the {_NFR_PERF_001_TARGET_SECONDS}s target",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "PASS: NFR-PERF-001's query-latency mechanism verified against a synthetic "
        "Gold fixture -- see this script's docstring for what real-scale/production "
        "verification still needs (a capacity model, and a live Metabase instance)."
    )


if __name__ == "__main__":
    main()
