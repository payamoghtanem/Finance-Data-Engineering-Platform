"""Unit tests for the S3/MinIO-backed RawStorage (US-03-001).

Runs against a mocked S3 (moto) — no live MinIO required, no network call, per
docs/engineering/test-strategy.md §2.
"""

from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws
from src.common.raw_storage import RawStorageError, S3RawStorage


@pytest.fixture
def s3_storage() -> Iterator[S3RawStorage]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        storage = S3RawStorage(
            bucket="raw",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",  # noqa: S106 - test fixture, not a credential
            client=client,
        )
        storage.ensure_bucket()
        yield storage


class TestS3RawStorage:
    def test_put_then_get_round_trips_identical_bytes(self, s3_storage: S3RawStorage) -> None:
        payload = b'{"observations": [1, 2, 3]}'
        key = s3_storage.put("raw/fred/CPIAUCSL/date=2026-09-10/abc.json", payload)
        assert s3_storage.get(key) == payload

    def test_exists_false_before_put_true_after(self, s3_storage: S3RawStorage) -> None:
        key = "raw/fred/CPIAUCSL/date=2026-09-10/abc.json"
        assert s3_storage.exists(key) is False
        s3_storage.put(key, b"payload")
        assert s3_storage.exists(key) is True

    def test_putting_same_key_twice_is_idempotent(self, s3_storage: S3RawStorage) -> None:
        key = "raw/fred/CPIAUCSL/date=2026-09-10/abc.json"
        s3_storage.put(key, b"payload")
        s3_storage.put(key, b"payload")
        # A second put on an existing key must not error and must not alter content.
        assert s3_storage.get(key) == b"payload"

    def test_get_missing_key_raises(self, s3_storage: S3RawStorage) -> None:
        with pytest.raises(RawStorageError):
            s3_storage.get("raw/does/not/exist.json")

    def test_ensure_bucket_is_safe_to_call_repeatedly(self, s3_storage: S3RawStorage) -> None:
        s3_storage.ensure_bucket()
        s3_storage.ensure_bucket()  # must not raise on an already-existing bucket
