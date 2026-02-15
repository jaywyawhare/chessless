"""
Chess engine that chooses the worst legal move (minimizes position evaluation).
"""
import chess
from typing import Optional
from src.evaluator import Evaluator
from src.search import WorstMoveSearch


class WorstEngine:
    __slots__ = ['depth', 'max_time', 'evaluator', 'search', 'last_move']
    
    def __init__(self, depth: int = 3, max_time: float = 5.0) -> None:
        self.depth = depth
        self.max_time = max_time
        self.evaluator = Evaluator()
        self.search = WorstMoveSearch(self.evaluator, max_time=max_time)
        self.last_move: Optional[chess.Move] = None

    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        legal = list(board.legal_moves)
        if not legal:
            return None
        if len(legal) == 1:
            return legal[0]

        try:
            move, _ = self.search.get_worst_move(board, self.depth)
            if move is None or move not in legal:
                move = legal[0]
            self.last_move = move
            return move
        except Exception:
            return legal[0]
