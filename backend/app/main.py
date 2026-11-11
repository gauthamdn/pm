import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import NO_STORE
from app.auth import router as session_router
from app.board import router as board_router
from app.database import initialize


def create_app(
    static_dir: Path | None = None, *, database_path: Path | None = None
) -> FastAPI:
    path = database_path or Path(
        os.environ.get(
            "DATABASE_PATH", Path(__file__).resolve().parents[2] / "data/kanban.sqlite3"
        )
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize(path)
        yield

    app = FastAPI(title="Kanban Studio API", lifespan=lifespan)
    app.state.database_path = path
    app.state.sessions = {}
    app.include_router(session_router)
    app.include_router(board_router)

    @app.middleware("http")
    async def no_api_cache(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers.update(NO_STORE)
        return response

    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request, exc):
        if exc.sqlite_errorcode & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            return JSONResponse(
                {"detail": "Database is busy. Please try again."},
                status_code=503,
                headers=NO_STORE,
            )
        raise exc

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "message": "Hello from FastAPI."}

    # Local API development can start before the frontend has been built.
    directory = static_dir or Path(
        os.environ.get(
            "STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend/out"
        )
    )
    # API routes must be registered before the root static mount.
    app.mount("/", StaticFiles(directory=directory, html=True, check_dir=False))
    return app


app = create_app()
