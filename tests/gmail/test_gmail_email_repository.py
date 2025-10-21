"""Tests for GmailEmailService with stubbed Weaviate dependencies."""

from __future__ import annotations

import sys
import types
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, TypedDict, cast

import pytest


def _install_weaviate_stubs() -> None:
    """Ensure lightweight stand-ins for the weaviate SDK are present."""
    if "weaviate" in sys.modules:
        return

    weaviate_module = types.ModuleType("weaviate")
    sys.modules["weaviate"] = weaviate_module

    classes_module = types.ModuleType("weaviate.classes")
    sys.modules["weaviate.classes"] = classes_module

    query_module = types.ModuleType("weaviate.classes.query")

    class _PropertyFilter:
        def __init__(self, name: str) -> None:
            self._name = name

        def equal(self, value: object) -> tuple[str, str, object]:
            return ("equal", self._name, value)

    class _Filter:
        @staticmethod
        def by_property(name: str) -> _PropertyFilter:
            return _PropertyFilter(name)

    setattr(query_module, "Filter", _Filter)
    sys.modules["weaviate.classes.query"] = query_module
    setattr(classes_module, "query", query_module)

    config_module = types.ModuleType("weaviate.classes.config")

    class _Vectorizer:
        @staticmethod
        def none() -> str:
            return "none"

    class _Configure:
        Vectorizer = _Vectorizer

    class _DataType:
        TEXT = "text"
        DATE = "date"
        BOOL = "bool"

    class _Property:
        def __init__(self, *, name: str, data_type: str) -> None:
            self.name = name
            self.data_type = data_type

    setattr(config_module, "Configure", _Configure)
    setattr(config_module, "DataType", _DataType)
    setattr(config_module, "Property", _Property)
    sys.modules["weaviate.classes.config"] = config_module

    exceptions_module = types.ModuleType("weaviate.exceptions")

    class _AlreadyExistsError(RuntimeError):
        pass

    setattr(exceptions_module, "ObjectAlreadyExistsError", _AlreadyExistsError)
    sys.modules["weaviate.exceptions"] = exceptions_module

    util_module = types.ModuleType("weaviate.util")
    setattr(
        util_module, "generate_uuid5", lambda namespace, name: f"{namespace}:{name}"
    )
    sys.modules["weaviate.util"] = util_module

    setattr(weaviate_module, "classes", classes_module)
    setattr(weaviate_module, "exceptions", exceptions_module)
    setattr(weaviate_module, "util", util_module)

    class _ContextlessClient:
        def __enter__(self) -> "_ContextlessClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    setattr(weaviate_module, "connect_to_local", lambda **_: _ContextlessClient())


_install_weaviate_stubs()

from gmail.gmail_email_repository import (
    COLLECTION_NAME,
    GmailEmailRepository,
)  # noqa: E402
import gmail.gmail_email_repository as service_module  # noqa: E402
from gmail.models.email_record import EmailRecord  # noqa: E402

service_module = cast(Any, service_module)


@pytest.fixture(autouse=True)
def _deterministic_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep UUID generation stable for deterministic assertions."""

    monkeypatch.setattr(
        service_module,
        "generate_uuid5",
        lambda namespace, value: f"{namespace}:{value}",
    )


def _make_record(
    message_id: str,
    *,
    subject: str = "Subject",
    content: str = "Body",
    sent_at: datetime = datetime(2024, 1, 1),
    is_read: bool = False,
    is_vectorized: bool = False,
) -> EmailRecord:
    return EmailRecord(
        message_id=message_id,
        subject=subject,
        content=content,
        sent_at=sent_at,
        is_read=is_read,
        is_vectorized=is_vectorized,
    )


class _StubCollectionData:
    def __init__(self, parent: "_StubCollection") -> None:
        self._parent = parent

    def insert(
        self,
        *,
        properties: Dict[str, object],
        uuid: str,
        vector: Optional[List[float]] = None,
    ) -> None:
        if uuid in self._parent.items:
            raise service_module.ObjectAlreadyExistsError()
        self._parent.items[uuid] = {"properties": dict(properties), "vector": vector}

    def update(
        self,
        *,
        uuid: str,
        properties: Dict[str, object],
        vector: Optional[List[float]] = None,
    ) -> None:
        if uuid not in self._parent.items:
            self._parent.items[uuid] = {"properties": {}, "vector": None}
        entry = self._parent.items[uuid]
        entry["properties"].update(dict(properties))
        if vector is not None:
            entry["vector"] = vector


class _StubCollectionQuery:
    def __init__(self, parent: "_StubCollection") -> None:
        self._parent = parent

    def fetch_objects(
        self,
        *,
        filters: Optional[tuple[str, str, object]] = None,
        limit: int,
        return_properties: Iterable[str],
    ) -> types.SimpleNamespace:
        results = []
        for entry in self._parent.items.values():
            if filters and filters[0] == "equal":
                prop_name = filters[1]
                expected = filters[2]
                if entry["properties"].get(prop_name) != expected:
                    continue
            props = {
                key: entry["properties"][key]
                for key in return_properties
                if key in entry["properties"]
            }
            results.append(types.SimpleNamespace(properties=props))
            if len(results) >= limit:
                break
        return types.SimpleNamespace(objects=results)


class _StoredEntry(TypedDict):
    properties: Dict[str, object]
    vector: Optional[List[float]]


class _StubCollection:
    def __init__(self) -> None:
        self.items: Dict[str, _StoredEntry] = {}
        self.data = _StubCollectionData(self)
        self.query = _StubCollectionQuery(self)


class _StubCollectionsFacade:
    def __init__(self) -> None:
        self._collections: Dict[str, _StubCollection] = {}
        self.created_configs: List[Dict[str, object]] = []

    def exists(self, name: str) -> bool:
        return name in self._collections

    def create(
        self,
        *,
        name: str,
        properties: List[object],
        vectorizer_config: object,
    ) -> None:
        self.created_configs.append(
            {
                "name": name,
                "properties": properties,
                "vectorizer_config": vectorizer_config,
            }
        )
        self._collections[name] = _StubCollection()

    def get(self, name: str) -> _StubCollection:
        return self._collections.setdefault(name, _StubCollection())


class _StubClient:
    def __init__(self) -> None:
        self.collections = _StubCollectionsFacade()
        self.close_count = 0

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close_count += 1
        return None


def test_initialises_collection_when_missing() -> None:
    client = _StubClient()

    GmailEmailRepository(client)

    assert client.collections.created_configs
    created = client.collections.created_configs[0]
    assert created["name"] == COLLECTION_NAME
    assert client.collections.exists(COLLECTION_NAME)


def test_upsert_inserts_new_record_and_marks_vectorized_when_vector_present() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)
    record = _make_record("abc123", subject="Hello")

    uuid = service.upsert(record, vector=[0.1, 0.2])

    assert uuid == f"{COLLECTION_NAME}:abc123"
    stored = client.collections.get(COLLECTION_NAME).items[uuid]
    assert stored["properties"]["subject"] == "Hello"
    assert stored["properties"]["is_vectorized"] is True
    assert stored["vector"] == [0.1, 0.2]


def test_upsert_updates_existing_record_when_already_present() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)
    original = _make_record("abc123", subject="First")
    updated = _make_record("abc123", subject="Updated", is_vectorized=True)

    service.upsert(original)
    service.upsert(updated)

    stored = client.collections.get(COLLECTION_NAME).items[f"{COLLECTION_NAME}:abc123"]
    assert stored["properties"]["subject"] == "Updated"
    assert stored["properties"]["is_vectorized"] is True


def test_mark_vectorized_updates_flag() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)
    record = _make_record("msg-1")
    service.upsert(record)

    service.mark_vectorized("msg-1", is_vectorized=True)

    stored = client.collections.get(COLLECTION_NAME).items[f"{COLLECTION_NAME}:msg-1"]
    assert stored["properties"]["is_vectorized"] is True


def test_list_unvectorized_returns_only_pending_records() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)
    pending = _make_record("pending-1")
    completed = _make_record("done-1")

    service.upsert(pending)
    service.upsert(completed, vector=[0.5])

    records = list(service.list_unvectorized())

    assert [record.message_id for record in records] == ["pending-1"]


def test_close_invokes_client_exit_when_owned() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)
    service._owns_client = True  # simulate connect()-managed lifecycle

    service.close()

    assert client.close_count == 1
    assert service._owns_client is False


def test_close_ignored_when_not_owned() -> None:
    client = _StubClient()
    service = GmailEmailRepository(client)

    service.close()

    assert client.close_count == 0
