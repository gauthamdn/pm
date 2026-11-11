# Part 5: database proposal

Status: ready for user review. No application database or database APIs have been implemented. Approval is required before Part 6.

The proposed schema and exact demo seed are in [database-schema.json](database-schema.json). Its column declarations and constraints describe the proposed SQL tables; the application will not become a dynamic schema loader.

## Storage and ownership

Use Python's standard-library `sqlite3` with parameterized SQL and short-lived connections. The existing Docker volume stores `/app/data/kanban.sqlite3`, including SQLite sidecar files. Enable foreign keys on every connection, WAL mode, and a five-second busy timeout. Use explicit write transactions with `BEGIN IMMEDIATE`; do not hold a transaction open during an OpenRouter call. These choices follow the [SQLite transaction](https://www.sqlite.org/lang_transaction.html), [foreign-key](https://www.sqlite.org/foreignkeys.html), and [Python sqlite3](https://docs.python.org/3/library/sqlite3.html) documentation.

| Table | Purpose | Main constraints |
| --- | --- | --- |
| `users` | Stable identity for current and future users | UUID primary key; unique username |
| `boards` | One board per user | Unique user foreign key; nonnegative revision |
| `board_columns` | Five fixed slots with editable titles | Board-scoped IDs; unique position 0-4; fixed ID allowlist |
| `cards` | Titles, optional details, column membership, and order | Board-scoped IDs; composite foreign key to the board's column; unique position per column |
| `chat_messages` | Ordered completed user/assistant turns | Board-scoped IDs; unique sequence; unique role per turn |

The unique constraints supply the indexes needed for owner lookup, ordered columns/cards/messages, and chat retry lookup. Do not add duplicate indexes initially.

All board, card, and conversation access derives the board from the authenticated user. The browser never chooses a user or board owner. Every card/column lookup includes `board_id`; the existing `col-*` and `card-1` through `card-8` IDs can therefore be reused safely for another user's seed. The composite card foreign key prevents cross-board column references.

The schema supports multiple users without adding registration, password management, or multiple-board UI. MVP credentials remain hardcoded. Part 4 sessions stay in memory and resolve the username to its database identity when private data APIs are implemented. No session or password table is proposed.

## Initialization and seeding

1. After approval, create the database and version-1 schema when absent. Record `PRAGMA user_version = 1` in the initialization transaction. Later changes use explicit versioned migrations, preserving existing data.
2. Create the MVP `user` identity and its board, five columns, and eight cards atomically. Use server UUIDs for user/board IDs, preserve all existing demo card/column IDs and text, and start the revision at zero with no chat messages.
3. Seed only when a board is first created. Finding zero cards is a valid empty board and must never trigger reseeding. Reload, sign-in, and container restart only read existing data.
4. A future provisioned user receives their own board and seed under the same ownership rules. Usernames are unique, and `boards.user_id` enforces one board per user.

The JSON proposal captures `initialData` directly from `frontend/src/lib/kanban.ts`. Part 6 will place the approved seed in the backend; it will no longer initialize browser runtime state after Part 7 integration.

## Mapping to the current frontend

A board snapshot adds `id` and `revision` to the current `BoardData` shape:

```ts
type BoardSnapshot = {
  id: string;
  revision: number;
  columns: { id: string; title: string; cardIds: string[] }[];
  cards: Record<string, { id: string; title: string; details: string }>;
};
```

The full five-column/eight-card payload is reproduced in the JSON seed. `columns[].cardIds` is derived from card rows ordered by their stored `position`; it is not stored a second time in SQLite.

Column IDs and order remain fixed. Only titles can change. IDs are nonempty strings. Card titles and column titles are trimmed and must be nonempty; card details may be an empty string. Every card must appear exactly once in one of the five columns, with no unknown references or mismatched card-map keys. The backend validates the entire candidate before saving.

New manual cards use `crypto.randomUUID()` on the frontend; new AI cards receive backend-generated UUIDs. These conventions coexist with the unchanged legacy seed IDs. Card and column IDs remain stable through edits and moves.

## API contracts

The existing [session API](AUTH.md) stays unchanged. All endpoints below require `require_user`, use the current user's board, and return `Cache-Control: no-store`.

| Method | Path | Request | Success response | Stage |
| --- | --- | --- | --- | --- |
| GET | `/api/board` | None | Board snapshot | Part 6 |
| PUT | `/api/board` | `{expected_revision, columns, cards}` | Saved board snapshot | Part 6 |
| GET | `/api/chat` | None | `{board: <snapshot>, messages: [...]}` from one read transaction | Part 6 history read; Part 10 UI |
| POST | `/api/chat` | `{turn_id, expected_revision, message}` | `{board: <snapshot>, messages: [<user message>, <assistant message>]}` | Part 9 |

`PUT /api/board` saves one complete candidate board rather than exposing separate mutation routes for every UI action. Creation, editing, removal, reordering, movement, and column renaming all map to the current frontend state model. The endpoint rejects changes to the fixed column set/order and checks the expected revision before any write. It updates column titles and replaces the board's card rows inside one transaction, preserving IDs and assigning dense positions. Atomic replacement avoids intermediate uniqueness collisions during swaps and cross-column moves. No chat message references a mutable card row by foreign key.

For example, moving `card-1` to Review removes it from Backlog's `cardIds` and appends it to Review's `cardIds`; all other cards remain in the candidate. A successful save from revision 0 returns revision 1. A stale revision returns 409 without applying any part of the candidate. The frontend reloads the latest state and lets the user retry; no automatic merge is proposed.

Chat messages have this shape:

```json
{
  "id": "<message UUID>",
  "turn_id": "<client request UUID>",
  "sequence": 0,
  "role": "user",
  "content": "Move Align roadmap themes to Review.",
  "created_at": "2026-11-11T10:00:00.000Z"
}
```

The sequence is zero-based per board and controls display order; timestamps are UTC metadata. The assistant reply uses the same turn ID and the next sequence. `GET /api/chat` returns a coherent board/history snapshot, allowing the full chat workspace to initialize with one request in Part 10. Chat requests accept the message only; the backend supplies persisted board state and history to the model.

Errors retain the existing FastAPI `{"detail": ...}` envelope:

| Status | Meaning | State change |
| --- | --- | --- |
| 401 | Missing, expired, or invalid session | None |
| 409 | Stale revision, or reusing a completed turn ID with different message text | None |
| 422 | Invalid request, empty title/message, changed fixed columns, duplicate membership, or invalid reference | None |
| 502 | Invalid AI structured response | None |
| 503 | Provider unavailable or database still busy after its timeout | None |

Normal FastAPI field-validation details may be a list. Frontend errors should present clear messages rather than raw SQL/provider exceptions.

## AI consistency and retries

1. Read the board, revision, and ordered history in one short transaction. Check for a completed turn ID first: matching user text returns its saved message pair and the current board, even if the retry carries the old revision. Otherwise reject an already-stale `expected_revision` before calling the provider. Replays neither call the AI nor reapply old changes.
2. Call OpenRouter outside a database transaction and validate the optional board update against the same board invariants. The AI does not choose an owner or modify metadata such as revision.
3. Start a write transaction and recheck the completed turn ID before the revision. If not already completed, apply valid board changes immediately, append the user/assistant pair, increment revision once, update `updated_at`, and commit. A concurrent board save or chat completion causes 409 if the turn has not already completed. Manual board saves also increment revision and update `updated_at`.
4. Reply-only turns also increment revision: this single counter tracks board and conversation changes, keeping the context used by concurrent AI calls consistent.
5. Persist only completed turns. Provider failures, invalid output, and revision conflicts leave both board and history unchanged; the UI retains the failed draft for retry. There is no persisted pending/failed-turn queue in this MVP.
6. Reuse the same client turn ID when retrying an uncertain request. The unique `(board_id, turn_id, role)` constraint and transactional recheck prevent duplicate messages or repeated board application. The UI merges returned messages by their stable IDs. Simultaneous identical requests may both reach the provider, but only one turn is committed; exactly-once provider execution is not proposed.

## Scenario review and implementation acceptance

| Scenario | Required outcome |
| --- | --- |
| New database | One `user`, one board, five fixed columns, eight exact seed cards, revision 0, no messages |
| Create/edit/remove card | Saved candidate has correct membership and title/details; IDs remain stable for existing cards |
| Reorder/move/drop into empty column | Dense order is reconstructed exactly from `cardIds`, without duplicate positions |
| Rename a column | Title changes, while ID/order and column count stay fixed |
| Delete all cards and restart | Board stays empty; demo cards do not return |
| Sign out/in or restart | Board and completed messages remain in the volume; restarted sessions require sign-in |
| Future second user | Separate board/history, including safe reuse of seeded card IDs; no owner supplied by the browser |
| AI changes multiple cards | All changes and both messages commit together, with one revision increment |
| Failure or stale AI response | No partial card/message writes; draft can be retried against refreshed context |
| Successful response lost in transit | Retry returns the saved message pair and current board, without applying changes twice |

Validation of this proposal uses JSON parsing, exact seed comparison, and disposable in-memory SQLite only. Part 6 must add real API/unit/integration tests for initialization, ownership, ordering, rollback, revisions, and restart persistence against isolated test storage before connecting the frontend in Part 7.

Validation completed: all five table definitions executed successfully; two users each received the exact five-column/eight-card seed with shared legacy IDs. Invalid ownership, column references, duplicate ordering, blank titles, and a sixth column were rejected. A candidate snapshot exercised creation, editing, removal, movement, reordering, and renaming while retaining the other user's data. Revision comparison rejected a stale write. Rollback restored cards/messages, and message ordering plus turn-role uniqueness held. These are proposal-level checks, not claims that the future endpoints already exist. No application database file or persistent volume was touched.

## Approval checkpoint

Please approve or request changes to the five-table schema, full-board save contract, shared revision counter, and completed-turn-only chat persistence. Per [Part 5 of PLAN.md](PLAN.md), this checkpoint remains open until the user signs off. No schema or seed will be applied to the running app before that approval.
