"""
Move ordering for worst-move search (bitboard-based).
Try the worst moves first (low score). Heavily reward giving away material,
allowing mate, moving into attacks, opening the king.
"""
import chess
from typing import List, Optional
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    square_bb,
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
    moving_piece = board.piece_at(from_sq)

    # Allow checkmate: worst → try first
    board.push(move)
    if board.is_checkmate():
        score -= 12_000
    # Hanging pieces after our move (bitboard)
    hanging = hanging_bb(board, us)
    for sq in chess.SQUARES:
        if not (hanging & square_bb(sq)):
            continue
        p = board.piece_at(sq)
        if p:
            score -= 600 + get_piece_value(p) * 35
    board.pop()

    # Captures: losing material very bad; winning material good (try last)
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = get_piece_value(moving_piece)
            cv = get_piece_value(captured)
            if cv > mv:
                score -= 1500
            elif cv == mv:
                score -= 200
            else:
                score += 400

    # After our move: sit on attacked square? (bitboard)
    board.push(move)
    their_attacks = their_attacks_bb(board, them)
    our_attacks = their_attacks_bb(board, us)
    if (to_bb & their_attacks) and moving_piece:
        def_them = popcount(board.attackers_mask(them, to_sq))
        def_us = popcount(board.attackers_mask(us, to_sq))
        if def_us == 0 or def_them > def_us:
            score -= 700 + get_piece_value(moving_piece) * 40
    # Blocking our own piece (to_sq in our attack set from another piece)
    our_bb = our_pieces_bb(board, us)
    for sq in chess.SQUARES:
        if sq == to_sq:
            continue
        if not (our_bb & square_bb(sq)):
            continue
        p = board.piece_at(sq)
        if p and p.piece_type != chess.PAWN:
            if board.attacks_mask(sq) & to_bb:
                score -= 120
    board.pop()

    # Opening king: move pawn in king shield (bitboard)
    if moving_piece and moving_piece.piece_type == chess.PAWN:
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        if square_bb(from_sq) & shield:
            score -= 350

    # Castling: good → try last
    if board.is_castling(move):
        score += 900

    # Developing N/B from back rank: good → try last
    back_rank_bb = chess.BB_RANK_1 if us == chess.WHITE else chess.BB_RANK_8
    if moving_piece and (square_bb(from_sq) & back_rank_bb):
        if moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            score += 250

    # Moving to corner/edge (passive): prefer (try first) → lower score
    if moving_piece and to_sq in (chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7):
        score -= 100
    if moving_piece and chess.square_file(to_sq) in (0, 7):
        score -= 40

    return score


def order_moves(
    board: chess.Board,
    history_table: Optional[dict] = None,
) -> List[chess.Move]:
    scored = [(score_move(board, m), m) for m in board.legal_moves]
    if history_table and board.fen() in history_table:
        ht = history_table[board.fen()]
        scored = [(s + ht.get(m, 0), m) for s, m in scored]
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored]
