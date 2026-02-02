"""
Move ordering for worst-move search: try bad moves first (low score first).
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
    """Lower score = worse move (we want to try these first)."""
    score = 0.0
    if board.is_capture(move):
        moving = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)
        if moving and captured:
            mv = get_piece_value(moving)
            cv = get_piece_value(captured)
            score -= (cv - mv) * 10
    board.push(move)
    if board.is_checkmate():
        score -= 1000
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
