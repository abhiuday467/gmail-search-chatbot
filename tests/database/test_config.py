"""Tests for database configuration helpers."""

from __future__ import annotations

import pytest

from database.config import WeaviateSettings, _get_int, load_weaviate_settings


class TestLoadWeaviateSettings:
    """Behavioural checks for the load_weaviate_settings helper."""

    def test_load_defaults_when_env_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in (
            "WEAVIATE_HOST",
            "WEAVIATE_PORT",
            "WEAVIATE_GRPC_PORT",
            "WEAVIATE_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)

        settings = load_weaviate_settings()

        assert settings.host == "localhost"
        assert settings.port == 8080
        assert settings.grpc_port == 50051
        assert settings.api_key is None

    def test_load_values_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEAVIATE_HOST", "weaviate.internal")
        monkeypatch.setenv("WEAVIATE_PORT", "1234")
        monkeypatch.setenv("WEAVIATE_GRPC_PORT", "4321")
        monkeypatch.setenv("WEAVIATE_API_KEY", "secret")

        settings = load_weaviate_settings()

        assert settings.host == "weaviate.internal"
        assert settings.port == 1234
        assert settings.grpc_port == 4321
        assert settings.api_key == "secret"


class TestWeaviateSettingsHeaders:
    """Focused tests for the computed headers property."""

    def test_headers_include_api_key(self) -> None:
        settings = WeaviateSettings(host="h", port=1, grpc_port=2, api_key="token")

        assert settings.headers == {"X-API-KEY": "token"}

    def test_headers_none_without_key(self) -> None:
        settings = WeaviateSettings(host="h", port=1, grpc_port=2, api_key=None)

        assert settings.headers is None


class TestGetIntHelper:
    """Validation coverage for the internal _get_int helper."""

    def test_get_int_rejects_non_numeric(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEAVIATE_PORT", "not-a-number")

        with pytest.raises(ValueError) as excinfo:
            _get_int("WEAVIATE_PORT", default=8080)

        assert "WEAVIATE_PORT must be an integer" in str(excinfo.value)
