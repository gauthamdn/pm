# Kanban Studio

## Run

Start the Docker app from the repository root first. The dev server proxies `/api/` to FastAPI on port 8000. Sign in with `user` / `password`.

```bash
npm ci
npm run dev
```

## Tests

```bash
npm run test:unit
npm run test:e2e
```

`npm run build` exports to `out/`. Use Docker for a working production preview; `npm start` serves files only and does not supply the session API.

To test the Docker-served app after starting it from the repository root:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e
```

See [frontend verification](../docs/FRONTEND.md) for browser setup and coverage.
