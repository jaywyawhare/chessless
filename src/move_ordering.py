"""
Move ordering for worst-move search: try the worst moves first (low score first).
Maximally rewards giving away material, allowing mate, moving into attacks,
opening the king, and avoiding development/castling.
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
    Strongly prefer: allowing mate, losing material, moving into attack,
    opening king, blocking pieces. Strongly avoid trying: good captures, castling.
    """
    score = 0.0
    us = board.turn
    them = not us
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)

    # Allow checkmate: worst possible → try first
    board.push(move)
    if board.is_checkmate():
        score -= 8000
    # After our move, do we leave a piece hanging?
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p or p.color != us:
            continue
        if board.attackers(them, sq) and not board.attackers(us, sq):
            score -= 400 + get_piece_value(p) * 25
    board.pop()

    # Captures: losing material is very bad (try first); winning material is good (try last)
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if moving_piece and captured:
            mv = get_piece_value(moving_piece)
            cv = get_piece_value(captured)
            if cv > mv:
                score -= 1200
            elif cv == mv:
                score -= 150
            else:
                score += 300

    # After our move: sit on attacked square or block our pieces?
    board.push(move)
    if board.attackers(them, to_sq) and moving_piece:
        if not board.attackers(us, to_sq) or len(board.attackers(them, to_sq)) > len(board.attackers(us, to_sq)):
            score -= 500 + get_piece_value(moving_piece) * 30
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p or p.color != us or sq == to_sq:
            continue
        if p.piece_type != chess.PAWN and to_sq in board.attacks(sq):
            score -= 80
    board.pop()

    # Opening our king: move pawn in front of castled king or move king's shield
    if moving_piece and moving_piece.piece_type == chess.PAWN:
        ksq = board.king(us)
        if ksq is not None:
            kfile = chess.square_file(ksq)
            krank = chess.square_rank(ksq)
            from_file, from_rank = chess.square_file(from_sq), chess.square_rank(from_sq)
            if abs(from_file - kfile) <= 1 and (from_rank == krank or from_rank == krank + (1 if us == chess.WHITE else -1)):
                score -= 200

    # Castling: good move → try last
    if board.is_castling(move):
        score += 600

    # Developing knight/bishop from back rank: good → try last
    back_rank = 0 if us == chess.WHITE else 7
    if moving_piece and chess.square_rank(from_sq) == back_rank:
        if moving_piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            score += 150

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
