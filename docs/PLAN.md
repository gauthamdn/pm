# Project implementation plan

Status: Part 1 planning and frontend documentation are complete. User approval of the plan remains pending before Part 2 implementation.

## Agreed behavior

- One board per signed-in user, with five fixed columns that can be renamed.
- Users can create, edit, remove, reorder, and move cards between columns.
- MVP credentials are `user` and `password`.
- AI card changes apply immediately without confirmation.
- Chat history persists across reloads and sign-ins.
- A new database starts with the existing demo columns and eight demo cards.
- Board data and chat history survive container stops and restarts through persistent SQLite storage.
- Next.js static assets are served by FastAPI at `/`; browser API calls use the same origin.
- OpenRouter calls and credentials stay in the backend. Model: `openai/gpt-oss-120b`.
- Preserve the existing visual style and project colors. Keep the implementation within MVP scope.

## Existing frontend

- `frontend/src/app/page.tsx` renders `KanbanBoard`; `layout.tsx` provides metadata and Google fonts.
- `KanbanBoard.tsx` owns in-memory state and pointer drag and drop using dnd-kit.
- `KanbanColumn`, `KanbanCard`, `KanbanCardPreview`, and `NewCardForm` implement the board UI.
- `frontend/src/lib/kanban.ts` contains board types, demo data, ID generation, and movement logic.
- Column renaming, card creation/removal, and card movement exist. Card editing is missing, and changes reset on reload.
- Vitest and React Testing Library cover board interactions and movement logic. Playwright covers loading, adding, and moving cards in Chromium against the Next.js development server.
- Static export, authentication, API integration, persistence, and AI chat are not implemented.

## Part 1: Plan and frontend documentation

- [x] Inspect the frontend and existing test configuration.
- [x] Record the user's decisions and expand frontend tasks, tests, and success criteria.
- [ ] Obtain user approval of this plan before implementation.
- [x] Create `frontend/AGENTS.md` describing the actual component structure, state, styling, commands, and tests; maintain it as implementation proceeds.

Success criteria: the approved plan covers frontend requirements and backend dependencies; frontend documentation describes implemented behavior accurately.

Verification: reviewed the frontend source, package scripts, and test configuration against `frontend/AGENTS.md`. The plan includes implementation checklists, tests, and success criteria for all ten parts and records the four agreed product decisions. Documentation work is complete; the approval checkbox remains open until the user approves the plan. No application changes or application tests were needed for this documentation stage.

## Part 2: Scaffolding

- [ ] Set up Docker, FastAPI in `backend/`, and macOS, Windows, and Linux start/stop scripts in `scripts/`.
- [ ] Serve example static HTML at `/` that calls an API endpoint and displays its response.
- [ ] Configure persistent SQLite storage that normal stop/start operations retain.

Tests and success criteria:

- [ ] Start the container using the documented script and verify the page and API response in a browser.
- [ ] Confirm stopping the container does not delete persistent storage.

## Part 3: Serve the existing frontend

- [ ] Configure Next.js static export and copy the exported assets into the Docker image for FastAPI to serve.
- [ ] Verify asset paths, fonts, initial navigation, and reload at `/` in the production build.
- [ ] Preserve demo board interactions during this stage.
- [ ] Allow Playwright to target the Docker-served app while retaining convenient local frontend tests.
- [ ] Inspect desktop and narrow-screen layouts for clipping, spacing, wrapping, and focus visibility; fix clear UI defects.

Tests:

- [ ] Run lint, unit/component tests, and the production build.
- [ ] Run browser tests against the exported app: five columns, eight demo cards, column renaming, card creation/removal, and drag and drop.
- [ ] Cover reordering, movement between columns, drops into empty columns, and drag cancellation.
- [ ] Check console/network errors on initial load and reload.

Success criteria: the demo board works at `/` from Docker without a Next.js runtime server, and remains usable at desktop and narrow widths.

## Part 4: Sign-in and sign-out

- [ ] Agree session API contracts with the backend: session lookup, sign-in, and sign-out using a backend-managed session cookie.
- [ ] Add labeled username/password inputs, submit/pending states, invalid-credentials feedback, and service-error feedback.
- [ ] Resolve session state before displaying the board, with a loading state that avoids flashing private content.
- [ ] Show the board after successful sign-in and provide an accessible sign-out action.
- [ ] Clear private frontend state on sign-out or session expiry while retaining saved board/chat data on the server.
- [ ] Validate credentials and protect API routes in the backend rather than relying on client-side checks.

Tests:

- [ ] Component tests cover validation, pending submission, errors, successful sign-in, and sign-out.
- [ ] Browser tests cover a fresh visit, rejected/accepted credentials, reload with an active session, and sign-out.
- [ ] Verify unauthenticated API requests are rejected and returning after sign-out does not expose board/chat content.

Success criteria: `user` / `password` unlocks the board; sign-out returns to the form without deleting saved data.

## Part 5: Database modeling and frontend contracts

- [ ] Propose the database schema as JSON and document it in `docs/`, including users, boards, fixed columns, ordered cards, and persistent chat messages.
- [ ] Define stable IDs, card title/details, column titles, card ordering, and message ordering.
- [ ] Define request/response shapes for session, board reads/mutations, chat history, and chat submission, including errors.
- [ ] Seed demo data only when a user's board is first created; later loads must not recreate removed cards.
- [ ] Define how successful AI responses return persisted messages and the resulting board to the UI.
- [ ] Obtain user sign-off on the schema and database approach before implementing it.

Validation and success criteria:

- [ ] Walk through card creation/editing/removal/movement, column renaming, chat reload, and sign-out/sign-in using the proposed contracts.
- [ ] The approved schema supports these operations without adding account management or multiple-board UI.

## Part 6: Backend APIs

- [ ] Implement authenticated board reads and mutations, database creation, and demo seeding.
- [ ] Support card creation, editing, removal, movement/reordering, and column renaming.
- [ ] Enforce user ownership and fixed columns; return persisted results after successful mutations.
- [ ] Implement persistent chat history reads in preparation for AI integration.
- [ ] Test validation, ownership, ordering, persistence, and failure behavior with backend tests.

Success criteria: APIs match the approved frontend contracts, failed mutations do not partially save, and saved data survives reloads and restarts.

## Part 7: Persistent frontend board

- [ ] Replace runtime demo initialization with authenticated board loading; retain demo data as the agreed seed and test fixture.
- [ ] Add a small typed API layer using same-origin requests and the backend session.
- [ ] Provide loading, load-error/retry, empty-column, and save-pending/error states.
- [ ] Add card title/details editing with save and cancel. Reject empty card titles and empty column names.
- [ ] Commit column renames on submit or blur rather than sending a request for every keystroke.
- [ ] Connect all board actions to the backend and reconcile the UI with the saved response.
- [ ] If drag feedback updates locally before saving, restore the previous state and display an error when saving fails.
- [ ] Preserve form input on request failures, prevent duplicate submissions, and prevent overlapping saves from overwriting newer state.
- [ ] Support keyboard card movement and accessible labels/focus handling. Ensure edit/remove controls do not accidentally initiate dragging.

Tests:

- [ ] Component tests cover loading, validation, edit/cancel, pending saves, failed saves, and session expiry using controlled API responses.
- [ ] Browser tests against the real backend create, edit, remove, rename, reorder, and move cards, then reload to verify persistence.
- [ ] Verify empty-column drops and keyboard movement preserve card order.
- [ ] Verify the same board returns after sign-out/sign-in and container restart with the same storage.
- [ ] Isolate test storage so repeatable tests do not modify the user's database or depend on previous runs.

Success criteria: every board action persists, the five columns remain fixed, and request failures never silently discard input or present unsaved changes as saved.

## Part 8: AI connectivity

- [ ] Add backend-only OpenRouter connectivity using the root `.env` key and configured model.
- [ ] Run the simple `2+2` connectivity check without exposing credentials.
- [ ] Define useful AI-unavailable errors for the future chat UI.

Tests and success criteria:

- [ ] A live backend call returns the expected answer; routine tests mock the provider.
- [ ] No provider credentials appear in browser requests, frontend assets, or errors.

## Part 9: Structured AI responses

- [ ] Send the persisted board JSON, user message, and conversation history to the AI from the backend.
- [ ] Validate structured output containing assistant text and optional board changes.
- [ ] Apply valid changes immediately and persist messages and resulting board consistently.
- [ ] Return saved messages and authoritative board state to the frontend.
- [ ] Define failure/retry behavior so malformed responses and provider failures leave the board unchanged and do not duplicate messages.
- [ ] Prevent stale AI responses from silently overwriting concurrent manual edits; prefer an explicit conflict response and reload over automatic merging.

Tests and success criteria:

- [ ] Test reply-only output, single/multiple card changes, invalid output, unknown card/column references, provider failures, and concurrent board edits.
- [ ] Saved chat and applied changes remain consistent after reload, sign-out/sign-in, and container restart.

## Part 10: AI chat sidebar

- [ ] Build a sidebar matching the existing typography and colors: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, and gray `#888888`.
- [ ] Keep the board readable beside chat on desktop; use a collapsible panel on narrow screens with accessible controls and focus handling.
- [ ] Load saved conversation history in message order when the signed-in workspace opens.
- [ ] Add a labeled composer, send action, pending indicator, and clear failure/retry behavior; prevent empty messages and duplicate sends.
- [ ] Render message text without executing returned HTML.
- [ ] Keep new replies visible without pulling readers away from older messages they are reading.
- [ ] Apply returned board state immediately after a successful AI change, without confirmation or page reload.
- [ ] Make pending/conflict behavior recoverable without losing drafts or presenting unapplied changes as successful.
- [ ] Preserve form input when opening/closing the sidebar and provide predictable keyboard navigation.

Tests:

- [ ] Component tests cover history loading/order, composer validation, pending state, failure/retry, and board updates.
- [ ] Browser tests cover normal replies and AI creation/editing/movement of one or multiple cards, using deterministic provider responses behind the real application API.
- [ ] Verify immediate updates, reload persistence, sign-out/sign-in history, and board/chat survival after container restart.
- [ ] Exercise provider failures and concurrent manual edits; confirm no duplicate cards/messages or silent loss of saved edits.
- [ ] Inspect desktop/narrow layouts, long messages/titles, scrolling, keyboard navigation, focus, and loading/error states.

Success criteria: users can chat, see valid AI changes immediately, and return to the saved conversation; the sidebar remains usable alongside the board and failures have clear recovery paths.

## Completion checks

- [ ] Run lint, frontend unit/component tests, static production build, backend tests, and browser integration tests against the Docker-served app.
- [ ] Fix test failures, flakiness, and clear UI defects discovered during verification. Reproduce bugs through the user flow before fixing their root cause.
- [ ] Complete one real OpenRouter chat smoke test after deterministic tests pass.
- [ ] Verify the full flow: start, sign in, edit board, ask AI to change cards, reload, sign out/in, restart, and confirm board/history persistence.
- [ ] Keep documentation concise, update frontend instructions, and record actual verification outcomes and remaining limitations in `docs/`.
