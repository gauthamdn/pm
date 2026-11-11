# Static frontend and verification

## Production

From the repository root, run `./scripts/start.sh` (or `./scripts/start.ps1` on Windows), then open http://localhost:8000.

The Docker build runs `npm ci` and `next build` in a Node stage, then copies `frontend/out/` to `/app/static` in the Python runtime. FastAPI serves the export at `/`, including JavaScript, CSS, fonts, and the exported 404 page. `/api/health` remains an API route. This follows the [Next.js static export documentation](https://nextjs.org/docs/app/guides/static-exports).

Sign in with `user` / `password`. The board still uses React state seeded from the demo data; reloading or signing out resets edits. Card editing and frontend persistence integration remain Part 7 work. The [persistent backend APIs](DATABASE.md) are implemented. See [session behavior](AUTH.md).

## Local checks

With Node 26 installed, run from `frontend/`:

```sh
npm ci
npm run lint
npm run test:unit
npm run build
npx playwright install chromium
```

Start the Docker backend before `npm run dev`; the dev server proxies `/api/` to `127.0.0.1:8000`. Use Docker for a working production preview. `npm start` serves files only and does not provide session APIs.

With the backend running on port 8000, default browser tests start a Next.js dev server automatically:

```sh
npm run test:e2e
```

To test the running Docker app instead:

```sh
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e
```

The external URL disables Playwright's dev server. Browser tests use fresh contexts, and this stage has no persistent board mutations. Backend test commands are documented in [Docker setup](SCAFFOLDING.md).

## Browser tests in Docker

After starting the app, this direct command uses matching browser binaries from the [official Playwright image](https://playwright.dev/docs/docker). Run it from the repository root after installing frontend dependencies with `npm ci` in `frontend/`:

```sh
docker run --rm --init --shm-size=1g \
  --network container:kanban-studio-app-1 \
  --mount "type=bind,source=$PWD/frontend,target=/frontend" \
  --workdir /frontend \
  -e PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 \
  mcr.microsoft.com/playwright:v1.65.0-noble \
  npm run test:e2e -- --reporter=list --workers=2
```

Use the container's loopback address for this test. The browser trace showed that the hostname `app` was automatically upgraded to HTTPS, which does not match the local HTTP server. The `.app` domain is on the [HTTPS preload list](https://developers.googleblog.com/en/build-security-into-your-next-website/).

## Coverage

- Frontend unit/component tests: movement, ordering, empty columns, invalid IDs, immutable updates, renaming, adding/removing cards, title validation, draft cancellation, and default details.
- Authentication component tests: initial loading/retry, form validation and pending state, invalid credentials, service failures, sign-out clearing, expiry, stale responses, and retaining local edits after failed background checks.
- Backend tests: health response, nested static assets, missing assets/API paths, and exported 404 responses using isolated fixture files.
- Production browser tests: initial load and reload, five columns/eight cards, fonts, console/network failures, renaming, adding/removing/cancelling cards, long text, focus visibility, cross-column movement, reordering, empty-column drops, and Escape cancellation.
- Authentication browser tests: anonymous visits, wrong/correct credentials, reload, HttpOnly cookies, logout/revocation, returning after logout, periodic/focus revalidation, and recoverable API failures, at both screen widths.
- Desktop viewport: 1440 x 1000. Narrow viewport: 390 x 844. Four pointer drag tests run on desktop and are explicitly skipped in the narrow project; other browser scenarios run at both widths.
- Load tests save full-page screenshots under `frontend/test-results/`; failures retain screenshots and traces. Inspect these visually as well as checking assertions.

## Fixes found during integration

- Escape cancelled dnd-kit's drag but left the custom preview visible. Clearing board drag state on cancellation removes it.
- Reloading the dev server produced different generated drag accessibility IDs on the server and client. An explicit stable context ID fixes the hydration mismatch.
- Desktop card text was squeezed beside the Remove button. Moving the button below the text, adding word wrapping and focus outlines, and adjusting responsive column sizes improves readability.
- Production type checking exposed missing Vitest imports in existing tests; explicit imports keep tests and the production build type-safe.

## Part 3 verification results (historical)

- Frontend lint passed; 12 unit/component tests passed; production type checking and static export passed, both locally in the Node container and during the multi-stage Docker build.
- Backend lint and formatting passed; seven backend tests passed with warnings treated as errors.
- Final production browser run: 16 passed in 5.0 seconds, four intentionally skipped narrow pointer-drag variants. All desktop drag scenarios passed.
- Local dev-server browser run: nine desktop tests passed; the FastAPI-only test was skipped as intended.
- Desktop and narrow production screenshots were visually inspected. Load/reload tests reported no browser errors or failed resources, including font files.
- Confirmed the runtime uses a non-root user and contains no Node binary. The updated `npm start` command returned the exported board with HTTP 200.

Current authentication verification is recorded in [AUTH.md](AUTH.md).
