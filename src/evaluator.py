"""
Position evaluation for the worst-move engine.
Optimized with zobrist hash caching and minimal computation.
"""
import chess
from typing import Dict
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    isolated_files_bb,
    pinned_bb,
    passed_pawns_bb,
    backward_pawns_bb,
    rooks_on_seventh_bb,
    king_escape_squares,
    find_pieces_defending_others,
    allows_mate_in_1,
    lsb,
    BB_CENTER,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
    BB_BACKRANK_WHITE,
    BB_BACKRANK_BLACK,
    BB_KNIGHT_HOME_WHITE,
    BB_KNIGHT_HOME_BLACK,
    BB_BISHOP_HOME_WHITE,
    BB_BISHOP_HOME_BLACK,
    BB_RIM,
    king_in_center_bb,
    square_bb,
    PIECE_VALUES,
)


class Evaluator:
    __slots__ = ['_cache', 'max_cache_size', 'position_history']
    
    def __init__(self) -> None:
        self._cache: Dict[int, float] = {}
        self.max_cache_size = 100_000
        self.position_history: Dict[str, int] = {}

    def evaluate_position(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -50_000 if board.turn else 50_000
        if board.is_stalemate():
            return 25_000
        if board.can_claim_threefold_repetition() or board.is_repetition():
            return 20_000 if board.turn else -20_000
        if board.can_claim_draw():
            return 15_000

        key = hash(board.board_fen() + str(board.turn) + str(board.castling_rights))
        if key in self._cache:
            return self._cache[key]

        us = board.turn
        them = not us
        
        score = self._fast_eval(board, us, them)
        
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score

    def _fast_eval(self, board: chess.Board, us: chess.Color, them: chess.Color) -> float:
        score = 0.0
        
        our_pieces = our_pieces_bb(board, us)
        their_pieces = our_pieces_bb(board, them)
        our_attacks = their_attacks_bb(board, us)
        their_attacks = their_attacks_bb(board, them)
        
        score += self._material(board, us)
        score += (popcount(our_attacks) - popcount(their_attacks)) * 4.0
        
        hanging = hanging_bb(board, us)
        if hanging:
            score -= self._hanging_score(board, us, hanging) * 45
        
        ksq = board.king(us)
        if ksq is not None:
            attackers = popcount(board.attackers_mask(them, ksq))
            score -= attackers * 1200
            
            escape_bad = king_escape_squares(board, us)
            score -= escape_bad * 200
        
        our_pawns = board.pieces_mask(chess.PAWN, us)
        score -= popcount(isolated_files_bb(board, us)) * 240
        
        for f in range(8):
            if popcount(our_pawns & chess.BB_FILES[f]) >= 2:
                score -= 320
        
        our_non_king = our_pieces & ~board.pieces_mask(chess.KING, us)
        backrank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        score -= popcount(our_non_king & backrank) * 80
        
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        missing_shield = popcount(shield & ~our_pawns)
        score -= missing_shield * 400
        
        score -= popcount(our_non_king & BB_RIM) * 150 * (-1)
        score += popcount(their_pieces & BB_RIM & ~board.pieces_mask(chess.KING, them)) * 100
        
        score -= popcount(our_non_king & BB_CENTER) * 250
        
        pinned = pinned_bb(board, us)
        if pinned:
            bb = pinned
            while bb:
                sq = lsb(bb)
                bb &= bb - 1
                p = board.piece_at(sq)
                if p:
                    score -= 200 + PIECE_VALUES.get(p.piece_type, 0)
        
        passed = passed_pawns_bb(board, us)
        if passed:
            score -= popcount(passed) * 300
        
        backward = backward_pawns_bb(board, us)
        if backward:
            score -= popcount(backward) * 150 * (-1)
        
        bishops = board.pieces_mask(chess.BISHOP, us)
        if popcount(bishops) >= 2:
            score -= 300
        
        rooks7 = rooks_on_seventh_bb(board, us)
        if rooks7:
            score -= popcount(rooks7) * 200
        
        if board.is_check():
            score -= 600
        
        legal_count = len(list(board.legal_moves))
        if legal_count <= 1:
            score -= 1200
        elif legal_count <= 3:
            score -= 600
        elif legal_count <= 5:
            score -= 250
        
        defenders = find_pieces_defending_others(board, us)
        for sq, count in defenders.items():
            p = board.piece_at(sq)
            if p:
                score -= count * 100 + PIECE_VALUES.get(p.piece_type, 0) // 2
        
        return score

    def _material(self, board: chess.Board, us: chess.Color) -> float:
        s = 0
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            v = PIECE_VALUES[pt]
            s += popcount(board.pieces_mask(pt, chess.WHITE)) * v
            s -= popcount(board.pieces_mask(pt, chess.BLACK)) * v
        return float(s if us == chess.WHITE else -s)

    def _hanging_score(self, board: chess.Board, us: chess.Color, hanging: int) -> float:
        penalty = popcount(hanging) * 500
        bb = hanging
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if p:
                pv = PIECE_VALUES.get(p.piece_type, 0)
                penalty += pv * 15
                if p.piece_type == chess.QUEEN:
                    penalty += 3000
                elif p.piece_type == chess.ROOK:
                    penalty += 1500
        return float(penalty)

    def clear_history(self) -> None:
        self.position_history.clear()
