"""Utilities for ingesting Gmail messages into the vector store."""

from __future__ import annotations

from datetime import datetime
from email.header import decode_header, make_header
from typing import Any

from langchain_core.documents import Document

from .gmail_client import GmailClient
from .vector_store import VectorStore


def _decode_header(value: str | None) -> str:
    """Decode RFC 2047 encoded headers."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _message_body(message: dict[str, Any]) -> str:
    """Extract a readable plain-text body from a Gmail message."""
    payload = message.get("payload", {})
    body = payload.get("body", {})
    data = body.get("data")
    if data:
        from base64 import urlsafe_b64decode

        return urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []) or []:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data")
            if not data:
                continue
            from base64 import urlsafe_b64decode

            return urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    return ""


def _to_document(message: dict[str, Any]) -> Document:
    headers = {header["name"]: header["value"] for header in message.get("payload", {}).get("headers", [])}
    subject = _decode_header(headers.get("Subject"))
    sender = _decode_header(headers.get("From"))
    timestamp = message.get("internalDate")
    metadata = {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "subject": subject,
        "from": sender,
        "snippet": message.get("snippet", ""),
    }
    if timestamp:
        metadata["received_at"] = datetime.fromtimestamp(int(timestamp) / 1000).isoformat()

    return Document(page_content=_message_body(message), metadata=metadata)


def ingest_mailbox(
    vector_store: VectorStore,
    gmail_client: GmailClient,
    query: str = "",
    limit: int | None = None,
) -> int:
    """Fetch messages from Gmail and persist them in the vector store."""
    count = 0
    for message in gmail_client.iter_messages(query=query):
        document = _to_document(message)
        if not document.page_content.strip():
            continue
        vector_store.add_documents([document])
        count += 1
        if limit is not None and count >= limit:
            break
    if count:
        vector_store.persist()
    return count
