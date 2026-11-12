"""Destination facts: every fact cites an official source of its own destination (NFR-03)."""

from fastapi.testclient import TestClient

from app.destinations import DestinationData, load_destinations, problems
from app.main import create_app
from app.requirements.loader import load_requirement_data
from app.sources.registry import load_registry


def test_the_repository_file_loads_and_covers_the_pilot_destinations() -> None:
    data = load_destinations()
    assert [d.id for d in data.destinations] == load_requirement_data().destinations
    for destination in data.destinations:
        assert {"where", "when", "biometrics", "fee"} <= {f.id for f in destination.facts}


def test_a_fact_with_a_source_of_another_destination_is_reported() -> None:
    data = load_destinations()
    raw = data.model_dump(mode="json")
    raw["destinations"][0]["facts"][0]["source"]["source_id"] = "no-visitors-visa-tr"
    raw["destinations"][1]["facts"][0]["source"]["source_id"] = "nowhere"
    found = problems(DestinationData.model_validate(raw), load_registry())
    assert found == ["NL.stay: source is about NO", "NO.stay: unknown source nowhere"]


def test_the_api_returns_facts_in_the_interface_language_with_source_links() -> None:
    client = TestClient(create_app())
    turkish = client.get("/destinations").json()
    assert turkish["checked_on"] == "2026-11-12"
    netherlands = turkish["destinations"][0]
    assert netherlands["id"] == "NL" and netherlands["schengen"] is True
    when = next(f for f in netherlands["facts"] if f["id"] == "when")
    assert when["title"] == "Ne zaman başvurulur" and "15 takvim günü" in when["text"]
    assert when["source"]["url"].startswith("https://www.netherlandsworldwide.nl/")
    assert when["source"]["section"] == "Step 3: Make an appointment"

    english = client.get("/destinations", params={"lang": "en"}).json()
    fee = next(f for f in english["destinations"][1]["facts"] if f["id"] == "fee")
    assert "EUR 90" in fee["text"]
    assert client.get("/destinations", params={"lang": "de"}).status_code == 422
