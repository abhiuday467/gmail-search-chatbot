"""Tests for the health check utility."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Callable, Dict, Optional, Tuple
import importlib
import sys
import types

import pytest


class _StubClient:
    """Minimal stand-in for the Weaviate client used by health_check."""

    def __init__(
        self,
        *,
        live: bool,
        ready: bool,
        meta: Optional[Dict[str, str]] = None,
    ) -> None:
        self._live = live
        self._ready = ready
        self._meta = meta or {}

    def __enter__(self) -> "_StubClient":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        return None

    def is_live(self) -> bool:
        return self._live

    def is_ready(self) -> bool:
        return self._ready

    def get_meta(self) -> Dict[str, str]:
        return self._meta


def _patch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    client_factory: Callable[[], _StubClient],
) -> Tuple[types.ModuleType, Callable[[], _StubClient]]:
    """Patch external dependencies so main() can be exercised deterministically."""

    stub_weaviate = types.SimpleNamespace(connect_to_local=None)
    monkeypatch.setitem(sys.modules, "weaviate", stub_weaviate)
    if "database.health_check" in sys.modules:
        module = importlib.reload(sys.modules["database.health_check"])
    else:
        module = importlib.import_module("database.health_check")

    def fake_connect_to_local(**_: object) -> _StubClient:
        return client_factory()

    monkeypatch.setattr(module.weaviate, "connect_to_local", fake_connect_to_local)

    settings = SimpleNamespace(
        host="localhost",
        port=8080,
        grpc_port=50051,
        headers=None,
    )
    monkeypatch.setattr(module, "load_weaviate_settings", lambda: settings)
    return module, fake_connect_to_local


class TestHealthCheckMain:
    """Behavioural coverage for database.health_check.main."""

    def test_returns_zero_when_weaviate_is_healthy(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module, _ = _patch_dependencies(
            monkeypatch,
            client_factory=lambda: _StubClient(
                live=True,
                ready=True,
                meta={"version": "1.0.0"},
            ),
        )

        assert module.main() == 0

        captured = capsys.readouterr()
        assert "[health-check] Weaviate is live and ready." in captured.out
        assert "version" in captured.out

    def test_returns_two_when_service_reports_unhealthy(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module, _ = _patch_dependencies(
            monkeypatch,
            client_factory=lambda: _StubClient(
                live=False,
                ready=True,
            ),
        )

        assert module.main() == 2

        captured = capsys.readouterr()
        assert "reported an unhealthy status" in captured.err

    def test_returns_one_when_connection_fails(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stub_weaviate = types.SimpleNamespace(connect_to_local=lambda **_: None)
        monkeypatch.setitem(sys.modules, "weaviate", stub_weaviate)
        if "database.health_check" in sys.modules:
            module = importlib.reload(sys.modules["database.health_check"])
        else:
            module = importlib.import_module("database.health_check")

        def fake_connect(**_: object) -> None:
            raise RuntimeError("boom")

        monkeypatch.setattr(module.weaviate, "connect_to_local", fake_connect)
        settings = SimpleNamespace(
            host="localhost",
            port=8080,
            grpc_port=50051,
            headers=None,
        )
        monkeypatch.setattr(module, "load_weaviate_settings", lambda: settings)

        assert module.main() == 1

        captured = capsys.readouterr()
        assert "Failed to contact Weaviate" in captured.err
