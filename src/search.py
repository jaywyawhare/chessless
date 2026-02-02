"""
Search that finds the worst legal move: minimizes evaluation for the side to move.
Uses negamax with iterative deepening, transposition table, quiescence, and time limit.
"""
import chess
import time
from typing import Tuple, Optional, List, Dict
from src.evaluator import Evaluator
from src.move_ordering import order_moves


class WorstMoveSearch:
    def __init__(self, evaluator: Evaluator, max_time: float = 5.0) -> None:
        self.evaluator = evaluator
        self.max_time = max_time
        self.start_time = 0.0
        self.transposition: Dict[str, Tuple[float, int]] = {}
        self.max_tt_size = 500_000
        self.history: Dict[str, Dict[chess.Move, int]] = {}

    def is_timeout(self) -> bool:
        return time.time() - self.start_time >= self.max_time

    def get_worst_move(
        self, board: chess.Board, depth: int
    ) -> Tuple[Optional[chess.Move], float]:
        legal = list(board.legal_moves)
        if not legal:
            return None, 0.0

        self.start_time = time.time()
        self.transposition.clear()
        best_move: Optional[chess.Move] = None
        best_value = 1e9

        for d in range(1, depth + 1):
            if self.is_timeout():
                break
            try:
                move, value = self._root(board, d)
                if move is not None:
                    best_move = move
                    best_value = value
            except TimeoutError:
                break

        if best_move is None:
            best_move = legal[0]
            best_value = self.evaluator.evaluate_position(board)
        return best_move, best_value

    def _root(self, board: chess.Board, depth: int) -> Tuple[Optional[chess.Move], float]:
        moves = order_moves(board, self.history)
        best_move: Optional[chess.Move] = None
        best_value = float("inf")

        for i, move in enumerate(moves):
            if self.is_timeout():
                raise TimeoutError
            board.push(move)
            if i == 0:
                value = -self._negamax(board, depth - 1, -float("inf"), float("inf"))
            else:
                value = -self._negamax(board, depth - 1, -best_value - 1, -best_value)
                if value > best_value:
                    value = -self._negamax(board, depth - 1, -float("inf"), float("inf"))
            board.pop()
            if value < best_value:
                best_value = value
                best_move = move
                if best_value <= -1e7:
                    break

        return best_move, best_value

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> float:
        if self.is_timeout():
            raise TimeoutError

        if depth <= 0:
            return self._quiescence(board, alpha, beta)

        key = board.fen()
        if key in self.transposition:
            val, d = self.transposition[key]
            if d >= depth:
                return val

        legal = list(board.legal_moves)
        if not legal:
            if board.is_check():
                return -10_000
            return 0.0

        best = -1e9
        moves = order_moves(board, self.history)

        for move in moves:
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            if score > best:
                best = score
                alpha = max(alpha, best)
                if alpha >= beta:
                    break

        if len(self.transposition) >= self.max_tt_size:
            self.transposition.clear()
        self.transposition[key] = (best, depth)
        return best

    def _quiescence(self, board: chess.Board, alpha: float, beta: float) -> float:
        stand = self.evaluator.evaluate_position(board)
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        captures = [m for m in board.legal_moves if board.is_capture(m)]
        for move in captures:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha
