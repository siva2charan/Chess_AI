from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import chess
import chess.pgn

from .models import (
    MoveRequest,
    MoveResponse,
    NewGameResponse
)

from .engine import ChessEngine


# Small local request model for /ai-move. It only needs a FEN and a
# difficulty — unlike /move it has no "move" field, because this endpoint
# is used to let the engine move with no player move preceding it (needed
# when the human chooses to play Black, so White/the engine has to make
# the opening move first).
class AiMoveRequest(BaseModel):
    fen: str
    difficulty: str

app = FastAPI(
    title="Chess AI API",
    version="1.0.0",
    description="FastAPI Chess AI using Stockfish"
)

# NOTE: allow_origins=["*"] cannot be combined with allow_credentials=True —
# that combination violates the CORS spec and browsers will reject the
# preflight response (you'll see "blocked by CORS policy" in the console
# even though the server looks like it's responding correctly).
#
# Since this app doesn't use cookies/auth headers, credentials aren't
# needed, so we simply turn them off. If you later need credentialed
# requests, replace "*" with an explicit list of allowed origins instead,
# e.g. allow_origins=["http://localhost:5000", "https://yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

engine = ChessEngine()


@app.get("/")
def home():
    return {
        "name": "Chess AI API",
        "version": "1.0.0",
        "engine": "Stockfish",
        "status": "Running"
    }


@app.post(
    "/new-game",
    response_model=NewGameResponse
)
def new_game():

    board = chess.Board()

    return {
        "fen": board.fen()
    }


@app.post("/ai-move")
def ai_move(request: AiMoveRequest):
    """
    Lets the engine make a move on its own, with no player move first.

    This is needed for the "play as Black" case: the board always starts
    with White to move, so if the human picked Black, the engine (playing
    White) has to make the opening move before the human can do anything.
    The regular /move endpoint always expects a player move to push first,
    so it can't be reused for this.
    """

    if request.difficulty not in [
        "easy",
        "medium",
        "hard"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty"
        )

    try:

        board = chess.Board(request.fen)

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid FEN"
        )

    if board.is_game_over():

        raise HTTPException(
            status_code=400,
            detail="Game is already finished"
        )

    try:

        ai_move_result = engine.get_best_move(
            board,
            request.difficulty
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

    if ai_move_result is None:

        raise HTTPException(
            status_code=400,
            detail="Engine has no legal move for this position"
        )

    board.push(ai_move_result)

    score = None

    try:

        score = engine.get_evaluation(
            board
        )

    except Exception:
        pass

    game = chess.pgn.Game.from_board(board)

    message = "AI moved"

    if board.is_checkmate():

        message = "Checkmate"

    elif board.is_stalemate():

        message = "Stalemate"

    elif board.is_insufficient_material():

        message = "Draw"

    elif board.can_claim_threefold_repetition():

        message = "Threefold Repetition"

    elif board.can_claim_fifty_moves():

        message = "50 Move Rule"

    elif board.is_check():

        message = "Check"

    # NOTE: no response_model here — this endpoint doesn't have a
    # "player_move" the way /move does, so it deliberately returns a
    # plain dict rather than being forced into MoveResponse's shape.
    return {

        "ai_move": ai_move_result.uci(),

        "fen": board.fen(),

        "game_over": board.is_game_over(),

        "message": message,

        "turn": "white" if board.turn else "black",

        "is_check": board.is_check(),

        "is_checkmate": board.is_checkmate(),

        "is_stalemate": board.is_stalemate(),

        "score": score,

        "pgn": str(game)

    }


@app.post(
    "/move",
    response_model=MoveResponse
)
def make_move(request: MoveRequest):

    if request.difficulty not in [
        "easy",
        "medium",
        "hard"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty"
        )

    try:

        board = chess.Board(request.fen)

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid FEN"
        )

    if board.is_game_over():

        game = chess.pgn.Game.from_board(board)

        return {

            "player_move": request.move,

            "ai_move": None,

            "fen": board.fen(),

            "game_over": True,

            "message": "Game already finished",

            "turn": "white" if board.turn else "black",

            "is_check": board.is_check(),

            "is_checkmate": board.is_checkmate(),

            "is_stalemate": board.is_stalemate(),

            "score": None,

            "pgn": str(game)

        }

    # Normalize the move string (defensive: strip whitespace, lowercase
    # promotion suffix if present, e.g. "E7E8Q" -> "e7e8q")
    move_str = (request.move or "").strip().lower()

    try:

        player_move = chess.Move.from_uci(move_str)

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid move format"
        )

    if player_move not in board.legal_moves:

        raise HTTPException(
            status_code=400,
            detail="Illegal move"
        )

    board.push(player_move)

    if board.is_game_over():

        game = chess.pgn.Game.from_board(board)

        message = "Game Over"

        if board.is_checkmate():
            message = "Checkmate"

        elif board.is_stalemate():
            message = "Stalemate"

        elif board.is_insufficient_material():
            message = "Draw"

        elif board.can_claim_threefold_repetition():
            message = "Threefold Repetition"

        elif board.can_claim_fifty_moves():
            message = "50 Move Rule"

        return {

            "player_move": request.move,

            "ai_move": None,

            "fen": board.fen(),

            "game_over": True,

            "message": message,

            "turn": "white" if board.turn else "black",

            "is_check": board.is_check(),

            "is_checkmate": board.is_checkmate(),

            "is_stalemate": board.is_stalemate(),

            "score": None,

            "pgn": str(game)

        }

    try:

        ai_move = engine.get_best_move(
            board,
            request.difficulty
        )

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

    if ai_move is None:

        game = chess.pgn.Game.from_board(board)

        return {

            "player_move": request.move,

            "ai_move": None,

            "fen": board.fen(),

            "game_over": board.is_game_over(),

            "message": "AI has no legal move",

            "turn": "white" if board.turn else "black",

            "is_check": board.is_check(),

            "is_checkmate": board.is_checkmate(),

            "is_stalemate": board.is_stalemate(),

            "score": None,

            "pgn": str(game)

        }

    board.push(ai_move)

    score = None

    try:

        score = engine.get_evaluation(
            board
        )

    except Exception:
        pass

    game = chess.pgn.Game.from_board(board)

    message = "AI moved"

    if board.is_checkmate():

        message = "Checkmate"

    elif board.is_stalemate():

        message = "Stalemate"

    elif board.is_insufficient_material():

        message = "Draw"

    elif board.can_claim_threefold_repetition():

        message = "Threefold Repetition"

    elif board.can_claim_fifty_moves():

        message = "50 Move Rule"

    elif board.is_check():

        message = "Check"

    return {

        "player_move": request.move,

        "ai_move": ai_move.uci(),

        "fen": board.fen(),

        "game_over": board.is_game_over(),

        "message": message,

        "turn": "white" if board.turn else "black",

        "is_check": board.is_check(),

        "is_checkmate": board.is_checkmate(),

        "is_stalemate": board.is_stalemate(),

        "score": score,

        "pgn": str(game)

    }