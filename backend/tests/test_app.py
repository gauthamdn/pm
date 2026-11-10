import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_health_returns_api_response(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Hello from FastAPI."}


@pytest.mark.parametrize(
    ("path", "content_type", "content"),
    [
        ("/", "text/html", "Hello world."),
        ("/app.js", "javascript", "/api/health"),
        ("/styles.css", "text/css", "#032147"),
    ],
)
def test_serves_static_files(client, path, content_type, content):
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    assert content in response.text


def test_unknown_api_route_is_not_the_homepage(client):
    assert client.get("/api/missing").status_code == 404
