from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Kanban Studio API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "message": "Hello from FastAPI."}


# API routes must be registered before the root static mount.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
