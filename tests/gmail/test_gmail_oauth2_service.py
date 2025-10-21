from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

import gmail.gmail_oauth2_service as oauth_module
from gmail.gmail_oauth2_service import GmailOAuth2Service


def test_get_credentials_refreshes_existing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_dependencies(monkeypatch)

    creds = _StubCredentials(expired=True, refresh_token="refresh-token", valid=False)
    stored: Dict[str, Any] = {}

    monkeypatch.setattr(oauth_module, "_load_credentials", lambda: creds, raising=False)
    monkeypatch.setattr(
        oauth_module,
        "_store_credentials",
        lambda value: stored.setdefault("creds", value),
        raising=False,
    )

    service = GmailOAuth2Service()
    result = service.get_credentials()

    assert result is creds
    assert creds.refresh_calls  # refresh invoked
    assert stored["creds"] is creds


def test_get_credentials_runs_flow_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_dependencies(monkeypatch)

    stub_creds = _StubCredentials(
        expired=False, refresh_token="refresh-token", valid=True
    )
    config_calls: Dict[str, Any] = {}
    stored: Dict[str, Any] = {}

    monkeypatch.setattr(oauth_module, "_load_credentials", lambda: None, raising=False)
    monkeypatch.setattr(
        oauth_module,
        "_load_client_config",
        lambda: config_calls.setdefault("config", {"installed": {"client_id": "id"}}),
        raising=False,
    )
    monkeypatch.setattr(
        oauth_module,
        "_store_credentials",
        lambda value: stored.setdefault("creds", value),
        raising=False,
    )

    flow = _StubFlow(stub_creds)

    class _DummyInstalledFlow:
        @classmethod
        def from_client_config(
            cls, config: Dict[str, Any], scopes: list[str]
        ) -> _StubFlow:
            config_calls["args"] = (config, scopes)
            return flow

    monkeypatch.setattr(
        oauth_module, "InstalledAppFlow", _DummyInstalledFlow, raising=False
    )

    service = GmailOAuth2Service()
    result = service.get_credentials()

    assert result is stub_creds
    assert stored["creds"] is stub_creds
    assert config_calls["args"][1] == oauth_module.SCOPES
    assert flow.port == (0,)


def test_get_credentials_raises_when_dependencies_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(oauth_module, "Credentials", None, raising=False)
    monkeypatch.setattr(oauth_module, "Request", None, raising=False)
    monkeypatch.setattr(oauth_module, "InstalledAppFlow", None, raising=False)

    service = GmailOAuth2Service()
    with pytest.raises(RuntimeError):
        service.get_credentials()


class _StubCredentials:
    def __init__(self, *, expired: bool, refresh_token: str, valid: bool) -> None:
        self.expired = expired
        self.refresh_token = refresh_token
        self.valid = valid
        self.refresh_calls: list[Any] = []

    def refresh(self, request: Any) -> None:
        self.refresh_calls.append(request)
        self.expired = False
        self.valid = True

    def to_json(self) -> str:
        return '{"token": "stub"}'


class _StubFlow:
    def __init__(self, result: _StubCredentials) -> None:
        self._result = result
        self.port: Tuple[int, ...] | None = None

    def run_local_server(self, port: int) -> _StubCredentials:
        self.port = (port,)
        return self._result


def _set_required_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DummyRequest:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class _DummyInstalledFlow:
        from_client_config = None  # replaced in tests

    # Ensure the module sees the expected Google classes
    monkeypatch.setattr(oauth_module, "Credentials", object(), raising=False)
    monkeypatch.setattr(oauth_module, "Request", _DummyRequest, raising=False)
    monkeypatch.setattr(
        oauth_module, "InstalledAppFlow", _DummyInstalledFlow, raising=False
    )
