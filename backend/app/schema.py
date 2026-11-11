"""Version 1 schema. Future changes require an explicit versioned migration."""

VERSION = 1

STATEMENTS = (
    """
    CREATE TABLE users (
        id TEXT NOT NULL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE CHECK (length(trim(username)) > 0),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE boards (
        id TEXT NOT NULL PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    )
    """,
    """
    CREATE TABLE board_columns (
        board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
        id TEXT NOT NULL CHECK (id IN (
            'col-backlog', 'col-discovery', 'col-progress', 'col-review', 'col-done'
        )),
        title TEXT NOT NULL CHECK (length(trim(title)) > 0),
        position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 4),
        PRIMARY KEY (board_id, id),
        UNIQUE (board_id, position)
    )
    """,
    """
    CREATE TABLE cards (
        board_id TEXT NOT NULL,
        id TEXT NOT NULL,
        column_id TEXT NOT NULL,
        title TEXT NOT NULL CHECK (length(trim(title)) > 0),
        details TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL CHECK (position >= 0),
        PRIMARY KEY (board_id, id),
        UNIQUE (board_id, column_id, position),
        FOREIGN KEY (board_id, column_id)
            REFERENCES board_columns(board_id, id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE chat_messages (
        board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
        id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        sequence INTEGER NOT NULL CHECK (sequence >= 0),
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL CHECK (length(trim(content)) > 0),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        PRIMARY KEY (board_id, id),
        UNIQUE (board_id, sequence),
        UNIQUE (board_id, turn_id, role)
    )
    """,
)
