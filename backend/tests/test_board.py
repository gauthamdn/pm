from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app import board as board_routes
from app.auth import require_user
from app.database import SEED, ensure_user_board, transaction
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(database_path=tmp_path / "nested" / "kanban.sqlite3")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        login(client)
        yield client


def login(client):
    response = client.post(
        "/api/session", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 200


def candidate(board):
    return {
        "expected_revision": board["revision"],
        "columns": deepcopy(board["columns"]),
        "cards": deepcopy(board["cards"]),
    }


@pytest.mark.parametrize(
    "method,path", [("GET", "/api/board"), ("PUT", "/api/board"), ("GET", "/api/chat")]
)
def test_private_endpoints_require_authentication(app, method, path):
    with TestClient(app) as anonymous:
        payload = {**SEED.model_dump(), "expected_revision": 0}
        response = anonymous.request(
            method, path, json=payload if method == "PUT" else None
        )
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"


def test_initial_snapshot_and_empty_chat(client):
    response = client.get("/api/board")
    assert response.status_code == 200
    board = response.json()
    assert {key: board[key] for key in ("columns", "cards")} == SEED.model_dump()
    assert board["revision"] == 0
    assert board["id"]
    assert response.headers["cache-control"] == "no-store"
    history = client.get("/api/chat")
    assert history.json() == {"board": board, "messages": []}
    assert history.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "action", ["create", "edit", "remove", "reorder", "move", "empty-column", "rename"]
)
def test_board_operations_persist(client, action):
    original = client.get("/api/board").json()
    update = candidate(original)
    if action == "create":
        update["cards"]["new-card"] = {
            "id": "new-card",
            "title": "New task",
            "details": "",
        }
        update["columns"][0]["cardIds"].append("new-card")
    elif action == "edit":
        update["cards"]["card-1"].update(title="Edited title", details="Edited details")
    elif action == "remove":
        update["columns"][0]["cardIds"].remove("card-1")
        del update["cards"]["card-1"]
    elif action == "reorder":
        update["columns"][0]["cardIds"].reverse()
    elif action == "move":
        update["columns"][0]["cardIds"].remove("card-1")
        update["columns"][3]["cardIds"].insert(0, "card-1")
    elif action == "empty-column":
        update["columns"][3]["cardIds"] = ["card-1"]
        del update["cards"]["card-6"]
        update["columns"][0]["cardIds"].remove("card-1")
    else:
        update["columns"][0]["title"] = "Ready"
    response = client.put("/api/board", json=update)
    assert response.status_code == 200
    saved = response.json()
    assert saved["id"] == original["id"]
    assert saved["revision"] == original["revision"] + 1
    assert saved["columns"] == update["columns"]
    assert saved["cards"] == update["cards"]
    assert client.get("/api/board").json() == saved
    assert response.headers["cache-control"] == "no-store"
    with transaction(client.app.state.database_path) as db:
        for column in update["columns"]:
            rows = db.execute(
                "SELECT id, position FROM cards "
                "WHERE board_id = ? AND column_id = ? ORDER BY position",
                (saved["id"], column["id"]),
            ).fetchall()
            assert [(row["id"], row["position"]) for row in rows] == [
                (card_id, position)
                for position, card_id in enumerate(column["cardIds"])
            ]


def test_titles_are_trimmed_details_are_preserved_and_sql_is_parameterized(client):
    update = candidate(client.get("/api/board").json())
    update["columns"][0]["title"] = "  Ready  "
    update["cards"]["card-1"]["title"] = "  Task'); DROP TABLE users; --  "
    update["cards"]["card-1"]["details"] = "  keep indentation\nsecond line  "
    del update["cards"]["card-2"]["details"]
    response = client.put("/api/board", json=update)
    assert response.status_code == 200
    board = response.json()
    assert board["columns"][0]["title"] == "Ready"
    assert board["cards"]["card-1"]["title"] == "Task'); DROP TABLE users; --"
    assert board["cards"]["card-1"]["details"] == "  keep indentation\nsecond line  "
    assert board["cards"]["card-2"]["details"] == ""
    assert client.get("/api/board").status_code == 200


@pytest.mark.parametrize(
    "invalid",
    [
        "column-id",
        "column-order",
        "column-count",
        "duplicate-column",
        "blank-column",
        "blank-title",
        "duplicate-membership",
        "duplicate-within-column",
        "unknown-card",
        "unassigned-card",
        "key-mismatch",
        "empty-id",
        "extra-owner",
        "extra-board",
        "extra-card-field",
        "wrong-details-type",
        "negative-revision",
        "string-revision",
        "float-revision",
        "boolean-revision",
    ],
)
def test_invalid_snapshots_leave_database_unchanged(client, invalid):
    before = client.get("/api/board").json()
    update = candidate(before)
    if invalid == "column-id":
        update["columns"][0]["id"] = "other"
    elif invalid == "column-order":
        update["columns"].reverse()
    elif invalid == "column-count":
        update["columns"].pop()
    elif invalid == "duplicate-column":
        update["columns"][1]["id"] = update["columns"][0]["id"]
    elif invalid == "blank-column":
        update["columns"][0]["title"] = " \t\n"
    elif invalid == "blank-title":
        update["cards"]["card-1"]["title"] = " \t\n"
    elif invalid == "duplicate-membership":
        update["columns"][1]["cardIds"].append("card-1")
    elif invalid == "duplicate-within-column":
        update["columns"][0]["cardIds"].append("card-1")
    elif invalid == "unknown-card":
        update["columns"][0]["cardIds"].append("missing")
    elif invalid == "unassigned-card":
        update["columns"][0]["cardIds"].remove("card-1")
    elif invalid == "key-mismatch":
        update["cards"]["card-1"]["id"] = "other"
    elif invalid == "empty-id":
        update["cards"][""] = {"id": "", "title": "Task", "details": ""}
        update["columns"][0]["cardIds"].append("")
    elif invalid == "extra-owner":
        update["user_id"] = "other"
    elif invalid == "extra-board":
        update["id"] = "other-board"
    elif invalid == "extra-card-field":
        update["cards"]["card-1"]["owner"] = "other"
    elif invalid == "wrong-details-type":
        update["cards"]["card-1"]["details"] = 123
    else:
        update["expected_revision"] = {
            "negative-revision": -1,
            "string-revision": "0",
            "float-revision": 0.0,
            "boolean-revision": False,
        }[invalid]
    response = client.put("/api/board", json=update)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/board").json() == before


def test_stale_revision_is_rejected_without_overwriting(client):
    before = client.get("/api/board").json()
    first = candidate(before)
    first["cards"]["card-1"]["title"] = "First edit"
    saved = client.put("/api/board", json=first).json()
    stale = candidate(before)
    stale["cards"]["card-1"]["title"] = "Stale edit"
    response = client.put("/api/board", json=stale)
    assert response.status_code == 409
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/board").json() == saved


def test_concurrent_saves_have_one_winner(client):
    with TestClient(client.app) as other:
        login(other)
        before = client.get("/api/board").json()
        updates = [candidate(before), candidate(before)]
        updates[0]["columns"][0]["title"] = "First tab"
        updates[1]["columns"][0]["title"] = "Second tab"
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(browser.put, "/api/board", json=update)
                for browser, update in zip((client, other), updates)
            ]
            responses = [future.result() for future in futures]
        assert sorted(response.status_code for response in responses) == [200, 409]
        winner = next(
            response.json() for response in responses if response.status_code == 200
        )
        assert winner["revision"] == 1
        assert client.get("/api/board").json() == winner


def test_rollback_after_partial_write_preserves_everything(client):
    before = client.get("/api/board").json()
    with transaction(client.app.state.database_path, write=True) as db:
        db.execute("""
            CREATE TRIGGER force_failure BEFORE INSERT ON cards
            WHEN NEW.title = 'Trip rollback'
            BEGIN SELECT RAISE(ABORT, 'forced failure'); END
        """)
    update = candidate(before)
    update["columns"][0]["title"] = "Must roll back"
    update["cards"]["card-1"]["title"] = "Trip rollback"
    with TestClient(client.app, raise_server_exceptions=False) as failing_client:
        login(failing_client)
        response = failing_client.put("/api/board", json=update)
    assert response.status_code == 500
    assert "forced failure" not in response.text
    assert client.get("/api/board").json() == before


def test_locked_database_returns_recoverable_error(client):
    before = client.get("/api/board").json()
    with transaction(client.app.state.database_path, write=True):
        response = client.put("/api/board", json=candidate(before))
    assert response.status_code == 503
    assert response.json() == {"detail": "Database is busy. Please try again."}
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/board").json() == before
    assert client.put("/api/board", json=candidate(before)).status_code == 200


def test_users_cannot_read_or_modify_each_others_board_or_chat(client):
    own = client.get("/api/board").json()
    with transaction(client.app.state.database_path, write=True) as db:
        other_id = ensure_user_board(db, "other")
        db.execute(
            "UPDATE cards SET title = 'Other private task' "
            "WHERE board_id = ? AND id = 'card-1'",
            (other_id,),
        )
        db.execute(
            "INSERT INTO chat_messages (board_id,id,turn_id,sequence,role,content) "
            "VALUES (?,?,?,?,?,?)",
            (other_id, "other-message", "other-turn", 0, "user", "Other private text"),
        )
    assert client.get(f"/api/board?board_id={other_id}&username=other").json() == own
    assert "Other private" not in client.get("/api/chat").text
    update = candidate(own)
    update["cards"]["card-1"]["title"] = "Own edit"
    assert client.put("/api/board", json=update).status_code == 200
    # Future users are provisioned internally; no registration endpoint is introduced.
    client.app.dependency_overrides[require_user] = lambda: {"username": "other"}
    try:
        other_board = client.get("/api/board").json()
        assert other_board["id"] == other_id
        assert other_board["cards"]["card-1"]["title"] == "Other private task"
        assert (
            client.get("/api/chat").json()["messages"][0]["content"]
            == "Other private text"
        )
    finally:
        client.app.dependency_overrides.clear()


def test_deleted_cards_and_chat_survive_app_restart_and_sign_out(client):
    path = client.app.state.database_path
    update = candidate(client.get("/api/board").json())
    update["cards"] = {}
    for column in update["columns"]:
        column["cardIds"] = []
    saved = client.put("/api/board", json=update).json()
    with transaction(path, write=True) as db:
        for sequence, role in ((1, "assistant"), (0, "user")):
            db.execute(
                "INSERT INTO chat_messages (board_id,id,turn_id,sequence,role,content) "
                "VALUES (?,?,?,?,?,?)",
                (
                    saved["id"],
                    f"m{sequence}",
                    "turn-1",
                    sequence,
                    role,
                    f"Message {sequence}",
                ),
            )
        db.execute(
            "UPDATE boards SET revision = revision + 1 WHERE id = ?", (saved["id"],)
        )
    before = client.get("/api/chat").json()
    assert [message["sequence"] for message in before["messages"]] == [0, 1]
    assert before["board"]["revision"] == 2
    client.delete("/api/session")
    login(client)
    assert client.get("/api/chat").json() == before
    with TestClient(create_app(database_path=path)) as restarted:
        assert restarted.get("/api/board").status_code == 401
        login(restarted)
        assert restarted.get("/api/chat").json() == before
        assert restarted.get("/api/board").json()["cards"] == {}


def test_chat_read_keeps_one_snapshot_during_a_concurrent_commit(client, monkeypatch):
    original_read = board_routes.read_board
    committed = False

    def commit_between_board_and_messages(db, username):
        nonlocal committed
        snapshot = original_read(db, username)
        if not committed:
            committed = True
            with transaction(client.app.state.database_path, write=True) as writer:
                for sequence, role in enumerate(("user", "assistant")):
                    writer.execute(
                        "INSERT INTO chat_messages "
                        "(board_id,id,turn_id,sequence,role,content) "
                        "VALUES (?,?,?,?,?,?)",
                        (
                            snapshot.id,
                            f"m{sequence}",
                            "turn-1",
                            sequence,
                            role,
                            "Message",
                        ),
                    )
                writer.execute(
                    "UPDATE boards SET revision = revision + 1 WHERE id = ?",
                    (snapshot.id,),
                )
        return snapshot

    monkeypatch.setattr(board_routes, "read_board", commit_between_board_and_messages)
    old = client.get("/api/chat").json()
    assert old["board"]["revision"] == 0
    assert old["messages"] == []
    current = client.get("/api/chat").json()
    assert current["board"]["revision"] == 1
    assert [message["role"] for message in current["messages"]] == ["user", "assistant"]
