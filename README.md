# Kanban Studio

Requires Docker with Docker Compose v2 or newer running Linux containers.

macOS / Linux:

```sh
./scripts/start.sh
./scripts/stop.sh
```

Windows PowerShell:

```powershell
./scripts/start.ps1
./scripts/stop.ps1
```

Open http://localhost:8000 and sign in with `user` / `password`. FastAPI serves the static frontend and session API. Board changes currently reset on reload; persistence comes in later stages.

Normal stops preserve the data volume. See [Docker setup](docs/SCAFFOLDING.md) and [frontend testing](docs/FRONTEND.md).
