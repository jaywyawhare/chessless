"""
Ultra-fast move ordering - minimal push/pop, static scoring.
"""
import chess
from typing import List, Optional, Tuple
from src.fast_tables import file_of, rank_of, FAST_PIECE_VALUES_LIGHT, BB_KING_SHIELD_WHITE, BB_KING_SHIELD_BLACK, RIM_SQUARES, KNIGHT_RIM_SQUARES, square_bb


SCORE_PAWN_SHIELD = -4000
SCORE_KING_CENTER_FILE = -2000
SCORE_KING_MOVE = -4000
SCORE_QUEEN_RIM = -2500
SCORE_KNIGHT_RIM = -2200
SCORE_BISHOP_RIM = -2000
SCORE_DEVELOP = 4000
SCORE_CASTLE = 10000
SCORE_RIM_SQ = -1500
SCORE_RIM_FILE = -500
SCORE_BAD_CAPTURE = -25000
SCORE_EQUAL_CAPTURE = -8000
SCORE_CHECKMATE = -300000
SCORE_CHECK = -20000
SCORE_DRAW = 80000
SCORE_HANGING_QUEEN = -40000
SCORE_HANGING_ROOK = -20000


def ultra_score_move(board: chess.Board, move: chess.Move) -> float:
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)
    
    if not moving_piece:
        return 0.0
    
    us = board.turn
    them = not us
    pt = moving_piece.piece_type
    pv = FAST_PIECE_VALUES_LIGHT[pt]
    to_file = file_of(to_sq)
    to_rank = rank_of(to_sq)
    from_bb = square_bb(from_sq)
    to_bb = square_bb(to_sq)
    
    score = 0.0
    
    if pt == chess.PAWN:
        shield = BB_KING_SHIELD_WHITE if us else BB_KING_SHIELD_BLACK
        if from_bb & shield:
            score += SCORE_PAWN_SHIELD
        if to_file in (0, 7):
            score -= 1000
    
    elif pt == chess.KING:
        if not board.is_castling(move):
            score += SCORE_KING_MOVE
        if to_file in (2, 3, 4, 5):
            score += SCORE_KING_CENTER_FILE
    
    elif pt == chess.QUEEN:
        if to_file in (0, 7) or to_rank in (0, 7):
            score += SCORE_QUEEN_RIM
        if to_sq in RIM_SQUARES:
            score -= 500
    
    elif pt == chess.KNIGHT:
        if to_file in (0, 7):
            score += SCORE_KNIGHT_RIM
        if to_sq in KNIGHT_RIM_SQUARES:
            score -= 400
    
    elif pt == chess.BISHOP:
        if to_file in (0, 7):
            score += SCORE_BISHOP_RIM
    
    backrank = chess.BB_RANK_1 if us else chess.BB_RANK_8
    if from_bb & backrank and pt in (chess.KNIGHT, chess.BISHOP):
        score -= SCORE_DEVELOP
    
    if board.is_castling(move):
        score -= SCORE_CASTLE
    
    if to_sq in RIM_SQUARES:
        score -= SCORE_RIM_SQ
    elif to_file in (0, 7):
        score -= SCORE_RIM_FILE
    
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if captured:
            cv = FAST_PIECE_VALUES_LIGHT[captured.piece_type]
            if cv > pv:
                score += SCORE_BAD_CAPTURE
            elif cv == pv:
                score += SCORE_EQUAL_CAPTURE
    
    board.push(move)
    
    if board.is_checkmate():
        board.pop()
        return float(SCORE_CHECKMATE)
    
    if board.is_check():
        score += SCORE_CHECK
    
    if board.is_stalemate() or board.can_claim_draw():
        score -= SCORE_DRAW
    
    our_bb = board.occupied_co[us]
    hanging_queen = False
    hanging_rook = False
    
    for sq in range(64):
        if our_bb & square_bb(sq):
            if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
                p = board.piece_at(sq)
                if p:
                    if p.piece_type == chess.QUEEN:
                        hanging_queen = True
                    elif p.piece_type == chess.ROOK:
                        hanging_rook = True
    
    if hanging_queen:
        score += SCORE_HANGING_QUEEN
    if hanging_rook:
        score += SCORE_HANGING_ROOK
    
    board.pop()
    
    return score


def ultra_order_moves(board: chess.Board, killers: Optional[Tuple] = None) -> List[chess.Move]:
    moves = list(board.legal_moves)
    scored = [(ultra_score_move(board, m), m) for m in moves]
    
    if killers:
        k1, k2 = killers
        if k1:
            for i, (s, m) in enumerate(scored):
                if m == k1:
                    scored[i] = (s - 15000, m)
        if k2:
            for i, (s, m) in enumerate(scored):
                if m == k2:
                    scored[i] = (s - 15000, m)
    
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored]
