# Server scripts

Follow the root `AGENTS.md` and `../docs/PLAN.md`.

- `start.sh` / `stop.sh` support macOS and Linux through POSIX sh.
- `start.ps1` / `stop.ps1` support Windows PowerShell.
- Scripts resolve the repository from their own location, so they can run from another working directory.
- Docker must be running with Linux containers and Docker Compose v2 or newer.
- Start builds the image, starts Compose in detached mode, and waits for container health before printing the URL.
- Stop runs `docker compose down`, retaining the named data volume. Do not add volume removal to normal stop scripts.
- Propagate command failures instead of printing a success message when Docker fails.

See `../docs/SCAFFOLDING.md` for usage and verification.
