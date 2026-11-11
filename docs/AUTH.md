# Part 4: sign-in and sign-out

Open http://localhost:8000 after running `./scripts/start.sh` and sign in with `user` / `password`.

## Session contract

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/session` | Accepts `{"username":"user","password":"password"}`. Returns `{"username":"user"}` and sets a cookie; invalid credentials return 401. |
| GET | `/api/session` | Returns the current user; missing, forged, revoked, or expired tokens return 401. |
| DELETE | `/api/session` | Revokes the current token, clears the cookie, and returns 204. Repeated sign-out is safe. |

Session responses use `Cache-Control: no-store`. The opaque `kanban_session` cookie is HttpOnly, SameSite=Lax, scoped to `/`, and expires after eight hours. Cookie handling follows the [Starlette response API](https://starlette.dev/responses/). The local HTTP app does not set the HTTPS-only Secure flag.

Tokens and expiry times live in backend memory, with independent sessions per browser. Signing in again rotates that browser's token. Restarting the backend requires a new sign-in. `require_user` protects the current-session endpoint and is available for future private board/chat routes. The health endpoint and static assets remain public.

## Frontend behavior

The static homepage initially renders a session-loading screen. The board mounts only after a valid session response. The frontend rechecks every minute and on window focus or returning to a visible tab. A 401 unmounts the board and shows sign-in. Sign-out also clears credential fields and local board state; failed sign-out leaves the board available with an error and retry action.

Failed initial lookup shows a retry screen. A failed background check shows an error without discarding local board edits. In-flight checks are ignored during authentication changes so a stale response cannot restore private content after logout.

Backend persistence is implemented, while the board UI still uses local demo state until Part 7. Reloading or signing out resets UI demo edits. Sign-out only removes session state; saved API board data and chat history remain in SQLite. See [database implementation](DATABASE.md).

The Next.js dev server proxies `/api/` to the running backend on port 8000. Production builds remain static. The standalone `serve` preview has no API; use Docker to test the complete app.

## Manual verification

1. Start the app and visit `/` in a private browser window. Confirm sign-in appears without board cards.
2. Enter wrong credentials and confirm the error. Then use `user` / `password` and confirm five columns and eight demo cards appear.
3. Reload and confirm the session is restored.
4. Sign out, reload, and confirm the board stays hidden.
5. Sign in again. Delete the session cookie through browser developer tools and refocus the window; confirm the form returns. The periodic check also detects the missing session within a minute.

## Automated verification

Backend tests cover invalid credentials/tokens, expiry, rotation, revocation, independent sessions, and cookie/cache attributes. Frontend component tests cover loading, required fields, pending submission, errors/retry, sign-out, expiry checks, stale responses, and retaining local edits during network failures. Browser tests cover the complete flow at desktop and narrow widths, including API failure recovery and cookie properties. Production screenshots of sign-in and the board were visually inspected.

Results: 24 frontend tests and 18 backend tests passed; lint, formatting, type checking, and static build passed. Production browser tests passed 32 scenarios with the four existing narrow drag variants intentionally skipped. The development API-proxy path passed 17 desktop scenarios, with the FastAPI-only check skipped.
