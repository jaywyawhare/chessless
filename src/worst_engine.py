"""
Chess engine that chooses the worst legal move (minimizes position evaluation).
"""
import chess
from typing import Optional
from src.evaluator import Evaluator
from src.search import WorstMoveSearch


class WorstEngine:
    def __init__(self, depth: int = 3, max_time: int = 5) -> None:
        self.depth = depth
        self.max_time = max_time
        self.evaluator = Evaluator()
        self.search = WorstMoveSearch(self.evaluator, max_time=float(max_time))
        self.last_move: Optional[chess.Move] = None

    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Return a legal move that minimizes the position score (worst move)."""
        legal = list(board.legal_moves)
        if not legal:
            return None

        if len(self.evaluator.position_history) > 1000:
            self.evaluator.clear_history()

        try:
            move, _ = self.search.get_worst_move(board, self.depth)
            if move is None or move not in legal:
                move = legal[0]
            if self.last_move and move and len(legal) > 1:
                if (
                    move.from_square == self.last_move.to_square
                    and move.to_square == self.last_move.from_square
                ):
                    legal.remove(move)
                    move = legal[0]
            self.last_move = move
            return move
        except Exception:
            return legal[0]
