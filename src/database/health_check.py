"""Utility to confirm the local Weaviate stack is reachable."""

from __future__ import annotations

import json  # present metadata in a readable format
import sys  # exit codes and stderr output
from typing import Optional  # type hints for optional metadata

import weaviate  # client SDK for Weaviate operations

from .config import load_weaviate_settings  # reuse environment-based settings


def _format_meta(meta: Optional[dict]) -> str:
    if not meta:
        return "{}"
    try:
        return json.dumps(meta, indent=3, sort_keys=True)
    except (
        TypeError,
        ValueError,
    ):  # fall back if meta contains non-serialisable entries
        return str(meta)


def main() -> int:
    settings = load_weaviate_settings()
    headers = settings.headers

    try:
        with weaviate.connect_to_local(
            host=settings.host,
            port=settings.port,
            grpc_port=settings.grpc_port,
            headers=headers,
        ) as client:
            is_live = client.is_live()
            is_ready = client.is_ready()
            meta = client.get_meta()
    except Exception as exc:  # surface connectivity failures clearly
        print(f"[health-check] Failed to contact Weaviate: {exc}", file=sys.stderr)
        return 1

    if not (is_live and is_ready):
        print(
            "[health-check] Weaviate responded but reported an unhealthy status: "
            f"live={is_live}, ready={is_ready}",
            file=sys.stderr,
        )
        return 2

    print("[health-check] Weaviate is live and ready.")
    print(f"  host: {settings.host}:{settings.port}")
    print(f"  grpc_port: {settings.grpc_port}")
    print("  meta:")
    print(_format_meta(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
