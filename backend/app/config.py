from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+psycopg://devsphere@127.0.0.1:55433/devsphere"
    jwt_secret: str
    app_origin: str = "http://localhost:8010"
    secure_cookie: bool = False
    registration_enabled: bool = True
    provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    openai_api_key: str = ""
    openai_model: str = ""
    model_timeout: int = 480
    model_concurrency: int = 1
    model_tokens: int = 6500
    worker_enabled: bool = True
    docker_context: str = "colima-devsphere"
    sandbox_enabled: bool = True
    sandbox_timeout: int = 90
    max_files: int = 60
    max_file_bytes: int = 100000
    max_project_bytes: int = 750000
    public_demo: bool = False


@lru_cache
def settings():
    result = Settings()
    if len(result.jwt_secret) < 32:
        raise ValueError("JWT_SECRET must contain at least 32 characters")
    return result
