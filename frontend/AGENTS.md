# Frontend instructions

Follow the root `AGENTS.md` and read `../docs/PLAN.md` before making changes. Keep this file aligned with the actual frontend as implementation proceeds.

## Current implementation

This is an in-memory Kanban demo using Next.js 16 App Router, React 19, strict TypeScript, Tailwind CSS 4, dnd-kit, and clsx. Docker builds it as static assets served by FastAPI. The `@/*` import alias maps to `src/*`.

- `src/app/page.tsx` renders the board at `/`.
- `src/app/layout.tsx` sets metadata and loads Manrope and Space Grotesk through `next/font/google`.
- `src/app/globals.css` defines Tailwind imports, shared color/surface tokens, and typography.
- `src/components/KanbanBoard.tsx` owns board and drag state. It handles column renaming, card creation/removal, movement, and drag cancellation. Keep its explicit dnd-kit context ID stable to avoid server/client hydration mismatches.
- `src/components/KanbanColumn.tsx` provides editable column titles, droppable areas, sortable card lists, empty states, and the new-card form.
- `src/components/KanbanCard.tsx` renders sortable cards and their remove action; `KanbanCardPreview.tsx` renders the drag overlay.
- `src/components/NewCardForm.tsx` manages title/details inputs and add/cancel behavior. It trims input and rejects blank titles.
- `src/lib/kanban.ts` defines `Card`, `Column`, and `BoardData`, the demo seed, `moveCard`, and `createId`.

The demo starts with five columns and eight cards. Cards are stored by ID, and each column's `cardIds` array determines membership and order. Preserve these relationships when changing board logic, and update state immutably.

State lives only in React and resets on reload. Column titles change on each keystroke. Dragging uses a pointer sensor with a six-pixel activation threshold; keyboard movement is not implemented. Card editing, authentication, persistence, board API calls, and AI chat are also not implemented. `next.config.ts` exports to `out/` with trailing slashes for directory-based static serving.

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

`start` requires a successful build and previews `out/` using `serve`; it does not run a Next.js server. Font loading during builds requires access to Google Fonts; exported font files are served locally at runtime. `test:all` runs unit tests followed by browser tests; it does not run lint or a production build.

## Tests and verification

- Vitest uses jsdom and React Testing Library. Tests live under `src/` as `*.test.*` or `*.spec.*`; `src/test/setup.ts` loads jest-dom matchers.
- `src/lib/kanban.test.ts` covers reordering, cross-column and empty-column movement, append behavior, invalid IDs, and immutable updates.
- `src/components/KanbanBoard.test.tsx` covers initial columns, renaming, adding/removing cards, blank titles, draft cancellation, and default details.
- Playwright tests live in `tests/board.spec.ts`. They cover loading/reload, fonts, browser/network errors, column renaming, adding/removing/cancelling cards, long text, focus, and pointer drag/drop/cancellation.
- `playwright.config.ts` runs desktop (1440 x 1000) and narrow (390 x 844) Chromium projects. Pointer drag tests run on desktop; their four narrow variants are explicitly skipped.
- By default, Playwright starts the Next.js development server at `http://127.0.0.1:3000`. Set `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000` to test the running Docker app without starting a dev server. The health API test requires this external URL and is skipped in dev mode.
- Traces and failure screenshots are retained under ignored `test-results*/` directories. The load test also saves a full-page screenshot for visual inspection.
- Playwright requires its Chromium browser to be installed; use `npx playwright install chromium` when needed.

For bug fixes, first reproduce the issue through the browser as an end user would and establish the root cause. Add meaningful regression coverage for changed behavior. Run checks appropriate to the change, and fix failures, flakiness, and clear UI defects encountered during verification. Documentation-only changes do not require application tests.

## Planned integration boundaries

Docker uses a Node build stage and copies only `out/` into the Python runtime image. FastAPI serves these files alongside `/api/health`. See `../docs/FRONTEND.md` for production and development verification commands. Authenticated APIs and SQLite board data remain planned; keep OpenRouter credentials and calls in the backend, and avoid features requiring a Next.js runtime server.

The agreed product behavior is immediate AI card updates, chat history retained across reloads/sign-ins, existing demo data seeded into new databases, and data retained across container stops. Implement these through the stages and approval checkpoints in `../docs/PLAN.md`; they are not current demo capabilities.
