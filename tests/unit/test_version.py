"""Unit tests for get_code_version (FR-ING-001, NFR-AUDIT-001 provenance)."""

from __future__ import annotations

from src.common.version import _FALLBACK_VERSION, get_code_version


class TestGetCodeVersion:
    def test_returns_a_non_empty_string(self) -> None:
        result = get_code_version()
        assert isinstance(result, str)
        assert result != ""

    def test_falls_back_when_package_not_found(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import src.common.version as version_module

        def _raise_not_found(_name: str) -> str:
            raise version_module.PackageNotFoundError

        monkeypatch.setattr(version_module, "version", _raise_not_found)
        assert get_code_version() == _FALLBACK_VERSION
