import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Kanban Studio API")

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
