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

Open http://localhost:8000 after starting. Part 2 currently serves a smoke page that calls the FastAPI health endpoint. The frontend demo is still separate.

Normal stops preserve the data volume. See [scaffolding notes](docs/SCAFFOLDING.md) for development and verification.
