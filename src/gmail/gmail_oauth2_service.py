"""Kick off Gmail OAuth flow to obtain tokens for mailbox ingestion."""

from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import dotenv

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:  # pragma: no cover - optional dependency at import time
    Request = None  # type: ignore[assignment]
    Credentials = None  # type: ignore[assignment]
    InstalledAppFlow = None  # type: ignore[assignment]

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CLIENT_SECRET_B64_ENV = "GOOGLE_CLIENT_SECRET_B64"
TOKEN_B64_ENV = "GOOGLE_TOKEN_JSON_B64"
REFRESH_TOKEN_ENV = "GOOGLE_REFRESH_TOKEN"
CLIENT_ID_ENV = "GOOGLE_CLIENT_ID"
CLIENT_SECRET_ENV = "GOOGLE_CLIENT_SECRET"
TOKEN_URI_ENV = "GOOGLE_TOKEN_URI"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _load_client_config() -> Dict[str, Any]:
    """Load the OAuth client configuration from the environment."""
    dotenv.load_dotenv()
    secret_b64 = os.getenv(CLIENT_SECRET_B64_ENV, "").strip()
    if secret_b64:
        return _decode_b64_json(secret_b64, context=CLIENT_SECRET_B64_ENV)

    raise FileNotFoundError(
        f"Set {CLIENT_SECRET_B64_ENV} with the base64-encoded Gmail client secret JSON."
    )


def _decode_b64_json(value: str, *, context: str) -> Dict[str, Any]:
    try:
        decoded = base64.b64decode(value.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{context} must be base64-encoded JSON") from exc


def _load_credentials() -> Optional[Credentials]:
    if Credentials is None:
        raise RuntimeError("google-auth is required to load Gmail credentials.")
    dotenv.load_dotenv()
    token_b64 = os.getenv(TOKEN_B64_ENV, "").strip()
    if token_b64:
        data = _decode_b64_json(token_b64, context=TOKEN_B64_ENV)
        return Credentials.from_authorized_user_info(data, SCOPES)

    refresh_token = os.getenv(REFRESH_TOKEN_ENV, "").strip()
    client_id = os.getenv(CLIENT_ID_ENV, "").strip()
    client_secret = os.getenv(CLIENT_SECRET_ENV, "").strip()
    token_uri = os.getenv(TOKEN_URI_ENV, DEFAULT_TOKEN_URI).strip() or DEFAULT_TOKEN_URI

    if refresh_token and client_id and client_secret:
        data = {
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_uri": token_uri,
            "scopes": SCOPES,
        }
        return Credentials.from_authorized_user_info(data, SCOPES)

    return None


def _store_credentials(creds: Credentials) -> None:
    if Credentials is None:
        raise RuntimeError("google-auth is required to store Gmail credentials.")
    token_json = creds.to_json()
    token_b64 = base64.b64encode(token_json.encode("utf-8")).decode("utf-8")

    _update_env_variable(TOKEN_B64_ENV, token_b64)
    if creds.refresh_token:
        _update_env_variable(REFRESH_TOKEN_ENV, creds.refresh_token)


def _update_env_variable(name: str, value: str) -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    lines: list[str] = []
    found = False

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated_lines = []
    for line in lines:
        if line.startswith(f"{name}="):
            updated_lines.append(f"{name}={value}")
            found = True
        else:
            updated_lines.append(line)

    if not found:
        updated_lines.append(f"{name}={value}")

    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


class GmailOAuth2Service:
    """Manage Gmail OAuth2 credentials backed by environment variables."""

    def __init__(self) -> None:
        dotenv.load_dotenv()

    def get_credentials(self) -> Credentials:
        """Retrieve usable Gmail credentials, refreshing or prompting if required."""
        if Credentials is None or Request is None or InstalledAppFlow is None:
            raise RuntimeError(
                "google-auth and google-auth-oauthlib must be installed to use GmailOAuth2Service."
            )
        creds = _load_credentials()
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _store_credentials(creds)
            return creds

        if not creds or not creds.valid:
            client_config = _load_client_config()
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            _store_credentials(creds)
            return creds

        return creds


def main() -> None:
    service = GmailOAuth2Service()
    service.get_credentials()
    print("Gmail credentials updated in environment variables.")


__all__ = ["GmailOAuth2Service"]


if __name__ == "__main__":
    main()
