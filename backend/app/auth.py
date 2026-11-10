from secrets import compare_digest, token_urlsafe
from time import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

SESSION_COOKIE = "kanban_session"
SESSION_MAX_AGE = 8 * 60 * 60
NO_STORE = {"Cache-Control": "no-store"}

router = APIRouter(prefix="/api/session", tags=["session"])


class Credentials(BaseModel):
    username: str
    password: str


def require_user(request: Request) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE)
    sessions = request.app.state.sessions
    if sessions.get(token, 0) <= time():
        sessions.pop(token, None)
        raise HTTPException(401, "Please sign in.", headers=NO_STORE)
    return {"username": "user"}


@router.get("")
def current_session(
    response: Response, user: Annotated[dict[str, str], Depends(require_user)]
) -> dict[str, str]:
    response.headers.update(NO_STORE)
    return user


@router.post("")
def sign_in(credentials: Credentials, request: Request, response: Response):
    if not (
        compare_digest(credentials.username.encode(), b"user")
        and compare_digest(credentials.password.encode(), b"password")
    ):
        raise HTTPException(401, "Invalid username or password.", headers=NO_STORE)

    sessions = request.app.state.sessions
    sessions.pop(request.cookies.get(SESSION_COOKIE), None)
    token = token_urlsafe(32)
    sessions[token] = time() + SESSION_MAX_AGE
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        expires=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.headers.update(NO_STORE)
    return {"username": "user"}


@router.delete("", status_code=204)
def sign_out(request: Request):
    request.app.state.sessions.pop(request.cookies.get(SESSION_COOKIE), None)
    response = Response(status_code=204, headers=NO_STORE)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return response
