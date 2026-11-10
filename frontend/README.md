# Kanban Studio

## Run

```bash
npm ci
npm run dev
```

## Tests

```bash
npm run test:unit
npm run test:e2e
```

`npm run build` exports to `out/`; `npm start` previews that export on port 3000.

To test the Docker-served app after starting it from the repository root:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e
```

See [frontend verification](../docs/FRONTEND.md) for browser setup and coverage.
