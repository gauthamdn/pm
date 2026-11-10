# Backend instructions

Follow the root `AGENTS.md` and `../docs/PLAN.md`.

## Current implementation

- Python 3.14, FastAPI, and Uvicorn; dependencies are declared in `pyproject.toml` and resolved in the generated `uv.lock`. Regenerate the lock with uv rather than editing it.
- `app/main.py` defines the application and `GET /api/health`. Register API routes before the root static mount.
- `app/static/` contains the Part 2 smoke page, styles, and browser API call. The Next.js frontend is not integrated yet.
- `tests/test_app.py` verifies the health response, static resources, and unknown API routes. Tests use FastAPI TestClient with httpx2.
- The Docker image installs production dependencies using `uv sync --locked --no-dev` and runs as the non-root `app` user.
- Compose mounts persistent storage at `/app/data` and reserves `DATABASE_PATH=/app/data/kanban.sqlite3` for later database implementation. No application schema or database initialization exists yet; follow the Part 5 approval checkpoint.

## Development

From `backend/`, with uv and Python 3.14 available:

```sh
uv sync --locked
uv run uvicorn app.main:app --reload
uv run ruff check .
uv run ruff format --check .
uv run pytest -W error
```

Keep credentials out of static files and browser responses. Use isolated temporary storage for database tests when persistence is implemented.
