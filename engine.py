import os
import chess
import chess.engine

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

STOCKFISH_PATH = os.path.join(
    BASE_DIR,
    "stockfish",
    "stockfish-windows-x86-64-avx2.exe"
)

if not os.path.exists(STOCKFISH_PATH):
    raise FileNotFoundError(
        f"Stockfish not found: {STOCKFISH_PATH}"
    )


class ChessEngine:

    def __init__(self):

        self.engine = chess.engine.SimpleEngine.popen_uci(
            STOCKFISH_PATH
        )

    def get_best_move(
        self,
        board: chess.Board,
        difficulty: str = "medium"
    ):

        difficulty = difficulty.lower()

        if difficulty == "easy":
            limit = chess.engine.Limit(depth=5)

        elif difficulty == "medium":
            limit = chess.engine.Limit(depth=10)

        elif difficulty == "hard":
            limit = chess.engine.Limit(depth=18)

        else:
            limit = chess.engine.Limit(depth=10)

        result = self.engine.play(
            board,
            limit
        )

        return result.move

    def close(self):

        if self.engine:
            self.engine.quit()