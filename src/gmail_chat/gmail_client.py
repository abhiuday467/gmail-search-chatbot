"""Gmail API client helpers."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import Settings, get_settings


class GmailClient:
    """Light wrapper around the Gmail API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _credentials(self) -> Credentials:
        if not self._settings.google_refresh_token:
            raise ValueError("GOOGLE_REFRESH_TOKEN must be set before using the Gmail client.")

        creds = Credentials(
            None,
            refresh_token=self._settings.google_refresh_token,
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=list(self._settings.google_scopes),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds

    def _service(self):
        credentials = self._credentials()
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def iter_messages(self, query: str = "", page_size: int = 100) -> Generator[dict[str, Any], None, None]:
        """Yield raw message payloads for a query."""
        service = self._service()
        request = service.users().messages().list(
            userId=self._settings.gmail_user_id,
            q=query,
            maxResults=page_size,
        )

        while request is not None:
            response = request.execute()
            for metadata in response.get("messages", []):
                message = (
                    service.users()
                    .messages()
                    .get(userId=self._settings.gmail_user_id, id=metadata["id"], format="full")
                    .execute()
                )
                yield message
            request = service.users().messages().list_next(previous_request=request, previous_response=response)
