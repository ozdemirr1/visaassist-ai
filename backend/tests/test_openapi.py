"""The API description documents the checklist's error responses."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_checklist_documents_its_error_responses() -> None:
    schema = TestClient(create_app()).get("/openapi.json").json()
    responses = schema["paths"]["/checklist"]["get"]["responses"]
    assert {"200", "404", "422", "503"} <= responses.keys()
