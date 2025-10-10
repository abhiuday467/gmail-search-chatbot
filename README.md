# Gmail Chat Search App

This project sketches a Gradio chat application that can search your Gmail inbox via a vector database, using the `uv` build tool and LangChain for retrieval orchestration.

---

## 1. Environment Bootstrapping

- **Initialize with `uv`**: `uv init gmail-chat` (or run inside the repo). This creates `pyproject.toml`, `uv.lock`, and a `src/` layout.
- **Core dependencies**: add `langchain`, `gradio`, `chromadb` or `weaviate-client`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `python-dotenv`, and an embedding provider such as `sentence-transformers` or `openai`. Pin versions in `pyproject.toml`, then `uv sync`.
- **Project layout**:
  ```
  gmail-chat/
    src/
      gmail_chat/
        __init__.py
        config.py
        gmail_client.py
        ingestion.py
        vector_store.py
        chains.py
        app.py
    scripts/
      ingest_mailbox.py
    tests/
  ```
- **Configuration management**: keep secrets in a `.env` file (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, embedding API keys, vector DB URLs), loaded via `python-dotenv`.

---

## 2. Gmail Ingestion Module

- **OAuth setup**: create a Google Cloud project, enable Gmail API, configure OAuth consent (Desktop or Web application), and download the `client_secret.json`.
- **Token flow**: use `InstalledAppFlow` from `google-auth-oauthlib` to prompt the user for consent; cache the resulting `token.json` data for refresh support.
- **Message retrieval**:
  - Paginate through `users.messages.list` to collect message IDs.
  - Fetch each message via `users.messages.get(format="full")`.
  - Normalize relevant parts (subject, snippet, plain-text body, attachments metadata) into LangChain `Document` objects with metadata (message ID, thread ID, labels, timestamps).
- **Incremental sync**: persist the last synced history ID or message IDs to skip already indexed emails on subsequent runs.

---

## 3. Embedding & Vector Storage Pipeline

- **Embedding selection**: pick a model supported by LangChain (e.g., `OpenAIEmbeddings`, `HuggingFaceEmbeddings`) based on latency, cost, and data policies.
- **Batch processing**: chunk long emails using `RecursiveCharacterTextSplitter` (preserve headers, label as necessary), compute embeddings via the chosen model.
- **Vector database**:
  - **Chroma**: run a local persistent collection (`persist_directory="vector_store"`).
  - **Weaviate**: configure remote endpoint, API key, schema with email fields.
- **Repository abstraction**: implement helper functions `init_store()`, `upsert_documents(documents)`, and `query_store(query, k)` to isolate Chroma vs. Weaviate differences.
- **Ingestion script**: orchestrate Gmail fetch → document transformation → embedding → vector upsert; expose via `scripts/ingest_mailbox.py`.

---

## 4. Background Sync & Maintenance

- **Scheduling**: decide on manual runs, cron jobs, or a lightweight task queue to call the ingestion script periodically.
- **Delta handling**: leverage Gmail history IDs (via `users.history.list`) to capture only new/updated messages since the last sync.
- **Error resilience**: add retry/backoff for API quotas, log failures, and persist checkpoints so the ingestion resumes gracefully.

---

## 5. LangChain Retrieval Chains

- **Retriever setup**: wrap the vector store with LangChain’s `VectoreStoreRetriever` (or `SelfQueryRetriever` if filtering by metadata).
- **Prompting**: craft system + human prompts that summarize user questions, request supporting snippets, and format answers with references (subject, date, direct Gmail link using message ID).
- **Conversation handling**: for chatting over Gmail, use `ConversationalRetrievalChain` with a memory module (e.g., `ConversationBufferMemory`) to maintain context.
- **Tooling**: expose helper functions `build_retriever()`, `build_chain()` in `chains.py`.

---

## 6. Gradio Frontend

- **UI skeleton**: create `app.py` with `gr.ChatInterface` or custom Blocks layout for message input/output, optional search filters (labels, date ranges).
- **Session state**: manage user conversation history (pass to LangChain chain), render retrieved source snippets with metadata.
- **Configuration controls**: optionally expose inputs for top-k results, embedding model choice, or a sync trigger button.
- **Launch script**: `uv run python -m gmail_chat.app` to start the Gradio server locally.

---

## 7. Testing & Validation

- **Unit tests**: cover Gmail parsing logic, embedding chunking, and vector store writes/queries under `tests/`.
- **Integration checks**: mock Gmail API responses for deterministic tests; run sample ingestion against a limited mailbox (or cached fixtures).
- **Manual QA checklist**: validate OAuth login, ingestion completion, search relevance, and UI display of references before production use.

---

## 8. Deployment & Operational Notes

- **Packaging**: rely on `uv lock` for reproducible environments; optionally ship Dockerfile that wraps `uv` to install dependencies.
- **Secrets handling**: keep OAuth tokens and API keys outside version control (e.g., `.env`, secret manager).
- **Hosting considerations**: for remote deployment, configure OAuth redirect URIs, ensure vector store persistence, and secure Gradio with auth (e.g., `gradio.Auth` or reverse proxy).
- **Observability**: add logging around Gmail sync counts, embedding latency, and query performance; monitor quotas and error rates.

---

With this structure in place, the next steps are to generate Google OAuth credentials, initialize the `uv` project scaffold, and start implementing the ingestion and vector store modules.
