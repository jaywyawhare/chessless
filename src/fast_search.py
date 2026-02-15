"""
Simplified fast search for worst move.
"""
import chess
import time
from typing import Tuple, Optional, Dict, List
from src.fast_evaluator import FastEvaluator
from src.fast_move_order import ultra_order_moves
from src.fast_tables import board_key


class FastWorstSearch:
    __slots__ = ['evaluator', 'max_time', 'start_time', 'tt', 'max_tt', 'killers']
    
    def __init__(self, evaluator: FastEvaluator, max_time: float = 5.0):
        self.evaluator = evaluator
        self.max_time = max_time
        self.start_time = 0.0
        self.tt: Dict[int, Tuple[float, int]] = {}
        self.max_tt = 200_000
        self.killers: List[Optional[chess.Move]] = []
    
    def is_timeout(self) -> bool:
        return time.time() - self.start_time >= self.max_time
    
    def search(self, board: chess.Board, depth: int) -> Tuple[Optional[chess.Move], float]:
        moves = list(board.legal_moves)
        if not moves:
            return None, 0.0
        if len(moves) == 1:
            return moves[0], self.evaluator.evaluate(board)
        
        self.start_time = time.time()
        self.tt.clear()
        self.killers = [None] * (depth + 10)
        
        best_move = moves[0]
        best_score = float('inf')
        
        for d in range(1, depth + 1):
            if self.is_timeout():
                break
            move, score = self._root(board, d)
            if move:
                best_move = move
                best_score = score
        
        return best_move, best_score
    
    def _root(self, board: chess.Board, depth: int) -> Tuple[Optional[chess.Move], float]:
        killers = (self.killers[0], None)
        moves = ultra_order_moves(board, killers)
        
        best_move = None
        best_score = float('inf')
        
        for move in moves:
            if self.is_timeout():
                break
            
            board.push(move)
            score = -self._negamax(board, depth - 1, 1)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
                self.killers[0] = move
        
        return best_move, best_score
    
    def _negamax(self, board: chess.Board, depth: int, ply: int) -> float:
        if depth <= 0:
            return self._qsearch(board, ply)
        
        key = board_key(board)
        if key in self.tt:
            val, d = self.tt[key]
            if d >= depth:
                return val
        
        moves = list(board.legal_moves)
        if not moves:
            return -50_000 + ply if board.is_check() else 15_000
        
        killer = self.killers[ply] if ply < len(self.killers) else None
        ordered = ultra_order_moves(board, (killer, None))
        
        best = -1e9
        for move in ordered:
            board.push(move)
            score = -self._negamax(board, depth - 1, ply + 1)
            board.pop()
            
            if score > best:
                best = score
        
        if len(self.tt) >= self.max_tt:
            self.tt.clear()
        self.tt[key] = (best, depth)
        
        return best
    
    def _qsearch(self, board: chess.Board, ply: int) -> float:
        if board.is_check():
            moves = list(board.legal_moves)
            if not moves:
                return -50_000 + ply
            best = -1e9
            for move in moves:
                board.push(move)
                score = -self._qsearch(board, ply + 1)
                board.pop()
                if score > best:
                    best = score
            return best
        
        stand = self.evaluator.evaluate(board)
        
        for move in board.generate_legal_captures():
            board.push(move)
            score = -self._qsearch(board, ply + 1)
            board.pop()
            if score > stand:
                stand = score
        
        return stand
