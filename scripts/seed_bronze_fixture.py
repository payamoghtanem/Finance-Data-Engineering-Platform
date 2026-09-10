#!/usr/bin/env python3
"""Write a synthetic FRED CPI Bronze row for exercising src/transform/dbt_project/.

Used by CI's dbt-transform job (technical-design-document.md §5) and runnable
the same way locally. Writes through the real RawStorage/BronzeWriter code
path (never hand-crafts a Bronze row directly) so it exercises the same
checksum/lineage logic a live connector run would -- but the payload itself
is synthetic, not fetched from FRED. Not a source of truth for real data.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from src.bronze.writer import BronzeWriter
from src.common.raw_storage import LocalRawStorage, build_object_key, compute_sha256

_PAYLOAD = {
    "realtime_start": "2024-02-01",
    "realtime_end": "2024-02-01",
    "observations": [
        {
            "realtime_start": "2024-02-01",
            "realtime_end": "2024-02-01",
            "date": "2023-11-01",
            "value": "307.671",
        },
        {
            "realtime_start": "2024-02-01",
            "realtime_end": "2024-02-01",
            "date": "2023-12-01",
            "value": "306.746",
        },
        {
            "realtime_start": "2024-02-01",
            "realtime_end": "2024-02-01",
            "date": "2024-01-01",
            "value": "308.417",
        },
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-store", default="raw_store")
    parser.add_argument("--bronze-db", default="bronze_store/bronze.duckdb")
    args = parser.parse_args()

    raw_bytes = json.dumps(_PAYLOAD).encode("utf-8")
    raw_storage = LocalRawStorage(args.raw_store)
    retrieved_at = datetime(2024, 2, 1, 9, 0, tzinfo=UTC)
    sha256 = compute_sha256(raw_bytes)
    key = build_object_key("fred", "CPIAUCSL", retrieved_at, sha256)
    raw_storage.put(key, raw_bytes)

    writer = BronzeWriter(raw_storage, db_path=args.bronze_db)
    try:
        record = writer.write(
            source_id="fred",
            dataset_id="fred_cpiaucsl",
            raw_object_key=key,
            raw_sha256=sha256,
            retrieved_at=retrieved_at,
            code_version="0.0.0-ci-fixture",
        )
    finally:
        writer.close()
    print(f"Seeded Bronze fixture: bronze_id={record.bronze_id}")


if __name__ == "__main__":
    main()
