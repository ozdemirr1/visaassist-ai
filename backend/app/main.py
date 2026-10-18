"""FastAPI application entry point."""

from fastapi import FastAPI

APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory keeps app construction in one place, so tests and later
    configuration (database, routers) can create isolated instances.
    """
    app = FastAPI(title="VisaAssist AI API", version=APP_VERSION)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Liveness check: the API process is up and answering requests."""
        return {"status": "ok", "version": APP_VERSION}

    return app


app = create_app()
