"""FastAPI application entry point."""

from typing import Annotated

from fastapi import Depends, FastAPI, Response, status

from app.db import database_is_reachable

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

    @app.get("/health/ready", tags=["system"])
    def ready(
        response: Response,
        database_ok: Annotated[bool, Depends(database_is_reachable)],
    ) -> dict[str, str]:
        """Readiness check: the API can reach its database."""
        if not database_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unavailable", "database": "unreachable"}
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
