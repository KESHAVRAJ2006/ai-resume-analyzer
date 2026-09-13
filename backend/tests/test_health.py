"""Phase 1 smoke tests: the app boots and the health route answers."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    """GET /api/health responds 200 with status 'ok'."""
    # `with` triggers the lifespan handler, same as a real server start.
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["embeddings_ready"] is False  # no model loaded until Phase 5


def test_root_returns_pointers() -> None:
    """GET / returns links instead of a 404."""
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["health"] == "/api/health"
