"""Uvicorn entry point for the PE Document Intelligence Platform."""

import uvicorn

from src.api.app import create_app
from src.config.settings import get_settings


def main() -> None:
    """Start the application server."""
    settings = get_settings()
    app = create_app(database_url=settings.database_url)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
