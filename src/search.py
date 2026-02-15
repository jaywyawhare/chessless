"""
Search that finds the worst legal move: minimizes evaluation for the side to move.
Optimized with zobrist hashing and efficient move generation.
"""
import chess
import time
from typing import Tuple, Optional, List, Dict
from src.evaluator import Evaluator
from src.move_ordering import order_moves
from src.bitboards import see_capture_fast


class WorstMoveSearch:
    def __init__(self, evaluator: Evaluator, max_time: float = 5.0) -> None:
        self.evaluator = evaluator
        self.max_time = max_time
        self.start_time = 0.0
        self.transposition: Dict[int, Tuple[float, int]] = {}
        self.max_tt_size = 500_000
        self.history: Dict[int, Dict[chess.Move, int]] = {}
        self.killers: List[Tuple[Optional[chess.Move], Optional[chess.Move]]] = []

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
        self.killers = [(None, None)] * (depth + 4)
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
        killers = (self.killers[0][0], self.killers[0][1]) if self.killers else (None, None)
        moves = order_moves(board, self.history, killers)
        best_move: Optional[chess.Move] = None
        best_value = float("inf")

        for i, move in enumerate(moves):
            if self.is_timeout():
                raise TimeoutError
            board.push(move)
            if i == 0:
                value = -self._negamax(board, depth - 1, 1, -float("inf"), float("inf"))
            else:
                value = -self._negamax(board, depth - 1, 1, -best_value - 1, -best_value)
                if value > best_value:
                    value = -self._negamax(board, depth - 1, 1, -float("inf"), float("inf"))
            board.pop()
            if value < best_value:
                best_value = value
                best_move = move
                self._store_killer(0, move)
                self._store_history(board, move, depth * depth)
                if best_value <= -45_000:
                    break

        return best_move, best_value

    def _store_killer(self, ply: int, move: chess.Move) -> None:
        if ply >= len(self.killers):
            return
        k1, k2 = self.killers[ply]
        if move != k1:
            self.killers[ply] = (move, k1)

    def _store_history(self, board: chess.Board, move: chess.Move, bonus: int) -> None:
        key = board.zobrist_hash()
        if key not in self.history:
            self.history[key] = {}
        self.history[key][move] = self.history[key].get(move, 0) - bonus

    def _is_good_move(self, board: chess.Board, move: chess.Move) -> bool:
        if board.is_castling(move):
            return True
        if board.is_capture(move):
            see_val = see_capture_fast(board, move)
            if see_val > 0:
                return True
        from_sq = move.from_square
        back_rank = chess.BB_RANK_1 if board.turn == chess.WHITE else chess.BB_RANK_8
        if (1 << from_sq) & back_rank:
            p = board.piece_at(from_sq)
            if p and p.piece_type in (chess.KNIGHT, chess.BISHOP):
                return True
        return False

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        ply: int,
        alpha: float,
        beta: float,
    ) -> float:
        if self.is_timeout():
            raise TimeoutError

        if depth <= 0:
            return self._quiescence(board, ply, alpha, beta)

        key = board.zobrist_hash()
        if key in self.transposition:
            val, d = self.transposition[key]
            if d >= depth and abs(val) < 45_000:
                return val

        legal = list(board.legal_moves)
        if not legal:
            if board.is_check():
                return -50_000 + ply
            return 15_000

        killers = (self.killers[ply][0], self.killers[ply][1]) if ply < len(self.killers) else (None, None)
        moves = order_moves(board, self.history, killers)
        best = -1e9
        best_move: Optional[chess.Move] = None

        for i, move in enumerate(moves):
            board.push(move)
            reduced = depth - 1
            if depth >= 3 and i >= 1 and self._is_good_move(board, move):
                reduced = depth - 2
            score = -self._negamax(board, reduced, ply + 1, -beta, -alpha)
            if reduced != depth - 1 and score > alpha:
                score = -self._negamax(board, depth - 1, ply + 1, -beta, -alpha)
            board.pop()
            if score > best:
                best = score
                best_move = move
                alpha = max(alpha, best)
                if alpha >= beta:
                    if best_move and not board.is_capture(best_move):
                        self._store_killer(ply, best_move)
                        self._store_history(board, best_move, depth * depth)
                    break

        if len(self.transposition) >= self.max_tt_size:
            self.transposition.clear()
        if abs(best) < 45_000:
            self.transposition[key] = (best, depth)
        return best

    def _quiescence(self, board: chess.Board, ply: int, alpha: float, beta: float) -> float:
        legal = list(board.legal_moves)
        if not legal:
            if board.is_check():
                return -50_000 + ply
            return 15_000
        stand = self.evaluator.evaluate_position(board)
        if stand >= beta:
            return beta
        if stand > alpha:
            alpha = stand

        captures = [m for m in legal if board.is_capture(m)]
        if captures:
            captures.sort(key=lambda m: see_capture_fast(board, m))
        for move in captures:
            board.push(move)
            score = -self._quiescence(board, ply + 1, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha
