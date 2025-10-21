from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import pytest

from gmail.gmail_email_read_service import GmailEmailReadService


def test_fetch_latest_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    details = {
        "msg-1": {
            "id": "msg-1",
            "threadId": "thread-1",
            "snippet": "hello world",
            "internalDate": "123456",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "a@example.com"},
                    {"name": "To", "value": "b@example.com"},
                ]
            },
        },
        "msg-2": {
            "id": "msg-2",
            "threadId": "thread-2",
            "snippet": "second",
            "internalDate": "654321",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hi"},
                    {"name": "From", "value": "c@example.com"},
                ]
            },
        },
    }
    fake_client = _FakeGmailClient(details)

    monkeypatch.setenv("GMAIL_USER_ID", "me")
    monkeypatch.setattr(
        "gmail.gmail_email_read_service.build", lambda *args, **kwargs: fake_client
    )

    service = GmailEmailReadService(oauth_service=_StubOAuth())

    messages = service.fetch_latest_messages(max_results=2)

    assert [msg["id"] for msg in messages] == ["msg-1", "msg-2"]
    assert messages[0]["subject"] == "Hello"
    assert messages[0]["from"] == "a@example.com"
    assert messages[0]["to"] == "b@example.com"
    assert messages[1]["subject"] == "Hi"
    # Ensure inbox label used by default
    assert fake_client.messages.list_calls[0]["labelIds"] == ["INBOX"]


class _FakeRequest:
    def __init__(self, response: Dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> Dict[str, Any]:
        return self._response


class _FakeMessages:
    def __init__(self, details: Dict[str, Dict[str, Any]]) -> None:
        self._details = details
        self.list_calls: List[Dict[str, Any]] = []
        self.get_calls: List[Tuple[str, str, str]] = []

    def list(self, **kwargs: Any) -> _FakeRequest:
        self.list_calls.append(kwargs)
        return _FakeRequest({"messages": [{"id": key} for key in self._details]})

    def get(self, *, userId: str, id: str, format: str) -> _FakeRequest:
        self.get_calls.append((userId, id, format))
        return _FakeRequest(self._details[id])


class _FakeUsers:
    def __init__(self, messages: _FakeMessages) -> None:
        self._messages = messages

    def messages(self) -> _FakeMessages:
        return self._messages


class _FakeGmailClient:
    def __init__(self, details: Dict[str, Dict[str, Any]]) -> None:
        self.messages = _FakeMessages(details)
        self.users_calls = 0

    def users(self) -> _FakeUsers:
        self.users_calls += 1
        return _FakeUsers(self.messages)


class _StubOAuth:
    def get_credentials(self) -> object:
        return object()
