import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.auth import NO_STORE
from app.models import BoardData, BoardSnapshot, BoardUpdate, Column
from app.schema import STATEMENTS, VERSION

SEED = BoardData.model_validate_json(Path(__file__).with_name("seed.json").read_text())


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, autocommit=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def transaction(path: Path, *, write: bool = False):
    with closing(connect(path)) as db:
        try:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute("PRAGMA journal_mode = WAL")
    with transaction(path, write=True) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            tables = db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if tables:
                raise RuntimeError(
                    "Unversioned database requires an explicit migration."
                )
            for statement in STATEMENTS:
                db.execute(statement)
            db.execute(f"PRAGMA user_version = {VERSION}")
        elif version != VERSION:
            raise RuntimeError(f"Unsupported database schema version: {version}")
        ensure_user_board(db, "user")


def ensure_user_board(db: sqlite3.Connection, username: str) -> str:
    """Provision once inside the caller's write transaction."""
    user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if user is None:
        user_id = str(uuid4())
        db.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username)
        )
    else:
        user_id = user["id"]
    board = db.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone()
    if board is not None:
        return board["id"]

    board_id = str(uuid4())
    db.execute("INSERT INTO boards (id, user_id) VALUES (?, ?)", (board_id, user_id))
    db.executemany(
        "INSERT INTO board_columns (board_id, id, title, position) VALUES (?, ?, ?, ?)",
        [
            (board_id, column.id, column.title, position)
            for position, column in enumerate(SEED.columns)
        ],
    )
    replace_cards(db, board_id, SEED)
    return board_id


def owned_board(db: sqlite3.Connection, username: str) -> sqlite3.Row:
    board = db.execute(
        "SELECT boards.id, boards.revision FROM boards "
        "JOIN users ON users.id = boards.user_id WHERE users.username = ?",
        (username,),
    ).fetchone()
    if board is None:
        raise HTTPException(404, "Board not found.", headers=NO_STORE)
    return board


def read_board(db: sqlite3.Connection, username: str) -> BoardSnapshot:
    board = owned_board(db, username)
    columns = {
        row["id"]: Column(id=row["id"], title=row["title"], cardIds=[])
        for row in db.execute(
            "SELECT id, title FROM board_columns WHERE board_id = ? ORDER BY position",
            (board["id"],),
        )
    }
    cards = {}
    for row in db.execute(
        "SELECT id, title, details, column_id FROM cards "
        "WHERE board_id = ? ORDER BY column_id, position",
        (board["id"],),
    ):
        columns[row["column_id"]].cardIds.append(row["id"])
        cards[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "details": row["details"],
        }
    return BoardSnapshot(
        id=board["id"],
        revision=board["revision"],
        columns=list(columns.values()),
        cards=cards,
    )


def replace_cards(db: sqlite3.Connection, board_id: str, board: BoardData) -> None:
    db.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
    db.executemany(
        "INSERT INTO cards (board_id, id, column_id, title, details, position) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                board_id,
                card_id,
                column.id,
                board.cards[card_id].title,
                board.cards[card_id].details,
                position,
            )
            for column in board.columns
            for position, card_id in enumerate(column.cardIds)
        ],
    )


def save_board(
    db: sqlite3.Connection, username: str, candidate: BoardUpdate
) -> BoardSnapshot:
    board = owned_board(db, username)
    changed = db.execute(
        "UPDATE boards SET revision = revision + 1, "
        "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
        "WHERE id = ? AND revision = ?",
        (board["id"], candidate.expected_revision),
    )
    if changed.rowcount != 1:
        raise HTTPException(
            409, "Board changed. Reload and try again.", headers=NO_STORE
        )
    db.executemany(
        "UPDATE board_columns SET title = ? WHERE board_id = ? AND id = ?",
        [(column.title, board["id"], column.id) for column in candidate.columns],
    )
    replace_cards(db, board["id"], candidate)
    return read_board(db, username)
