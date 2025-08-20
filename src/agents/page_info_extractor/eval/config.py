# page_info_extractor/eval/config.py
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file_path() -> str:
    # Resolve the .env located at project root: page_info_extractor/.env
    # This file lives at page_info_extractor/eval/config.py
    return str(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    """Project configuration loaded via pydantic-settings.
    Environment variable names are explicit via Field(..., validation_alias=...)
    and also read from page_info_extractor/.env by default.
    """

    # Model & API
    model: str = Field(default="gemini-2.5-flash", validation_alias="GENAI_MODEL")
    # Concurrency / timeouts
    max_concurrency: int = Field(default=10, validation_alias="MAX_CONCURRENCY")
    request_timeout_s: int = Field(default=60, validation_alias="REQUEST_TIMEOUT_S")
    max_retries: int = Field(default=4, validation_alias="MAX_RETRIES")
    # I/O
    pages_dir: Path = Field(default=Path("../crawler/pages"), validation_alias="PAGES_DIR")
    output_jsonl: Path = Field(default=Path("./eval_result.jsonl"), validation_alias="OUTPUT_JSONL")
    # Limits
    max_output_tokens: int = Field(default=1024, validation_alias="MAX_OUTPUT_TOKENS")
    temperature: float = Field(default=0.0, validation_alias="TEMPERATURE")
    max_html_bytes: int = Field(default=2_000_000, validation_alias="MAX_HTML_BYTES")

    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    # HTML preprocessing
    preprocess_html: bool = Field(default=True, validation_alias="PREPROCESS_HTML")
    
    model_config = SettingsConfigDict(env_file=_env_file_path(), env_file_encoding="utf-8")

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        # Normalize to absolute paths (resolve relative to the eval/ folder location)
        base_dir = Path(__file__).resolve().parent
        s.pages_dir = (base_dir / s.pages_dir).resolve()
        s.output_jsonl = (base_dir / s.output_jsonl).resolve()
        return s
