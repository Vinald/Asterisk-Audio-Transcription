"""AI agent service."""

from app.clients.hashie import chat as _chat


def chat(
    text: str,
    language: str = "eng",
    conversation_id: str | None = None,
) -> tuple[str, str]:
    return _chat(text, language=language, conversation_id=conversation_id)
