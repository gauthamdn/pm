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

Open http://localhost:8000 and sign in with `user` / `password`. Persistent backend APIs are implemented; the board UI still uses demo state and resets on reload until Part 7 connects it.

Normal stops preserve the data volume. See [Docker setup](docs/SCAFFOLDING.md) and [frontend testing](docs/FRONTEND.md).
