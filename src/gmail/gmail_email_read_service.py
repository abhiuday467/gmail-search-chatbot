"""Utilities for reading Gmail messages using OAuth-protected credentials."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

try:
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - build is patched in tests when missing
    build = None  # type: ignore[assignment]

from gmail.gmail_oauth2_service import GmailOAuth2Service


class GmailEmailReadService:
    """Fetch Gmail messages using credentials managed by GmailOAuth2Service."""

    def __init__(
        self,
        *,
        oauth_service: Optional[GmailOAuth2Service] = None,
        user_id: Optional[str] = None,
    ) -> None:
        self._oauth_service = oauth_service or GmailOAuth2Service()
        self._user_id = user_id or os.getenv("GMAIL_USER_ID", "me")

    def fetch_latest_messages(
        self,
        *,
        max_results: int = 2,
        label_ids: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return the most recent Gmail messages, defaulting to the inbox."""
        if build is None:
            raise RuntimeError(
                "googleapiclient.discovery.build is required but not installed."
            )
        credentials = self._oauth_service.get_credentials()
        gmail_client = build("gmail", "v1", credentials=credentials)

        list_request = (
            gmail_client.users()
            .messages()
            .list(
                userId=self._user_id,
                maxResults=max_results,
                labelIds=list(label_ids) if label_ids else ["INBOX"],
            )
        )
        messages_payload = list_request.execute()

        messages = messages_payload.get("messages", [])
        results: List[Dict[str, Any]] = []
        for message in messages:
            message_id = message["id"]
            detail = (
                gmail_client.users()
                .messages()
                .get(userId=self._user_id, id=message_id, format="full")
                .execute()
            )
            results.append(self._simplify_message(detail))
        return results

    @staticmethod
    def _simplify_message(message: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            item["name"].lower(): item["value"]
            for item in message.get("payload", {}).get("headers", [])
        }
        return {
            "id": message.get("id"),
            "threadId": message.get("threadId"),
            "snippet": message.get("snippet"),
            "subject": headers.get("subject"),
            "from": headers.get("from"),
            "to": headers.get("to"),
            "internalDate": message.get("internalDate"),
        }


__all__ = ["GmailEmailReadService"]


def main() -> None:
    """CLI helper to fetch and display the latest Gmail messages."""
    service = GmailEmailReadService()
    messages = service.fetch_latest_messages(max_results=2)
    if not messages:
        print("No messages found.")
        return
    for message in messages:
        subject = message.get("subject") or "<no subject>"
        sender = message.get("from") or "<unknown sender>"
        snippet = (message.get("snippet") or "").strip()
        print(f"Subject: {subject}")
        print(f"From: {sender}")
        if snippet:
            print(f"Snippet: {snippet}")
        print("-" * 40)


if __name__ == "__main__":
    main()
