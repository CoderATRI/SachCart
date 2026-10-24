from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TINYFISH_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "postgresql+psycopg://sachcart:sachcart@127.0.0.1:5432/sachcart"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_PUBLIC_URL: str = "http://127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "sachcart-evidence"
    CLAUDE_MODEL: str = "claude-sonnet-5-5"
    SACHCART_API_KEYS: str = ""
    CAPTURE_EVIDENCE: bool = False
    MAX_PARALLEL_AUDITS: int = 4
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
