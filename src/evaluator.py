"""
Position evaluation for the worst-move engine.
Score is from the side-to-move perspective: positive = good for side to move.
The search minimizes this score to find the worst move.
"""
import chess
from typing import Dict


class Evaluator:
    def __init__(self) -> None:
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }
        self._cache: Dict[str, float] = {}
        self.max_cache_size = 100_000
        self.position_history: Dict[str, int] = {}

    def evaluate_position(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -10_000 if board.turn else 10_000
        if board.is_stalemate():
            return 0.0

        key = board.fen()
        if key in self._cache:
            return self._cache[key]

        score = self._material(board) + self._mobility(board)
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score

    def _material(self, board: chess.Board) -> float:
        s = 0.0
        for pt, v in self.piece_values.items():
            s += len(board.pieces(pt, chess.WHITE)) * v
            s -= len(board.pieces(pt, chess.BLACK)) * v
        return s if board.turn else -s

    def _mobility(self, board: chess.Board) -> float:
        s = 0.0
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p:
                continue
            n = len(list(board.attacks(sq)))
            s += n * (1 if p.color == board.turn else -1)
        return s * 5.0

    def clear_history(self) -> None:
        self.position_history.clear()
