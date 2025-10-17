"""Abstractions for persisting Gmail messages in Weaviate."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, TYPE_CHECKING

import weaviate
from weaviate.classes import query
from weaviate.classes.config import Configure, DataType, Property
from weaviate.exceptions import ObjectAlreadyExistsError
from weaviate.util import generate_uuid5

from database.config import WeaviateSettings, load_weaviate_settings
from gmail.models.email_record import EmailRecord

if TYPE_CHECKING:  # pragma: no cover - import only used for typing
    from weaviate.client import WeaviateClient
    from weaviate.collections.collection import Collection

COLLECTION_NAME = "GmailEmail"


class GmailEmailService:
    """High-level helper for managing Gmail email records in Weaviate."""

    def __init__(self, client: "WeaviateClient", *, owns_client: bool = False):
        self._client = client
        self._owns_client = owns_client
        self._collection = self._ensure_collection()

    @classmethod
    @contextmanager
    def connect(
        cls, settings: Optional[WeaviateSettings] = None
    ) -> Iterator["GmailEmailService"]:
        """Context-managed helper that yields a service with an active client."""
        resolved = settings or load_weaviate_settings()
        with weaviate.connect_to_local(
            host=resolved.host,
            port=resolved.port,
            grpc_port=resolved.grpc_port,
            headers=resolved.headers,
        ) as client:
            yield cls(client)

    def __enter__(self) -> "GmailEmailService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
        return None

    def _ensure_collection(self) -> "Collection":
        if not self._client.collections.exists(COLLECTION_NAME):
            self._client.collections.create(
                name=COLLECTION_NAME,
                properties=[
                    Property(name="message_id", data_type=DataType.TEXT),
                    Property(name="subject", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="sent_at", data_type=DataType.DATE),
                    Property(name="is_read", data_type=DataType.BOOL),
                    Property(name="is_vectorized", data_type=DataType.BOOL),
                ],
                vectorizer_config=Configure.Vectorizer.none(),
            )
        return self._client.collections.get(COLLECTION_NAME)

    @staticmethod
    def _uuid_for(message_id: str) -> str:
        return str(generate_uuid5(COLLECTION_NAME, message_id))

    def upsert(
        self,
        record: EmailRecord,
        *,
        vector: Optional[List[float]] = None,
    ) -> str:
        """Insert or update a Gmail email."""
        properties = record.to_properties()
        if vector is not None and not record.is_vectorized:
            properties["is_vectorized"] = True

        uuid = self._uuid_for(record.message_id)
        try:
            self._collection.data.insert(
                properties=properties,
                uuid=uuid,
                vector=vector,
            )
        except ObjectAlreadyExistsError:
            self._collection.data.update(
                uuid=uuid,
                properties=properties,
                vector=vector,
            )
        return uuid

    def mark_vectorized(self, message_id: str, *, is_vectorized: bool = True) -> None:
        """Toggle the vectorised flag for an email."""
        uuid = self._uuid_for(message_id)
        self._collection.data.update(
            uuid=uuid,
            properties={"is_vectorized": is_vectorized},
        )

    def list_unvectorized(self, limit: int = 100) -> Iterable[EmailRecord]:
        """Retrieve emails that still need vectorisation."""
        response = self._collection.query.fetch_objects(
            filters=query.Filter.by_property("is_vectorized").equal(False),
            limit=limit,
            return_properties=[
                "message_id",
                "subject",
                "content",
                "sent_at",
                "is_read",
                "is_vectorized",
            ],
        )
        for obj in response.objects:
            yield EmailRecord.from_properties(obj.properties)  # type: ignore[arg-type]

    def close(self) -> None:
        """Close the underlying client connection if this instance owns it."""
        if self._owns_client:
            self._client.__exit__(None, None, None)  # type: ignore[union-attr]
            self._owns_client = False


__all__ = ["GmailEmailRecord", "GmailEmailService", "COLLECTION_NAME"]
