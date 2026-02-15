"""
Move ordering for worst-move search (bitboard-based).
Try the worst moves first (low score). Uses SEE, killer moves, and heuristics
for giving away material, allowing mate, moving into attacks, opening the king.
"""
import chess
from typing import List, Optional, Tuple
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    square_bb,
    see_capture,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
)


PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def get_piece_value(piece: chess.Piece) -> int:
    return PIECE_VALUES.get(piece.piece_type, 0)


def score_move(board: chess.Board, move: chess.Move) -> float:
    """
    Lower score = worse move (try first).
    Bitboard-based: use attackers_mask, hanging_bb, their_attacks_bb.
    """
    score = 0.0
    us = board.turn
    them = not us
    from_sq = move.from_square
    to_sq = move.to_square
    to_bb = square_bb(to_sq)
    from_bb = square_bb(from_sq)
    moving_piece = board.piece_at(from_sq)

    board.push(move)
    if board.is_checkmate():
        score -= 200_000
    if board.is_stalemate():
        score += 150_000
    if board.can_claim_threefold_repetition() or board.is_repetition():
        score += 120_000
    if board.is_check():
        score -= 15_000
    if board.can_claim_draw():
        score += 100_000
    # Hanging pieces after our move (bitboard)
    hanging = hanging_bb(board, us)
    for sq in chess.SQUARES:
        if not (hanging & square_bb(sq)):
            continue
        p = board.piece_at(sq)
        if p:
            bonus = get_piece_value(p) * 400
            if p.piece_type == chess.QUEEN:
                bonus += 25_000
            elif p.piece_type == chess.ROOK:
                bonus += 12_000
            score -= bonus
    # Check if we allow mate in 1
    if not board.is_checkmate():
        for opp_move in board.legal_moves:
            board.push(opp_move)
            if board.is_checkmate():
                score -= 180_000
                board.pop()
                break
            board.pop()
    board.pop()
    our_defended = set()
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == us and p.piece_type != chess.KING:
            defenders = board.attackers_mask(us, sq)
            if defenders and not (defenders & square_bb(sq)):
                our_defended.add(sq)
    if moving_piece and from_sq in our_defended:
        score -= 8_000 + get_piece_value(moving_piece) * 300

    # SEE: prefer moves that lose material (negative SEE = try first)
    see_val = see_capture(board, move)
    score += see_val * 7.0

    # Captures: losing material very bad; winning material good (try last)
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = get_piece_value(moving_piece)
            cv = get_piece_value(captured)
            if cv > mv:
                score -= 14_000
            elif cv == mv:
                score -= 2000
            else:
                score += 3000

    # After our move: sit on attacked square? (bitboard)
    board.push(move)
    their_attacks = their_attacks_bb(board, them)
    if (to_bb & their_attacks) and moving_piece:
        def_them = popcount(board.attackers_mask(them, to_sq))
        def_us = popcount(board.attackers_mask(us, to_sq))
        if def_us == 0 or def_them > def_us:
            score -= 5500 + get_piece_value(moving_piece) * 220
    # Blocking our own piece
    our_bb = our_pieces_bb(board, us)
    for sq in chess.SQUARES:
        if sq == to_sq:
            continue
        if not (our_bb & square_bb(sq)):
            continue
        p = board.piece_at(sq)
        if p and p.piece_type != chess.PAWN:
            if board.attacks_mask(sq) & to_bb:
                score -= 1100
    board.pop()

    # Opening king: move pawn in king shield (bitboard)
    if moving_piece and moving_piece.piece_type == chess.PAWN:
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        if square_bb(from_sq) & shield:
            score -= 2200

    # Moving the king early (before castling): bad → try first
    if moving_piece and moving_piece.piece_type == chess.KING:
        if not board.is_castling(move):
            score -= 2000
        if chess.square_file(to_sq) in (2, 3, 4, 5):
            score -= 900

    # Moving queen to rim/corner: prefer (try first)
    if moving_piece and moving_piece.piece_type == chess.QUEEN:
        if chess.square_file(to_sq) in (0, 7) or chess.square_rank(to_sq) in (0, 7):
            score -= 1200
        if to_sq in (chess.A1, chess.H1, chess.A8, chess.H8):
            score -= 800

    # Knight to rim (a3/h3/a6/h6): very bad → try first
    if moving_piece and moving_piece.piece_type == chess.KNIGHT:
        if chess.square_file(to_sq) in (0, 7):
            score -= 1100
        if to_sq in (chess.A3, chess.H3, chess.A6, chess.H6):
            score -= 900

    # Castling: good → try last
    if board.is_castling(move):
        score += 5500

    # Developing N/B from back rank: good → try last
    back_rank_bb = chess.BB_RANK_1 if us == chess.WHITE else chess.BB_RANK_8
    if moving_piece and (square_bb(from_sq) & back_rank_bb):
        if moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            score += 2200

    # Moving to corner/edge (passive): prefer (try first) → lower score
    if moving_piece and to_sq in (chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7):
        score -= 700
    if moving_piece and chess.square_file(to_sq) in (0, 7):
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
