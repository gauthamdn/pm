# Frontend instructions

Follow the root `AGENTS.md` and read `../docs/PLAN.md` before making changes. Keep this file aligned with the actual frontend as implementation proceeds.

## Current implementation

This is an in-memory Kanban demo using Next.js 16 App Router, React 19, strict TypeScript, Tailwind CSS 4, dnd-kit, and clsx. Docker builds it as static assets served by FastAPI. The `@/*` import alias maps to `src/*`.

- `src/app/page.tsx` renders `Workspace` at `/`.
- `src/components/Workspace.tsx` resolves the backend session before showing the board, renders the sign-in form, and handles sign-out. Session checks run every minute and on focus/visibility changes; authentication requests suspend old checks so stale responses cannot restore a signed-out board. Background network failures retain the existing board and show an error.
- `src/lib/auth.ts` defines same-origin session lookup, sign-in, and sign-out requests. Authentication decisions and session cookies belong to the backend.
- `src/app/layout.tsx` sets metadata and loads Manrope and Space Grotesk through `next/font/google`.
- `src/app/globals.css` defines Tailwind imports, shared color/surface tokens, and typography.
- `src/components/KanbanBoard.tsx` owns board and drag state. It handles column renaming, card creation/removal, movement, and drag cancellation. Keep its explicit dnd-kit context ID stable to avoid server/client hydration mismatches.
- `src/components/KanbanColumn.tsx` provides editable column titles, droppable areas, sortable card lists, empty states, and the new-card form.
- `src/components/KanbanCard.tsx` renders sortable cards and their remove action; `KanbanCardPreview.tsx` renders the drag overlay.
- `src/components/NewCardForm.tsx` manages title/details inputs and add/cancel behavior. It trims input and rejects blank titles.
- `src/lib/kanban.ts` defines `Card`, `Column`, and `BoardData`, the demo seed, `moveCard`, and `createId`.

The demo starts with five columns and eight cards. Cards are stored by ID, and each column's `cardIds` array determines membership and order. Preserve these relationships when changing board logic, and update state immutably.

Board state lives only in React and resets on reload or sign-out. Column titles change on each keystroke. Dragging uses a pointer sensor with a six-pixel activation threshold; keyboard movement is not implemented. Card editing, persistence, board API calls, and AI chat are not implemented. Production builds export to `out/` with trailing slashes. Development mode proxies `/api/` to FastAPI at `127.0.0.1:8000`; start the backend before interactive dev or browser tests.

## UI conventions

Reuse the existing components, Tailwind utilities, and CSS tokens. Preserve rounded surfaces, spacing, display/body typography, and the project palette:

- Accent yellow: `#ecad0a`
- Primary blue: `#209dd7`
- Secondary purple: `#753991`
- Dark navy: `#032147`
- Supporting gray: `#888888`

Use accessible names for controls and visible keyboard focus. Check desktop and narrow layouts when changing UI, including long titles, empty columns, and drag overlays. Keep card actions usable without accidentally starting a drag.

## Commands

Run from `frontend/`:

```bash
npm ci
npm run dev
npm run lint
npm run build
npm run start
npm run test:unit
npm run test:unit:watch
npm run test:e2e
npm run test:all
```

`start` requires a successful build and serves only `out/` using `serve`; it has no session API. Use Docker for a working production preview or `dev` with the running backend. Font loading during builds requires access to Google Fonts; exported font files are served locally at runtime. `test:all` runs unit tests followed by browser tests; it does not run lint or a production build.

## Tests and verification

- Vitest uses jsdom and React Testing Library. Tests live under `src/` as `*.test.*` or `*.spec.*`; `src/test/setup.ts` loads jest-dom matchers.
- `src/lib/kanban.test.ts` covers reordering, cross-column and empty-column movement, append behavior, invalid IDs, and immutable updates.
- `src/components/KanbanBoard.test.tsx` covers initial columns, renaming, adding/removing cards, blank titles, draft cancellation, and default details.
- `Workspace.test.tsx` covers session loading/retry, required fields, pending submission, invalid credentials, network failures, sign-out, expiry, stale responses, and retaining drafts during background failures.
- Playwright tests live in `tests/board.spec.ts` and `tests/auth.spec.ts`. Board tests authenticate through the actual API; authentication tests exercise the UI, reloads, HttpOnly cookies, revocation, expiry checks, and failure recovery. Tests clean up their own sessions.
- `playwright.config.ts` runs desktop (1440 x 1000) and narrow (390 x 844) Chromium projects. Pointer drag tests run on desktop; their four narrow variants are explicitly skipped.
- By default, Playwright starts the Next.js development server at `http://127.0.0.1:3000`. Set `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000` to test the running Docker app without starting a dev server. The health API test requires this external URL and is skipped in dev mode.
- Traces and failure screenshots are retained under ignored `test-results*/` directories. The load test also saves a full-page screenshot for visual inspection.
- Playwright requires its Chromium browser to be installed; use `npx playwright install chromium` when needed.

For bug fixes, first reproduce the issue through the browser as an end user would and establish the root cause. Add meaningful regression coverage for changed behavior. Run checks appropriate to the change, and fix failures, flakiness, and clear UI defects encountered during verification. Documentation-only changes do not require application tests.

## Planned integration boundaries

Docker uses a Node build stage and copies only `out/` into the Python runtime image. FastAPI serves these files alongside session, persistent board, and chat history APIs. The UI still uses demo board state until Part 7 connects the approved snapshot contract in `../docs/DATABASE.md`. See `../docs/FRONTEND.md` and `../docs/AUTH.md`. Keep OpenRouter credentials and calls in the backend, and avoid production features requiring a Next.js runtime server.

The agreed product behavior is immediate AI card updates, chat history retained across reloads/sign-ins, existing demo data seeded into new databases, and data retained across container stops. Implement these through the stages and approval checkpoints in `../docs/PLAN.md`; they are not current demo capabilities.
