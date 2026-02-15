"""
Move ordering for worst-move search.
Optimized with fast scoring - prioritizes worst moves.
"""
import chess
from typing import List, Optional, Tuple
from src.bitboards import (
    popcount,
    our_pieces_bb,
    hanging_bb,
    square_bb,
    see_capture_fast,
    lsb,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
    PIECE_VALUES_LIGHT,
)

RIM_SQUARES = {chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7}
KNIGHT_RIM = {chess.A3, chess.H3, chess.A6, chess.H6}
CENTER_FILES = {2, 3, 4, 5}
RIM_FILES = {0, 7}


def score_move_fast(board: chess.Board, move: chess.Move) -> float:
    from_sq = move.from_square
    to_sq = move.to_square
    to_bb = square_bb(to_sq)
    moving_piece = board.piece_at(from_sq)
    us = board.turn
    
    board.push(move)
    
    if board.is_checkmate():
        board.pop()
        return -300_000.0
    
    score = 0.0
    
    if board.is_stalemate():
        score += 150_000
    elif board.can_claim_draw():
        score += 100_000
    
    if board.is_check():
        score -= 20_000
    
    hanging = hanging_bb(board, us)
    if hanging:
        bb = hanging
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if p:
                pv = PIECE_VALUES_LIGHT.get(p.piece_type, 0)
                score -= 5000 + pv * 500
                if p.piece_type == chess.QUEEN:
                    score -= 40_000
                elif p.piece_type == chess.ROOK:
                    score -= 20_000
    
    board.pop()
    
    if moving_piece:
        pt = moving_piece.piece_type
        
        our_pieces = our_pieces_bb(board, us)
        bb = our_pieces
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if p and p.piece_type != chess.KING and sq == from_sq:
                defenders = board.attackers_mask(us, sq)
                if defenders and not (defenders & square_bb(sq)):
                    score -= 10_000 + PIECE_VALUES_LIGHT.get(pt, 0) * 400
        
        if pt == chess.PAWN:
            shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
            if square_bb(from_sq) & shield:
                score -= 3000
        
        elif pt == chess.KING:
            if not board.is_castling(move):
                score -= 3000
            if chess.square_file(to_sq) in CENTER_FILES:
                score -= 1500
        
        elif pt == chess.QUEEN:
            if chess.square_file(to_sq) in RIM_FILES or chess.square_rank(to_sq) in (0, 7):
                score -= 2000
            if to_sq in RIM_SQUARES:
                score -= 1500
        
        elif pt == chess.KNIGHT:
            if chess.square_file(to_sq) in RIM_FILES:
                score -= 1800
            if to_sq in KNIGHT_RIM:
                score -= 1500
        
        elif pt == chess.BISHOP:
            if chess.square_file(to_sq) in RIM_FILES:
                score -= 1500
    
    if board.is_castling(move):
        score += 8000
    
    back_rank_bb = chess.BB_RANK_1 if us == chess.WHITE else chess.BB_RANK_8
    if moving_piece and (square_bb(from_sq) & back_rank_bb):
        if moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            score += 3000
    
    if moving_piece:
        if to_sq in RIM_SQUARES:
            score -= 1000
        if chess.square_file(to_sq) in RIM_FILES:
            score -= 400
    
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = PIECE_VALUES_LIGHT.get(moving_piece.piece_type, 0)
            cv = PIECE_VALUES_LIGHT.get(captured.piece_type, 0)
            if cv > mv:
                score -= 20_000
            elif cv == mv:
                score -= 5000
    
    see_val = see_capture_fast(board, move)
    score += see_val * 0.1
    
    return score


def order_moves_fast(
    board: chess.Board,
    history_table: Optional[dict] = None,
    killer_moves: Optional[Tuple[Optional[chess.Move], Optional[chess.Move]]] = None,
) -> List[chess.Move]:
    moves = list(board.legal_moves)
    scored = [(score_move_fast(board, m), m) for m in moves]
    
    if killer_moves:
        k1, k2 = killer_moves
        if k1 or k2:
            for i, (s, m) in enumerate(scored):
                if m == k1 or m == k2:
                    scored[i] = (s - 10000, m)
    
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored]
