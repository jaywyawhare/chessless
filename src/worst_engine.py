"""
Chess engine that chooses the worst legal move.
Uses greedy selection for maximum speed.
"""
import chess
from typing import Optional
from src.greedy_engine import GreedyWorstEngine, HybridWorstEngine


class WorstEngine:
    __slots__ = ['_engine', 'depth', 'max_time']
    
    def __init__(self, depth: int = 2, max_time: float = 1.0):
        self.depth = depth
        self.max_time = max_time
        if depth <= 1:
            self._engine = GreedyWorstEngine()
        else:
            self._engine = HybridWorstEngine(depth=depth, max_time=max_time)
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        return self._engine.get_worst_move(board)
