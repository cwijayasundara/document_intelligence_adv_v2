"""Pydantic settings classes for typed, validated configuration.

Loads values from config.yml (storage, chunking, bulk, RAG defaults)
and .env (secrets, database URL, API keys).
"""

import functools
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_config() -> dict[str, object]:
    """Load config.yml from the backend directory."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config.yml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class StorageSettings(BaseSettings):
    """File storage path configuration."""

    upload_dir: str = "./data/upload"
    parsed_dir: str = "./data/parsed"
    summary_dir: str = "./data/summary"
    extraction_dir: str = "./data/extraction"
    schemas_dir: str = "./schemas"


class ChunkingSettings(BaseSettings):
    """Text chunking parameters for RAG ingestion."""

    max_tokens: int = 512
    overlap_tokens: int = 100


class BulkSettings(BaseSettings):
    """Bulk processing configuration."""

    concurrent_documents: int = 3
    max_retries: int = 3
    retry_delay_seconds: int = 30


class RAGSettings(BaseSettings):
    """RAG search defaults."""

    default_search_mode: str = "hybrid"
    default_alpha: float = 0.5
    top_k: int = 5


class AppSettings(BaseSettings):
    """Root application settings combining env vars and config.yml values.

    Secrets (no defaults) are loaded from environment variables.
    Non-secret config is loaded from config.yml with sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Secrets from environment variables (no defaults -- validation fails if missing)
    openai_api_key: str = Field(..., description="OpenAI API key")
    reducto_api_key: str = Field(..., description="Reducto API key")
    reducto_base_url: str = Field(..., description="Reducto API base URL")
    database_url: str = Field(..., description="PostgreSQL async connection URL")
    weaviate_url: str = Field(..., description="Weaviate server URL")
    openai_model: str = Field(..., description="OpenAI model identifier")

    # Logging (configurable via LOG_LEVEL env var, defaults to INFO)
    log_level: str = Field(default="INFO", description="Root log level")

    # LLM retry/fallback
    openai_fallback_model: str = Field(default="", description="Fallback model for retries")
    llm_max_retries: int = Field(default=3, description="Max LLM call retries")
    llm_base_delay: float = Field(default=1.0, description="Base delay for LLM retry backoff")

    # Agent rate limiting
    agent_max_llm_calls: int = Field(default=50, description="Max LLM calls per pipeline run")
    agent_max_tool_calls: int = Field(default=200, description="Max tool calls per pipeline run")

    # Database connection pool
    db_pool_size: int = Field(default=5, description="Main DB connection pool size")
    db_max_overflow: int = Field(default=5, description="Main DB max overflow connections")
    audit_pool_size: int = Field(default=2, description="Audit DB connection pool size")
    audit_max_overflow: int = Field(default=1, description="Audit DB max overflow connections")

    # Observability
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    otel_service_name: str = Field(default="doc-intel", description="OTel service name")
    otel_exporter_endpoint: str = Field(default="", description="OTel collector endpoint")

    # Nested config from config.yml
    storage: StorageSettings = Field(default_factory=StorageSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    bulk: BulkSettings = Field(default_factory=BulkSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)

    @property
    def database_url_sync(self) -> str:
        """Sync postgres URL for checkpointer (strips +asyncpg driver suffix)."""
        _async_scheme = "postgresql+asyncpg"
        _sync_scheme = "postgresql"
        return self.database_url.replace(_async_scheme, _sync_scheme, 1)

    @classmethod
    def from_yaml_and_env(cls, env_file: str | None = None) -> "AppSettings":
        """Create settings from config.yml merged with .env values."""
        yaml_data = _load_yaml_config()

        storage_data = yaml_data.get("storage", {})
        chunking_data = yaml_data.get("chunking", {})
        bulk_data = yaml_data.get("bulk", {})
        rag_data = yaml_data.get("rag", {})

        storage = StorageSettings(**storage_data) if storage_data else StorageSettings()
        chunking = ChunkingSettings(**chunking_data) if chunking_data else ChunkingSettings()
        bulk = BulkSettings(**bulk_data) if bulk_data else BulkSettings()
        rag = RAGSettings(**rag_data) if rag_data else RAGSettings()

        kwargs: dict[str, object] = {
            "storage": storage,
            "chunking": chunking,
            "bulk": bulk,
            "rag": rag,
        }
        if env_file is not None:
            kwargs["_env_file"] = env_file

        return cls(**kwargs)


@functools.lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings singleton."""
    return AppSettings.from_yaml_and_env()
