import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "db.sqlite3")) as client:
        yield client


def login(client):
    return client.post(
        "/api/session", json={"username": "user", "password": "password"}
    )


def test_requires_a_valid_session(client):
    response = client.get("/api/session")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    client.cookies.set(auth.SESSION_COOKIE, "forged-token")
    assert client.get("/api/session").status_code == 401
    assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [("user", "wrong"), ("wrong", "password"), ("", ""), ("User", "password")],
)
def test_rejects_invalid_credentials(client, username, password):
    response = client.post(
        "/api/session", json={"username": username, "password": password}
    )
    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    assert client.get("/api/session").status_code == 401


def test_login_sets_opaque_cookie_and_restores_user(client):
    response = login(client)
    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert f"Max-Age={auth.SESSION_MAX_AGE}" in cookie
    assert client.cookies[auth.SESSION_COOKIE] not in ("user", "password")
    assert response.headers["cache-control"] == "no-store"
    session = client.get("/api/session")
    assert session.json() == {"username": "user"}
    assert session.headers["cache-control"] == "no-store"


def test_logout_revokes_token_and_clears_cookie(client):
    login(client)
    old_token = client.cookies[auth.SESSION_COOKIE]
    response = client.delete("/api/session")
    assert response.status_code == 204
    assert not response.content
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert client.get("/api/session").status_code == 401
    client.cookies.set(auth.SESSION_COOKIE, old_token)
    assert client.get("/api/session").status_code == 401
    assert client.delete("/api/session").status_code == 204


def test_expired_token_is_rejected(client, monkeypatch):
    login(client)
    now = auth.time()
    monkeypatch.setattr(auth, "time", lambda: now + auth.SESSION_MAX_AGE + 1)
    assert client.get("/api/session").status_code == 401


def test_signing_in_again_rotates_the_token(client):
    login(client)
    old_token = client.cookies[auth.SESSION_COOKIE]
    login(client)
    assert client.cookies[auth.SESSION_COOKIE] != old_token
    # Remove the current host-scoped cookie before replaying the old token.
    client.cookies.clear()
    client.cookies.set(auth.SESSION_COOKIE, old_token)
    assert client.get("/api/session").status_code == 401


def test_browsers_have_independent_sessions(client):
    login(client)
    with TestClient(client.app) as other:
        assert other.get("/api/session").status_code == 401
        login(other)
        client.delete("/api/session")
        assert other.get("/api/session").status_code == 200


def test_missing_credentials_are_rejected(client):
    assert client.post("/api/session", json={"username": "user"}).status_code == 422
