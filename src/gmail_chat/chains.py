"""LangChain runnable pipelines."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from .config import Settings, get_settings
from .vector_store import VectorStore


def _format_documents(documents: list[Any]) -> str:
    formatted = []
    for doc in documents:
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        subject = metadata.get("subject") or metadata.get("title") or "Untitled email"
        snippet = metadata.get("snippet", "").strip()
        formatted.append(f"Subject: {subject}\nSnippet: {snippet}\n\n{doc.page_content}".strip())
    return "\n\n---\n\n".join(formatted)


def build_retrieval_chain(
    vector_store: VectorStore,
    settings: Settings | None = None,
) -> Runnable:
    """Create a retrieval augmented generation chain backed by the vector store."""
    settings = settings or get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required to build the retrieval chain.")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=settings.openai_api_key,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a helpful assistant that answers questions about a Gmail mailbox. "
                    "Use the provided email context when it is relevant. If the answer cannot be "
                    "determined from the context, say so explicitly."
                ),
            ),
            ("human", "Question: {question}\n\nEmail context:\n{context}"),
        ]
    )

    retriever = RunnableLambda(lambda question: vector_store.similarity_search(question, k=4))

    chain = (
        {
            "question": RunnablePassthrough(),
            "context": RunnablePassthrough() | retriever | RunnableLambda(_format_documents),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
