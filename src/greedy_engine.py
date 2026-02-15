"""
Greedy worst move finder - evaluates more moves to find worst.
"""
import chess
from typing import Optional
from src.fast_evaluator import FastEvaluator
from src.fast_move_order import ultra_order_moves


class GreedyWorstEngine:
    __slots__ = ['evaluator']
    
    def __init__(self):
        self.evaluator = FastEvaluator()
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        moves = list(board.legal_moves)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]
        
        ordered = ultra_order_moves(board)
        
        for move in ordered:
            board.push(move)
            if board.is_checkmate():
                board.pop()
                return move
            board.pop()
        
        best_move = ordered[0]
        best_score = float('inf')
        
        for move in ordered[:12]:
            board.push(move)
            score = self.evaluator.evaluate(board)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
        
        return best_move


class HybridWorstEngine:
    __slots__ = ['evaluator', 'max_time']
    
    def __init__(self, depth: int = 2, max_time: float = 1.0):
        self.evaluator = FastEvaluator()
        self.max_time = max_time
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        moves = list(board.legal_moves)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]
        
        ordered = ultra_order_moves(board)
        
        for move in ordered:
            board.push(move)
            if board.is_checkmate():
                board.pop()
                return move
            board.pop()
        
        best_move = ordered[0]
        best_score = float('inf')
        
        for move in ordered[:8]:
            board.push(move)
            score = -self._eval_depth(board, 1)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _eval_depth(self, board: chess.Board, depth: int) -> float:
        if depth <= 0:
            return self.evaluator.evaluate(board)
        
        moves = list(board.legal_moves)
        if not moves:
            return -50_000 if board.is_check() else 15_000
        
        ordered = ultra_order_moves(board)
        
        best = -1e9
        for move in ordered[:5]:
            board.push(move)
            score = -self._eval_depth(board, depth - 1)
            board.pop()
            if score > best:
                best = score
        
        return best
