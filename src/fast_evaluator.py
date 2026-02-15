"""
Fast position evaluation using precomputed tables.
"""
import chess
from typing import Dict
from src.fast_tables import (
    popcount, lsb, square_bb, file_of, rank_of,
    FAST_PIECE_VALUES, FAST_PIECE_VALUES_LIGHT,
    BB_CENTER, BB_RIM, BB_BACKRANK_WHITE, BB_BACKRANK_BLACK,
    BB_KING_SHIELD_WHITE, BB_KING_SHIELD_BLACK,
    KNIGHT_HOME_WHITE, KNIGHT_HOME_BLACK,
    BISHOP_HOME_WHITE, BISHOP_HOME_BLACK,
    KING_ATTACKS, PAWN_ATTACKS_WHITE, PAWN_ATTACKS_BLACK, KNIGHT_ATTACKS,
    board_key, fast_material, fast_hanging, fast_king_attackers, fast_king_escape,
)


class FastEvaluator:
    __slots__ = ['_cache', 'max_cache_size']
    
    def __init__(self):
        self._cache: Dict[int, float] = {}
        self.max_cache_size = 50_000
    
    def evaluate(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -50_000 if board.turn else 50_000
        if board.is_stalemate():
            return 25_000
        if board.can_claim_draw():
            return 15_000
        
        key = board_key(board)
        if key in self._cache:
            return self._cache[key]
        
        us = board.turn
        score = self._fast_eval(board, us)
        
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score
    
    def _fast_eval(self, board: chess.Board, us: bool) -> float:
        them = not us
        score = 0.0
        
        score += fast_material(board)
        
        ksq = board.king(us)
        if ksq is not None:
            attackers = fast_king_attackers(board, us)
            score -= attackers * 1500
            
            escape_bad = fast_king_escape(board, us)
            score -= escape_bad * 300
        
        hanging = fast_hanging(board, us)
        score -= hanging * 600
        
        our_pawns = board.pieces_mask(chess.PAWN, us)
        shield = BB_KING_SHIELD_WHITE if us else BB_KING_SHIELD_BLACK
        missing = popcount(shield & ~our_pawns)
        score -= missing * 500
        
        backrank = BB_BACKRANK_WHITE if us else BB_BACKRANK_BLACK
        our_pieces = 0
        for pt in range(1, 7):
            our_pieces |= board.pieces_mask(pt, us)
        our_non_king = our_pieces & ~board.pieces_mask(chess.KING, us)
        score -= popcount(our_non_king & backrank) * 100
        
        score -= popcount(our_non_king & BB_CENTER) * 300
        score += popcount(our_non_king & BB_RIM) * 200
        
        bishops = board.pieces_mask(chess.BISHOP, us)
        if popcount(bishops) >= 2:
            score -= 400
        
        if board.is_check():
            score -= 800
        
        legal_count = 0
        for _ in board.legal_moves:
            legal_count += 1
        if legal_count <= 1:
            score -= 1500
        elif legal_count <= 3:
            score -= 800
        elif legal_count <= 5:
            score -= 300
        
        our_defenders = 0
        bb = our_non_king
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            att = board.attackers_mask(us, sq)
            if att and not (att & square_bb(sq)):
                our_defenders += popcount(att)
        score -= our_defenders * 150
        
        return float(score)
