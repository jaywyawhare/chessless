"""
Move ordering for worst-move search: try the worst moves first (low score first).
Heavily rewards giving away material, allowing mate, and moving into attacks.
"""
import chess
from typing import List, Optional


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
    Lower score = worse move (we try these first).
    We want to prefer: giving mate, losing material, moving into attack, blocking our pieces.
    """
    score = 0.0
    us = board.turn
    them = not us
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)

    # Allow checkmate: very bad → try first
    board.push(move)
    if board.is_checkmate():
        score -= 2000
    # After our move, do we leave a piece hanging?
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p or p.color != us:
            continue
        if board.attackers(them, sq) and not board.attackers(us, sq):
            score -= 150 + get_piece_value(p) * 10
    board.pop()

    # Captures: losing material is bad (try first)
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = get_piece_value(moving_piece)
            cv = get_piece_value(captured)
            if cv > mv:
                score -= 500
            elif cv == mv:
                score -= 50
            else:
                score += 100

    # After our move: do we sit on an attacked square or block our pieces?
    board.push(move)
    # Our piece on to_sq attacked and undefended?
    if board.attackers(them, to_sq) and moving_piece:
        if not board.attackers(us, to_sq) or len(board.attackers(them, to_sq)) > len(board.attackers(us, to_sq)):
            score -= 200 + get_piece_value(moving_piece) * 15
    # Blocking our own piece
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p or p.color != us or sq == to_sq:
            continue
        if p.piece_type != chess.PAWN and to_sq in board.attacks(sq):
            score -= 30
    board.pop()

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
