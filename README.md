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

Open http://localhost:8000 after starting. FastAPI serves the statically built Kanban demo. Board changes currently reset on reload; sign-in and persistence come in later stages.

Normal stops preserve the data volume. See [Docker setup](docs/SCAFFOLDING.md) and [frontend testing](docs/FRONTEND.md).
