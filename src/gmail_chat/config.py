"""Application configuration utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load secrets from a .env file if present. The file is expected at the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Strongly typed configuration wrapper."""

    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    google_refresh_token: str | None = field(default_factory=lambda: os.getenv("GOOGLE_REFRESH_TOKEN"))
    google_project_id: str | None = field(default_factory=lambda: os.getenv("GOOGLE_PROJECT_ID"))
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    sentence_transformer_model: str = field(
        default_factory=lambda: os.getenv("SENTENCE_TRANSFORMER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    vector_store_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("VECTOR_STORE_DIR", str((PROJECT_ROOT / "var" / "chroma").resolve()))
        ).expanduser()
    )
    gmail_user_id: str = field(default_factory=lambda: os.getenv("GMAIL_USER_ID", "me"))

    @property
    def google_scopes(self) -> tuple[str, ...]:
        """Return the OAuth scopes required for Gmail access."""
        return (
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
