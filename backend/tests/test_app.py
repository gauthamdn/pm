import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Kanban Studio</h1>")
    assets = tmp_path / "_next" / "static"
    assets.mkdir(parents=True)
    (assets / "app.js").write_text('console.log("Kanban Studio");')
    (assets / "styles.css").write_text("body { color: #032147; }")
    (tmp_path / "404.html").write_text("Page not found")
    with TestClient(create_app(tmp_path)) as client:
        yield client


def test_health_returns_api_response(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Hello from FastAPI."}


@pytest.mark.parametrize(
    ("path", "content_type", "content"),
    [
        ("/", "text/html", "Kanban Studio"),
        ("/_next/static/app.js", "javascript", "Kanban Studio"),
        ("/_next/static/styles.css", "text/css", "#032147"),
    ],
)
def test_serves_static_files(client, path, content_type, content):
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    assert content in response.text


def test_unknown_api_route_is_not_the_homepage(client):
    assert client.get("/api/missing").status_code == 404


def test_missing_asset_returns_404(client):
    assert client.get("/_next/static/missing.js").status_code == 404


def test_unknown_page_returns_exported_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.text == "Page not found"
