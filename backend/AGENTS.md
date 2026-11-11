# Backend instructions

Follow the root `AGENTS.md` and `../docs/PLAN.md`.

## Current implementation

- Python 3.14, FastAPI, and Uvicorn; dependencies are declared in `pyproject.toml` and resolved in the generated `uv.lock`. Regenerate the lock with uv rather than editing it.
- `app/main.py` defines `create_app`, initializes SQLite during lifespan startup, and serves `GET /api/health`. Register API routes before the root static mount. API responses are not cached; lock timeouts return a recoverable 503.
- `app/auth.py` provides GET/POST/DELETE `/api/session`, dummy credential validation, and `require_user`. Apply `Depends(require_user)` to private APIs introduced later; the health endpoint and static assets stay public.
- Each app instance owns an in-memory token/expiry store. Tokens expire after eight hours, rotate on sign-in, and are revoked on sign-out. Cookies are HttpOnly, SameSite=Lax, and scoped to `/`. Restarting the backend requires signing in again; persisted board/history data is independent of sessions.
- `app/schema.py` contains the explicit version-1 SQL schema approved in `docs/database-schema.json`. `app/seed.json` contains the exact approved demo board. Do not load schema definitions dynamically from planning documents.
- `app/database.py` owns connection setup, explicit transactions, initialization/provisioning, board reads, and atomic snapshot saves. Every connection enables foreign keys; writes use `BEGIN IMMEDIATE`, with rollback and connection cleanup on failure. Unknown or unversioned existing schemas require an explicit migration and are never reset.
- `app/models.py` validates strict board payloads: five fixed columns in order, nonempty titles/IDs, exactly one membership per card, matching card-map keys, and nonnegative integer revisions. Unknown fields are rejected.
- `app/board.py` implements authenticated GET/PUT `/api/board` and GET `/api/chat`. Ownership comes from the session username, never request-supplied owner IDs. Writes compare `expected_revision` and return 409 for stale data. Chat reads return board and messages from one database snapshot. AI/chat writes remain Part 9 work.
- Docker copies the Next.js export into `/app/static` and sets `STATIC_DIR` to that path. Local development defaults to `frontend/out/` relative to the repository. Missing exports do not block API startup; build the frontend before loading the local backend homepage.
- `tests/test_app.py` uses isolated static fixtures to verify the API, nested static assets, and 404 handling. Tests use FastAPI TestClient with httpx2. Frontend Playwright tests separately exercise the actual Docker export.
- `tests/test_auth.py` verifies credential rejection, token validity/expiry/rotation/revocation, independent browser sessions, and cookie/cache attributes.
- `tests/test_board.py` covers authenticated mutations, validation, ownership, concurrent saves/reads, partial-write rollback, lock recovery, and persistence across sessions/app instances. `tests/test_database.py` covers initialization, constraints, schema-version guards, and startup rollback.
- The Docker image installs production dependencies using `uv sync --locked --no-dev` and runs as the non-root `app` user.
- Docker stores `DATABASE_PATH=/app/data/kanban.sqlite3` in the named volume. Local development defaults to the ignored repository `data/kanban.sqlite3`. Startup creates version 1 and seeds only new boards; an empty existing board stays empty. The frontend still uses local demo state until Part 7.

## Development

From `backend/`, with uv and Python 3.14 available:

```sh
uv sync --locked
uv run uvicorn app.main:app --reload
uv run ruff check .
uv run ruff format --check .
uv run pytest -W error
```

Keep credentials out of static files and browser responses. Tests must pass an isolated temporary `database_path` to `create_app`; never run mutation tests against the user's database. `ensure_user_board` must be called within a write transaction. See `../docs/DATABASE.md` for the approved contracts.
