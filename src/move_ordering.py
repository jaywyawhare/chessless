"""
Move ordering for worst-move search (bitboard-based).
Optimized with fast bitboard operations.
"""
import chess
from typing import List, Optional, Tuple
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    square_bb,
    see_capture_fast,
    lsb,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
    PIECE_VALUES_LIGHT,
)


def score_move(board: chess.Board, move: chess.Move) -> float:
    score = 0.0
    us = board.turn
    them = not us
    from_sq = move.from_square
    to_sq = move.to_square
    to_bb = square_bb(to_sq)
    moving_piece = board.piece_at(from_sq)

    board.push(move)
    if board.is_checkmate():
        board.pop()
        return -200_000.0
    if board.is_stalemate():
        score += 150_000
    elif board.can_claim_threefold_repetition() or board.is_repetition():
        score += 120_000
    elif board.can_claim_draw():
        score += 100_000
    if board.is_check():
        score -= 15_000
    
    hanging = hanging_bb(board, us)
    bb = hanging
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(sq)
        if p:
            pv = PIECE_VALUES_LIGHT.get(p.piece_type, 0)
            bonus = pv * 400
            if p.piece_type == chess.QUEEN:
                bonus += 25_000
            elif p.piece_type == chess.ROOK:
                bonus += 12_000
            score -= bonus
    
    if not board.is_checkmate():
        for opp_move in board.legal_moves:
            board.push(opp_move)
            if board.is_checkmate():
                score -= 180_000
                board.pop()
                break
            board.pop()
    board.pop()

    our_pieces = our_pieces_bb(board, us)
    bb = our_pieces
    defender_sq = None
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(sq)
        if p and p.piece_type != chess.KING:
            defenders = board.attackers_mask(us, sq)
            if defenders and not (defenders & square_bb(sq)):
                if sq == from_sq:
                    defender_sq = sq
                    break
    
    if moving_piece and defender_sq == from_sq:
        pv = PIECE_VALUES_LIGHT.get(moving_piece.piece_type, 0)
        score -= 8_000 + pv * 300

    see_val = see_capture_fast(board, move)
    score += see_val * 0.07

    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = PIECE_VALUES_LIGHT.get(moving_piece.piece_type, 0)
            cv = PIECE_VALUES_LIGHT.get(captured.piece_type, 0)
            if cv > mv:
                score -= 14_000
            elif cv == mv:
                score -= 2000
            else:
                score += 3000

    board.push(move)
    their_attacks = their_attacks_bb(board, them)
    if (to_bb & their_attacks) and moving_piece:
        def_them = popcount(board.attackers_mask(them, to_sq))
        def_us = popcount(board.attackers_mask(us, to_sq))
        if def_us == 0 or def_them > def_us:
            pv = PIECE_VALUES_LIGHT.get(moving_piece.piece_type, 0)
            score -= 5500 + pv * 220
    
    our_bb = our_pieces_bb(board, us) & ~square_bb(to_sq)
    bb = our_bb
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(sq)
        if p and p.piece_type != chess.PAWN:
            if board.attacks_mask(sq) & to_bb:
                score -= 1100
                break
    board.pop()

    if moving_piece:
        pt = moving_piece.piece_type
        if pt == chess.PAWN:
            shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
            if square_bb(from_sq) & shield:
                score -= 2200
        elif pt == chess.KING:
            if not board.is_castling(move):
                score -= 2000
            if chess.square_file(to_sq) in (2, 3, 4, 5):
                score -= 900
        elif pt == chess.QUEEN:
            if chess.square_file(to_sq) in (0, 7) or chess.square_rank(to_sq) in (0, 7):
                score -= 1200
            if to_sq in (chess.A1, chess.H1, chess.A8, chess.H8):
                score -= 800
        elif pt == chess.KNIGHT:
            if chess.square_file(to_sq) in (0, 7):
                score -= 1100
            if to_sq in (chess.A3, chess.H3, chess.A6, chess.H6):
                score -= 900

    if board.is_castling(move):
        score += 5500

    back_rank_bb = chess.BB_RANK_1 if us == chess.WHITE else chess.BB_RANK_8
    if moving_piece and (square_bb(from_sq) & back_rank_bb):
        if moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            score += 2200

    if moving_piece:
        if to_sq in (chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7):
            score -= 700
        if chess.square_file(to_sq) in (0, 7):
            score -= 280

    return score


def order_moves(
    board: chess.Board,
    history_table: Optional[dict] = None,
    killer_moves: Optional[Tuple[Optional[chess.Move], Optional[chess.Move]]] = None,
) -> List[chess.Move]:
    scored = [(score_move(board, m), m) for m in board.legal_moves]
    if killer_moves:
        k1, k2 = killer_moves
        for i, (s, m) in enumerate(scored):
            if m == k1 or m == k2:
                scored[i] = (s - 7000, m)
    if history_table and board.fen() in history_table:
        ht = history_table[board.fen()]
        scored = [(s + ht.get(m, 0), m) for s, m in scored]
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored]
