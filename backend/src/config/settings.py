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
    database_url: str = Field(..., description="PostgreSQL async connection URL")
    weaviate_url: str = Field(..., description="Weaviate server URL")
    openai_model: str = Field(..., description="OpenAI model identifier")

    # Nested config from config.yml
    storage: StorageSettings = Field(default_factory=StorageSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    bulk: BulkSettings = Field(default_factory=BulkSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)

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
