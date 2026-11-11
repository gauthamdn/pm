from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

COLUMN_IDS = (
    "col-backlog",
    "col-discovery",
    "col-progress",
    "col-review",
    "col-done",
)

Identifier = Annotated[str, StringConstraints(min_length=1)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Card(APIModel):
    id: Identifier
    title: Title
    details: str = ""


class Column(APIModel):
    id: Identifier
    title: Title
    cardIds: list[Identifier]


class BoardData(APIModel):
    columns: list[Column]
    cards: dict[Identifier, Card]

    @model_validator(mode="after")
    def validate_board(self) -> Self:
        if tuple(column.id for column in self.columns) != COLUMN_IDS:
            raise ValueError("The five fixed columns must keep their IDs and order.")
        card_ids = [card_id for column in self.columns for card_id in column.cardIds]
        if len(card_ids) != len(set(card_ids)):
            raise ValueError("Each card must appear in exactly one column.")
        if set(card_ids) != self.cards.keys():
            raise ValueError("Column references must match the card map exactly.")
        if any(key != card.id for key, card in self.cards.items()):
            raise ValueError("Card map keys must match card IDs.")
        return self


class BoardUpdate(BoardData):
    expected_revision: int = Field(ge=0)


class BoardSnapshot(BoardData):
    id: Identifier
    revision: int = Field(ge=0)


class ChatMessage(APIModel):
    id: Identifier
    turn_id: Identifier
    sequence: int = Field(ge=0)
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatHistory(APIModel):
    board: BoardSnapshot
    messages: list[ChatMessage]
