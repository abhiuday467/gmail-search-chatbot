"""Configuration helpers for connecting to external services."""

from __future__ import annotations

import os  # standard library helpers for environment access
from dataclasses import dataclass  # structured container for settings
from typing import Dict, Optional  # typing support for optional headers

from dotenv import load_dotenv  # load variables from a local .env file

load_dotenv()


@dataclass(frozen=True)
class WeaviateSettings:
    host: str
    port: int
    grpc_port: int
    api_key: Optional[str] = None

    @property
    def headers(self) -> Optional[Dict[str, str]]:
        if self.api_key:
            return {"X-API-KEY": self.api_key}
        return None


def load_weaviate_settings() -> WeaviateSettings:
    """Load connection details for the Weaviate instance."""
    return WeaviateSettings(
        host=os.getenv("WEAVIATE_HOST", "localhost"),
        port=_get_int("WEAVIATE_PORT", 8080),
        grpc_port=_get_int("WEAVIATE_GRPC_PORT", 50051),
        api_key=os.getenv("WEAVIATE_API_KEY"),
    )


def _get_int(env_var: str, default: int) -> int:
    """Fetch an integer environment variable with a fallback."""
    raw_value = os.getenv(env_var)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:  # provide clear feedback on misconfiguration
        raise ValueError(
            f"Environment variable {env_var} must be an integer, got {raw_value!r}."
        ) from exc


__all__ = ["WeaviateSettings", "load_weaviate_settings"]
