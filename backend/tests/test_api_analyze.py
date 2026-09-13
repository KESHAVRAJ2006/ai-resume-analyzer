"""End-to-end tests for POST /api/analyze and GET /api/roles.

The embedding model is not loaded here (conftest sets ENABLE_SEMANTIC=false).
A stub index is injected where the three-tier path needs exercising, so the
wiring is covered without a 90MB download. tests/test_semantic.py covers the
real model.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.job_matcher import load_job_roles


class StubEmbeddingIndex:
    """Stands in for EmbeddingIndex, returning a fixed similarity per role.

    Same interface as the real one - score_resume(text) -> {role_id: 0-1} - so
    the route cannot tell the difference.
    """

    def __init__(self, value: float = 0.5) -> None:
        self.value = value
        self.calls: list[str] = []

    def score_resume(self, raw_text: str) -> dict[str, float]:
        self.calls.append(raw_text)
        return {role_id: self.value for role_id in load_job_roles()}


@pytest.fixture
def client() -> TestClient:
    """A client whose lifespan has run, with no embedding model loaded."""
    with TestClient(app) as test_client:
        yield test_client


def _upload(path: Path) -> dict[str, tuple[str, bytes, str]]:
    """Build the multipart payload for a resume file."""
    media = (
        "application/pdf"
        if path.suffix == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return {"file": (path.name, path.read_bytes(), media)}


# --------------------------------------------------------------------------
# GET /api/roles
# --------------------------------------------------------------------------

def test_roles_returns_all_eight(client: TestClient) -> None:
    """The role selector gets every role."""
    response = client.get("/api/roles")
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_roles_include_weighted_skills(client: TestClient) -> None:
    """Each role lists its skills with tier and weight, must-haves first."""
    roles = {role["role_id"]: role for role in client.get("/api/roles").json()}
    backend = roles["backend_developer"]
    assert backend["skills"][0]["weight"] == 3
    weights = [skill["weight"] for skill in backend["skills"]]
    assert weights == sorted(weights, reverse=True)


def test_roles_use_display_names_not_ids(client: TestClient) -> None:
    """The UI shows 'PostgreSQL', never 'postgresql'."""
    roles = {role["role_id"]: role for role in client.get("/api/roles").json()}
    names = {skill["name"] for skill in roles["backend_developer"]["skills"]}
    assert "PostgreSQL" in names
    assert "REST APIs" in names


# --------------------------------------------------------------------------
# POST /api/analyze - the happy path
# --------------------------------------------------------------------------

def test_analyze_returns_a_full_payload(client: TestClient, sample_pdf: Path) -> None:
    """One upload produces score, skills, ranking, gaps and roadmap."""
    response = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "backend_developer"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["target_role"]["role_id"] == "backend_developer"
    assert 0 <= body["target_role"]["score"] <= 100
    assert body["target_role"]["band"] in {"strong", "developing", "early"}
    assert body["skills_found"]
    assert len(body["role_ranking"]) == 8
    assert len(body["roadmap"]) == 4
    assert body["gaps"]["matched"] or body["gaps"]["missing"]


def test_analyze_accepts_docx(client: TestClient, sample_docx: Path) -> None:
    """Both supported formats reach the same pipeline."""
    response = client.post(
        "/api/analyze", files=_upload(sample_docx), data={"target_role": "data_scientist"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["skills_found"]


def test_ranking_is_sorted_and_contains_the_target(
    client: TestClient, sample_pdf: Path
) -> None:
    """The ranking is best-first and always includes the requested role."""
    body = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "ml_engineer"}
    ).json()
    scores = [role["score"] for role in body["role_ranking"]]
    assert scores == sorted(scores, reverse=True)
    assert any(role["role_id"] == "ml_engineer" for role in body["role_ranking"])


def test_target_score_matches_its_entry_in_the_ranking(
    client: TestClient, sample_pdf: Path
) -> None:
    """The hero number and the bar chart must not disagree."""
    body = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "data_analyst"}
    ).json()
    in_ranking = next(
        role for role in body["role_ranking"] if role["role_id"] == "data_analyst"
    )
    assert body["target_role"] == in_ranking


def test_response_carries_the_disclaimer(client: TestClient, sample_pdf: Path) -> None:
    """The 'not a hiring decision' notice travels with the data, not just the UI."""
    body = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "backend_developer"}
    ).json()
    assert "not a hiring decision" in body["meta"]["disclaimer"]


def test_no_personal_attribute_appears_in_the_response(
    client: TestClient, sample_pdf: Path
) -> None:
    """The fixture resume has a name, email and phone; none may be returned."""
    text = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "backend_developer"}
    ).text
    assert "Priya" not in text
    assert "priya.sharma@example.com" not in text
    assert "98765" not in text


# --------------------------------------------------------------------------
# POST /api/analyze - validation and errors
# --------------------------------------------------------------------------

def test_unknown_role_is_rejected(client: TestClient, sample_pdf: Path) -> None:
    """A bad role_id gives 400 and names the fix."""
    response = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "wizard"}
    )
    assert response.status_code == 400
    assert "/api/roles" in response.json()["detail"]


def test_unsupported_extension_is_rejected(client: TestClient, tmp_path: Path) -> None:
    """A .txt upload gives 415 before anything is parsed."""
    path = tmp_path / "resume.txt"
    path.write_text("Python developer", encoding="utf-8")
    response = client.post(
        "/api/analyze",
        files={"file": (path.name, path.read_bytes(), "text/plain")},
        data={"target_role": "backend_developer"},
    )
    assert response.status_code == 415


def test_scanned_pdf_gives_a_clear_422(client: TestClient, blank_pdf: Path) -> None:
    """An image-only PDF gets an actionable message, not a 500."""
    response = client.post(
        "/api/analyze", files=_upload(blank_pdf), data={"target_role": "backend_developer"}
    )
    assert response.status_code == 422
    assert "scanned" in response.json()["detail"].lower()


def test_corrupt_pdf_gives_400(client: TestClient, tmp_path: Path) -> None:
    """Garbage bytes with a .pdf name are a client error, not a server error."""
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a pdf at all, just some bytes" * 10)
    response = client.post(
        "/api/analyze",
        files={"file": (path.name, path.read_bytes(), "application/pdf")},
        data={"target_role": "backend_developer"},
    )
    assert response.status_code == 400


def test_empty_file_is_rejected(client: TestClient) -> None:
    """A zero-byte upload gives 400 rather than a confusing parse error."""
    response = client.post(
        "/api/analyze",
        files={"file": ("resume.pdf", b"", "application/pdf")},
        data={"target_role": "backend_developer"},
    )
    assert response.status_code == 400


def test_oversized_file_is_rejected(client: TestClient) -> None:
    """A file past the configured cap gives 413 and is not parsed."""
    settings = get_settings()
    payload = b"%PDF-1.4\n" + b"x" * (settings.max_upload_bytes + 1024)
    response = client.post(
        "/api/analyze",
        files={"file": ("huge.pdf", payload, "application/pdf")},
        data={"target_role": "backend_developer"},
    )
    assert response.status_code == 413


def test_missing_target_role_is_a_validation_error(
    client: TestClient, sample_pdf: Path
) -> None:
    """FastAPI rejects the request before our handler runs."""
    response = client.post("/api/analyze", files=_upload(sample_pdf))
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Temp file cleanup - the requirement that must hold on every path
# --------------------------------------------------------------------------

def _temp_files() -> set[Path]:
    """Return whatever is currently sitting in the upload directory."""
    return set(get_settings().temp_path.iterdir())


@pytest.mark.parametrize(
    "role, filename, payload, media",
    [
        ("backend_developer", "ok.pdf", None, "application/pdf"),
        ("wizard", "ok.pdf", None, "application/pdf"),
        ("backend_developer", "broken.pdf", b"garbage bytes here" * 20, "application/pdf"),
        ("backend_developer", "empty.pdf", b"", "application/pdf"),
    ],
)
def test_temp_file_is_always_deleted(
    client: TestClient, sample_pdf: Path, role: str, filename: str,
    payload: bytes | None, media: str,
) -> None:
    """Success, bad role, corrupt file and empty file all leave no file behind."""
    before = _temp_files()
    content = sample_pdf.read_bytes() if payload is None else payload

    client.post(
        "/api/analyze",
        files={"file": (filename, content, media)},
        data={"target_role": role},
    )

    assert _temp_files() == before, "an uploaded file survived the request"


def test_temp_file_is_deleted_even_when_the_pipeline_crashes(
    sample_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The finally block must survive an exception we never anticipated."""
    import app.api.routes.analyze as analyze_module

    def _explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated failure deep in the pipeline")

    monkeypatch.setattr(analyze_module, "_run_pipeline", _explode)

    before = _temp_files()
    # raise_server_exceptions=False makes the client behave like a real browser
    # and receive the 500, instead of re-raising the error into the test.
    with TestClient(app, raise_server_exceptions=False) as crash_client:
        response = crash_client.post(
            "/api/analyze",
            files=_upload(sample_pdf),
            data={"target_role": "backend_developer"},
        )

    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]
    assert _temp_files() == before, "a crash leaked an uploaded file"


# --------------------------------------------------------------------------
# The semantic tier, via a stub
# --------------------------------------------------------------------------

def test_without_the_model_the_response_says_so(
    client: TestClient, sample_pdf: Path
) -> None:
    """semantic_enabled is false and semantic_score is null in two-tier mode."""
    body = client.post(
        "/api/analyze", files=_upload(sample_pdf), data={"target_role": "backend_developer"}
    ).json()
    assert body["meta"]["semantic_enabled"] is False
    assert body["target_role"]["semantic_score"] is None


def test_with_an_index_the_third_tier_is_used(
    client: TestClient, sample_pdf: Path
) -> None:
    """Injecting an index switches the route to the full three-term formula."""
    stub = StubEmbeddingIndex(value=0.5)
    client.app.state.ml_models["embeddings"] = stub
    try:
        body = client.post(
            "/api/analyze",
            files=_upload(sample_pdf),
            data={"target_role": "backend_developer"},
        ).json()
    finally:
        client.app.state.ml_models.pop("embeddings", None)

    assert stub.calls, "the route never called the embedding index"
    assert body["meta"]["semantic_enabled"] is True
    assert body["target_role"]["semantic_score"] == pytest.approx(0.5)


def test_health_reports_model_readiness(client: TestClient) -> None:
    """/api/health tells an operator whether the semantic tier is live."""
    assert client.get("/api/health").json()["embeddings_ready"] is False

    client.app.state.ml_models["embeddings"] = StubEmbeddingIndex()
    try:
        assert client.get("/api/health").json()["embeddings_ready"] is True
    finally:
        client.app.state.ml_models.pop("embeddings", None)
