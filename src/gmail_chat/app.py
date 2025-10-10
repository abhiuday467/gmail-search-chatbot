"""Gradio application entrypoint."""

from __future__ import annotations

import gradio as gr

from .chains import build_retrieval_chain
from .config import Settings, get_settings
from .vector_store import VectorStore


def create_app(settings: Settings | None = None) -> gr.Blocks:
    """Create and configure the Gradio interface."""
    settings = settings or get_settings()
    vector_store = VectorStore(settings=settings)
    chain = build_retrieval_chain(vector_store=vector_store, settings=settings)

    def answer_question(question: str) -> str:
        if not question.strip():
            return "Please enter a question about your mailbox."
        return chain.invoke(question.strip())

    with gr.Blocks(title="Gmail Search Chatbot") as demo:
        gr.Markdown(
            "## Gmail Search Chatbot\n"
            "Ask questions about your Gmail mailbox. Ensure you have ingested mail before querying."
        )
        with gr.Row():
            question = gr.Textbox(label="Question", placeholder="What emails mention quarterly reports?")
        answer = gr.Textbox(label="Answer", lines=12)
        submit = gr.Button("Ask")

        submit.click(fn=answer_question, inputs=question, outputs=answer)
        question.submit(fn=answer_question, inputs=question, outputs=answer)
    return demo


def launch() -> None:
    """Launch the Gradio demo."""
    app = create_app()
    app.queue().launch()


if __name__ == "__main__":
    launch()
