"""End-to-end tests for POST /api/report.

The important one is the round trip: analyse a real file, post the response
straight back, and get a PDF. That is exactly what the browser does, and it is
what catches a schema drift between the two endpoints.
"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """A client whose lifespan has run, with no embedding model loaded."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def analysis(client: TestClient, sample_pdf: Path) -> dict:
    """Run a real analysis and return its payload."""
    response = client.post(
        "/api/analyze",
        files={"file": (sample_pdf.name, sample_pdf.read_bytes(), "application/pdf")},
        data={"target_role": "backend_developer"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_analyze_response_round_trips_into_a_pdf(
    client: TestClient, analysis: dict
) -> None:
    """The output of /api/analyze is valid input to /api/report, unmodified."""
    response = client.post("/api/report", json=analysis)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_report_content_matches_the_analysis(client: TestClient, analysis: dict) -> None:
    """The PDF actually contains this analysis, not a template."""
    response = client.post("/api/report", json=analysis)
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert analysis["target_role"]["role_name"] in text
    assert f"{round(analysis['target_role']['score'])}%" in text


def test_content_disposition_offers_a_safe_filename(
    client: TestClient, analysis: dict
) -> None:
    """The browser is told to download it, under a name we control."""
    response = client.post("/api/report", json=analysis)
    disposition = response.headers["content-disposition"]

    assert disposition.startswith("attachment;")
    assert "resume-analysis-backend_developer-" in disposition
    assert ".pdf" in disposition


def test_filename_header_is_exposed_to_the_browser(
    client: TestClient, analysis: dict
) -> None:
    """Without this header a cross-origin fetch cannot read the filename."""
    response = client.post("/api/report", json=analysis)
    assert "Content-Disposition" in response.headers["access-control-expose-headers"]


def test_report_carries_no_personal_data(client: TestClient, analysis: dict) -> None:
    """The fixture resume has a name, email and phone; none reach the PDF."""
    response = client.post("/api/report", json=analysis)
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()

    assert "priya" not in text
    assert "example.com" not in text
    assert "98765" not in text


def test_malformed_body_is_rejected(client: TestClient) -> None:
    """A truncated payload fails validation before reportlab runs."""
    response = client.post("/api/report", json={"target_role": {"role_id": "x"}})
    assert response.status_code == 422


def test_empty_body_is_rejected(client: TestClient) -> None:
    """No body at all is a validation error, not a 500."""
    assert client.post("/api/report", json={}).status_code == 422


def test_out_of_range_score_is_rejected(client: TestClient, analysis: dict) -> None:
    """The schema pins score to 0-100, so a nonsense value cannot be rendered."""
    payload = {**analysis, "target_role": {**analysis["target_role"], "score": 150}}
    assert client.post("/api/report", json=payload).status_code == 422
