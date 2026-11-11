import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from app import database
from app.database import connect, ensure_user_board, initialize, read_board, transaction


def test_initialization_creates_versioned_database_and_seed_once(tmp_path):
    path = tmp_path / "new" / "kanban.sqlite3"
    initialize(path)
    with transaction(path) as db:
        board = read_board(db, "user").model_dump()
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM boards").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM cards").fetchone()[0] == 8
        assert db.execute("SELECT count(*) FROM chat_messages").fetchone()[0] == 0
    initialize(path)
    with transaction(path) as db:
        assert read_board(db, "user").model_dump() == board
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_concurrent_initialization_provisions_one_board(tmp_path):
    path = tmp_path / "kanban.sqlite3"
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(initialize, [path, path]))
    with transaction(path) as db:
        assert db.execute("SELECT count(*) FROM boards").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM cards").fetchone()[0] == 8


def test_provisioning_future_user_is_idempotent(tmp_path):
    path = tmp_path / "kanban.sqlite3"
    initialize(path)
    with transaction(path, write=True) as db:
        first = ensure_user_board(db, "future-user")
        second = ensure_user_board(db, "future-user")
        assert first == second
        assert first != read_board(db, "user").id
        assert len(read_board(db, "future-user").cards) == 8
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 2


def test_unknown_schema_version_is_not_reset(tmp_path):
    path = tmp_path / "kanban.sqlite3"
    initialize(path)
    with transaction(path, write=True) as db:
        before = read_board(db, "user").model_dump()
        db.execute("PRAGMA user_version = 99")
    with pytest.raises(RuntimeError, match="Unsupported database schema version"):
        initialize(path)
    with transaction(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99
        assert read_board(db, "user").model_dump() == before


def test_unversioned_existing_tables_are_not_overwritten(tmp_path):
    path = tmp_path / "kanban.sqlite3"
    with closing(connect(path)) as db:
        db.execute("CREATE TABLE existing (value TEXT)")
        db.execute("INSERT INTO existing VALUES ('keep me')")
    with pytest.raises(RuntimeError, match="explicit migration"):
        initialize(path)
    with transaction(path) as db:
        assert db.execute("SELECT value FROM existing").fetchone()[0] == "keep me"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0


def test_failed_seed_rolls_back_schema_version_and_partial_data(tmp_path, monkeypatch):
    path = tmp_path / "kanban.sqlite3"
    original = database.replace_cards

    def interrupted_seed(db, board_id, board):
        original(db, board_id, board)
        raise RuntimeError("interrupted startup")

    monkeypatch.setattr(database, "replace_cards", interrupted_seed)
    with pytest.raises(RuntimeError, match="interrupted startup"):
        initialize(path)
    with transaction(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            == []
        )
    monkeypatch.setattr(database, "replace_cards", original)
    initialize(path)
    with transaction(path) as db:
        assert len(read_board(db, "user").cards) == 8


@pytest.mark.parametrize(
    "violation",
    ["foreign-column", "duplicate-position", "invalid-role", "duplicate-turn"],
)
def test_database_constraints_enforce_the_approved_schema(tmp_path, violation):
    path = tmp_path / "kanban.sqlite3"
    initialize(path)
    with transaction(path) as db:
        board_id = read_board(db, "user").id
    if violation == "duplicate-turn":
        with transaction(path, write=True) as db:
            db.execute(
                "INSERT INTO chat_messages (board_id,id,turn_id,sequence,role,content) "
                "VALUES (?,?,?,?,?,?)",
                (board_id, "m0", "turn-1", 0, "user", "Message"),
            )
    with pytest.raises(sqlite3.IntegrityError):
        with transaction(path, write=True) as db:
            if violation in ("foreign-column", "duplicate-position"):
                column_id = (
                    "missing" if violation == "foreign-column" else "col-backlog"
                )
                db.execute(
                    "INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?)",
                    (board_id, "new", column_id, "Task", "", 0),
                )
            else:
                role = "system" if violation == "invalid-role" else "user"
                db.execute(
                    "INSERT INTO chat_messages "
                    "(board_id,id,turn_id,sequence,role,content) VALUES (?,?,?,?,?,?)",
                    (board_id, "m1", "turn-1", 1, role, "Message"),
                )
