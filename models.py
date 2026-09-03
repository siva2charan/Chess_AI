from pydantic import BaseModel
from typing import Optional


class MoveResponse(BaseModel):
    player_move: str
    ai_move: Optional[str]
    fen: str
    game_over: bool
    message: str
    turn: str
    is_check: bool
    is_checkmate: bool
    is_stalemate: bool
    score: Optional[float]
    pgn: Optional[str]


class MoveRequest(BaseModel):
    fen: str
    move: str
    difficulty: str


class NewGameResponse(BaseModel):
    fen: str