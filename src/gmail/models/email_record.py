"""Data models for Gmail email persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EmailRecord:
    """Representation of a Gmail message persisted in Weaviate."""

    message_id: str
    subject: str
    content: str
    sent_at: datetime
    is_read: bool
    is_vectorized: bool = False

    def to_properties(self) -> dict:
        """Serialise record fields for Weaviate storage."""
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "content": self.content,
            "sent_at": self.sent_at.isoformat(),
            "is_read": self.is_read,
            "is_vectorized": self.is_vectorized,
        }

    @classmethod
    def from_properties(cls, properties: dict) -> "EmailRecord":
        """Rehydrate a record from Weaviate query results."""
        return cls(
            message_id=properties["message_id"],
            subject=properties["subject"],
            content=properties["content"],
            sent_at=datetime.fromisoformat(properties["sent_at"]),
            is_read=properties["is_read"],
            is_vectorized=properties["is_vectorized"],
        )
