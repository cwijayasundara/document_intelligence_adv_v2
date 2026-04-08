"""Uvicorn entry point for the PE Document Intelligence Platform."""

import logging
import os
import sys

import uvicorn

from src.api.app import create_app
from src.config.settings import get_settings

LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str) -> None:
    """Configure root logger with structured format and level."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )
    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("weaviate").setLevel(logging.WARNING)


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Export API keys to environment so third-party SDKs (OpenAI, LangChain) can find them
os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

# LangSmith tracing — auto-traces all LangChain/DeepAgents LLM calls
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    logger.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)
else:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")


logger.info(
    "Starting PE Document Intelligence Platform (log_level=%s)",
    settings.log_level,
)

app = create_app(database_url=settings.database_url)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
