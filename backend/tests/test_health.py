from fastapi.testclient import TestClient

from app.db import database_is_reachable
from app.main import APP_VERSION, create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": APP_VERSION}


def test_unknown_route_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/does-not-exist")

    assert response.status_code == 404


def test_ready_when_database_is_reachable() -> None:
    app = create_app()
    app.dependency_overrides[database_is_reachable] = lambda: True
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_not_ready_when_database_is_unreachable() -> None:
    app = create_app()
    app.dependency_overrides[database_is_reachable] = lambda: False
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}
