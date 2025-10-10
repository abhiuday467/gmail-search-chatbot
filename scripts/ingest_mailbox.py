"""CLI for ingesting Gmail messages into the vector store."""

from __future__ import annotations

import argparse
import logging

from gmail_chat.config import get_settings
from gmail_chat.gmail_client import GmailClient
from gmail_chat.ingestion import ingest_mailbox
from gmail_chat.vector_store import VectorStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="", help="Gmail search query to filter messages.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of messages to ingest.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    gmail_client = GmailClient(settings=settings)
    vector_store = VectorStore(settings=settings)

    count = ingest_mailbox(
        vector_store=vector_store,
        gmail_client=gmail_client,
        query=args.query,
        limit=args.limit,
    )
    logging.info("Ingested %s messages into the vector store.", count)


if __name__ == "__main__":
    main()
