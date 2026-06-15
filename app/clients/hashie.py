import requests

from app.clients._retry import retry_request
from app.core.config import settings


def chat(text: str, language: str = "eng", conversation_id: str | None = None) -> tuple[str, str | None]:
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    payload = {"message": text, "country": settings.HASHIE_COUNTRY, "max_new_tokens": 512}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    def _req():
        return requests.post(settings.HASHIE_CHAT_URL, headers=headers, json=payload, timeout=300)

    try:
        response = retry_request(_req)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise Exception("AI agent endpoint timeout — check if the service is reachable")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to AI agent endpoint — check network")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Agent API error: {e}")

    data = response.json()
    returned_id = data.get("conversation_id") or conversation_id
    return data["response"], returned_id
