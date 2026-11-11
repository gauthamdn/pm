from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import require_user
from app.database import read_board, save_board, transaction
from app.models import BoardSnapshot, BoardUpdate, ChatHistory, ChatMessage

router = APIRouter(prefix="/api", tags=["board"])
CurrentUser = Annotated[dict[str, str], Depends(require_user)]


@router.get("/board", response_model=BoardSnapshot)
def get_board(request: Request, user: CurrentUser):
    with transaction(request.app.state.database_path) as db:
        return read_board(db, user["username"])


@router.put("/board", response_model=BoardSnapshot)
def put_board(candidate: BoardUpdate, request: Request, user: CurrentUser):
    with transaction(request.app.state.database_path, write=True) as db:
        return save_board(db, user["username"], candidate)


@router.get("/chat", response_model=ChatHistory)
def get_history(request: Request, user: CurrentUser):
    with transaction(request.app.state.database_path) as db:
        board = read_board(db, user["username"])
        messages = db.execute(
            "SELECT id, turn_id, sequence, role, content, created_at "
            "FROM chat_messages WHERE board_id = ? ORDER BY sequence",
            (board.id,),
        ).fetchall()
        return ChatHistory(
            board=board, messages=[ChatMessage(**dict(row)) for row in messages]
        )
