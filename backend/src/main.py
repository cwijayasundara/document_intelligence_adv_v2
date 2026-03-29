"""Uvicorn entry point for the PE Document Intelligence Platform."""

import uvicorn

from src.api.app import create_app
from src.config.settings import get_settings

settings = get_settings()
app = create_app(database_url=settings.database_url)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
