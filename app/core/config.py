from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Required — startup fails with a clear error if these are missing
    AUTH_TOKEN: str   # Sunbird AI API credential (STT, TTS, language-ID)
    API_TOKEN: str    # Bearer token for our own /api/v1/ endpoints
    DATABASE_URL: str

    # Sunbird AI endpoints
    STT_URL: str = "https://api.sunbird.ai/tasks/modal/stt"
    TTS_URL: str = "https://api.sunbird.ai/tasks/modal/tts"
    LANGUAGE_ID_URL: str = "https://api.sunbird.ai/tasks/language_id"

    # Hashie AI agent
    HASHIE_CHAT_URL: str = "https://sb-modal-ws--hashie-medgemma-service-medgemmaservice-chat.modal.run"
    HASHIE_COUNTRY: str = "Uganda"

    # Dashboard / session
    DASHBOARD_SECRET_KEY: str = "change-this-in-production"
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "changeme"

    # Server
    PORT: int = 8000

    # Pipeline retries
    MAX_RETRIES: int = 5
    RETRY_DELAY: int = 3

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sunbird_headers(self) -> dict:
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {self.AUTH_TOKEN}",
        }

    @property
    def speakers(self) -> dict:
        return {
            "lug": 248,
            "eng": 248,
            "ach": 241,
            "teo": 242,
            "nyn": 243,
            "lgg": 245,
            "swa": 246,
        }

    # Sunbird language-ID returns full names; dialplan passes full names too.
    # This method resolves either a full name or a code to the correct speaker ID.
    def speaker_for(self, language: str) -> int:
        _name_to_code = {
            "English": "eng",
            "Luganda": "lug",
            "Acholi": "ach",
            "Ateso": "teo",
            "Runyankore": "nyn",
            "Lugbara": "lgg",
            "Swahili": "swa",
        }
        code = _name_to_code.get(language, language)
        return self.speakers.get(code, 248)


settings = Settings()

_INSECURE_DEFAULTS = {
    "DASHBOARD_SECRET_KEY": "change-this-in-production",
    "DASHBOARD_PASSWORD": "changeme",
}

def _check_insecure_defaults() -> None:
    import os
    if os.getenv("HASH_PBX_ALLOW_INSECURE_DEFAULTS"):
        return
    problems = [
        f"{var} is still set to its insecure default value"
        for var, default in _INSECURE_DEFAULTS.items()
        if getattr(settings, var) == default
    ]
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure default credentials:\n"
            + "\n".join(f"  • {p}" for p in problems)
            + "\nSet these in your .env file, or set HASH_PBX_ALLOW_INSECURE_DEFAULTS=1 "
            "to bypass this check (tests / local dev only)."
        )

_check_insecure_defaults()
