"""
Bitboard helpers for the worst-move engine.
Uses python-chess bitboard API: BB_*, pieces_mask, attacks_mask, attackers_mask, occupied.
"""
import chess
from typing import Optional, Tuple

# Popcount – compatible with older Python versions
def popcount(bb: int) -> int:
    return bin(bb).count("1") if bb else 0

# Center squares d4,d5,e4,e5
BB_CENTER = (
    chess.BB_D4 | chess.BB_D5 | chess.BB_E4 | chess.BB_E5
)

# King shield: pawns in front of king (e2,d2,f2 for white; e7,d7,f7 for black)
BB_KING_SHIELD_WHITE = chess.BB_E2 | chess.BB_D2 | chess.BB_F2
BB_KING_SHIELD_BLACK = chess.BB_E7 | chess.BB_D7 | chess.BB_F7

# Back ranks
BB_BACKRANK_WHITE = chess.BB_RANK_1
BB_BACKRANK_BLACK = chess.BB_RANK_8

# Knight/bishop home squares (for "don't develop" penalty)
BB_KNIGHT_HOME_WHITE = chess.BB_B1 | chess.BB_G1
BB_KNIGHT_HOME_BLACK = chess.BB_B8 | chess.BB_G8
BB_BISHOP_HOME_WHITE = chess.BB_C1 | chess.BB_F1
BB_BISHOP_HOME_BLACK = chess.BB_C8 | chess.BB_F8

# King in center (files c–f, ranks 1–2 for white, 7–8 for black)
BB_KING_ZONE_WHITE = chess.BB_RANK_1 | chess.BB_RANK_2
BB_KING_ZONE_BLACK = chess.BB_RANK_7 | chess.BB_RANK_8
BB_CENTER_FILES = chess.BB_FILE_C | chess.BB_FILE_D | chess.BB_FILE_E | chess.BB_FILE_F


def our_pieces_bb(board: chess.Board, color: chess.Color) -> int:
    """Bitboard of all pieces of color."""
    bb = 0
    for pt in chess.PIECE_TYPES:
        bb |= board.pieces_mask(pt, color)
    return bb


def their_attacks_bb(board: chess.Board, color: chess.Color) -> int:
    """Bitboard of all squares attacked by the given color."""
    attacks = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == color:
            attacks |= board.attacks_mask(sq)
    return attacks


def our_mobility_bb(board: chess.Board, color: chess.Color) -> int:
    """Bitboard of squares attacked by color (for mobility count)."""
    return their_attacks_bb(board, color)


def hanging_bb(board: chess.Board, us: chess.Color) -> int:
    """Bitboard of our pieces that are attacked and not defended."""
    them = not us
    our_bb = our_pieces_bb(board, us)
    hanging = 0
    for sq in chess.SQUARES:
        if not (our_bb & (1 << sq)):
            continue
        if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
            hanging |= 1 << sq
    return hanging


def attacked_but_undefended_bb(board: chess.Board, us: chess.Color, target_bb: int) -> int:
    """Squares in target_bb that are attacked by them and not defended by us."""
    them = not us
    out = 0
    for sq in chess.SQUARES:
        if not (target_bb & (1 << sq)):
            continue
        if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
            out |= 1 << sq
        elif board.attackers_mask(them, sq) and popcount(board.attackers_mask(them, sq)) > popcount(board.attackers_mask(us, sq)):
            out |= 1 << sq
    return out


def pawns_on_file_bb(board: chess.Board, us: chess.Color, file_index: int) -> int:
    """Bitboard of our pawns on the given file."""
    return board.pieces_mask(chess.PAWN, us) & chess.BB_FILES[file_index]


def doubled_pawn_count_bb(pawns_bb: int) -> int:
    """Number of doubled pawn groups (popcount of file masks that have pawns)."""
    n = 0
    for f in range(8):
        if pawns_bb & chess.BB_FILES[f]:
            n += 1
    return n


def isolated_files_bb(board: chess.Board, us: chess.Color) -> int:
    """Bitboard of files that have our pawns but no neighbor-file pawns."""
    our_pawns = board.pieces_mask(chess.PAWN, us)
    isolated = 0
    for f in range(8):
        file_bb = chess.BB_FILES[f] & our_pawns
        if not file_bb:
            continue
        left = chess.BB_FILES[f - 1] & our_pawns if f > 0 else 0
        right = chess.BB_FILES[f + 1] & our_pawns if f < 7 else 0
        if not left and not right:
            isolated |= file_bb
    return isolated


def square_bb(sq: chess.Square) -> int:
    return 1 << sq


def king_in_center_bb(board: chess.Board, us: chess.Color) -> bool:
    """True if our king is still in the center (not castled)."""
    ksq = board.king(us)
    if ksq is None:
        return False
    r = chess.square_rank(ksq)
    f = chess.square_file(ksq)
    if us == chess.WHITE:
        return 2 <= f <= 5 and r <= 1
    return 2 <= f <= 5 and r >= 6


# Piece values in centipawns for SEE
_SEE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def _see_piece_value(piece: Optional[chess.Piece]) -> int:
    return _SEE_VALUES.get(piece.piece_type, 0) if piece else 0


def see_capture(board: chess.Board, move: chess.Move) -> int:
    """
    Static Exchange Evaluation for a capture move.
    Returns net centipawn gain for the side making the move (negative = we lose material).
    """
    if not board.is_capture(move):
        return 0
    to_sq = move.to_square
    from_sq = move.from_square
    victim = board.piece_at(to_sq)
    piece = board.piece_at(from_sq)
    if not victim or not piece:
        return 0
    v_victim = _see_piece_value(victim)
    v_piece = _see_piece_value(piece)
    board.push(move)
    recapture_gain = _see_square(board, to_sq, not piece.color)
    board.pop()
    return v_victim - v_piece - recapture_gain


def _see_square(board: chess.Board, sq: chess.Square, color: chess.Color) -> int:
    """Max gain for color if they capture on sq (used recursively for SEE)."""
    attackers = []
    sq_bb = 1 << sq
    for s in chess.SQUARES:
        p = board.piece_at(s)
        if p and p.color == color and (board.attacks_mask(s) & sq_bb):
            attackers.append((_see_piece_value(p), s))
    if not attackers:
        return 0
    attackers.sort(key=lambda x: x[0])
    value_smallest, from_sq = attackers[0]
    victim_val = _see_piece_value(board.piece_at(sq))
    board.push(chess.Move(from_sq, sq))
    recapture = _see_square(board, from_sq, not color)
    board.pop()
    return victim_val - value_smallest - recapture


def pinned_bb(board: chess.Board, color: chess.Color) -> int:
    """Bitboard of our pieces that are pinned to our king."""
    out = 0
    for sq in chess.SQUARES:
        if board.piece_at(sq) and board.piece_at(sq).color == color and board.is_pinned(color, sq):
            out |= 1 << sq
    return out


def _ranks_bb(start: int, end: int) -> int:
    """Bitboard of ranks start..end inclusive (0-indexed)."""
    bb = 0
    for i in range(start, min(end + 1, 8)):
        bb |= chess.BB_RANKS[i]
    return bb


def passed_pawns_bb(board: chess.Board, us: chess.Color) -> int:
    """Bitboard of our pawns that are passed (no enemy pawn can stop them)."""
    our_pawns = board.pieces_mask(chess.PAWN, us)
    their_pawns = board.pieces_mask(chess.PAWN, not us)
    result = 0
    for sq in chess.SQUARES:
        if not (our_pawns & (1 << sq)):
            continue
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        if us == chess.WHITE:
            ahead = chess.BB_FILES[f] & _ranks_bb(r + 1, 7)
            block = ahead
            if f > 0:
                block |= chess.BB_FILES[f - 1] & _ranks_bb(r + 1, 7)
            if f < 7:
                block |= chess.BB_FILES[f + 1] & _ranks_bb(r + 1, 7)
        else:
            ahead = chess.BB_FILES[f] & _ranks_bb(0, r - 1)
            block = ahead
            if f > 0:
                block |= chess.BB_FILES[f - 1] & _ranks_bb(0, r - 1)
            if f < 7:
                block |= chess.BB_FILES[f + 1] & _ranks_bb(0, r - 1)
        if not (their_pawns & block):
            result |= 1 << sq
    return result


def backward_pawns_bb(board: chess.Board, us: chess.Color) -> int:
    """Bitboard of our pawns that are backward (cannot be supported by a pawn behind, enemy pawn ahead)."""
    our_pawns = board.pieces_mask(chess.PAWN, us)
    their_pawns = board.pieces_mask(chess.PAWN, not us)
    result = 0
    for sq in chess.SQUARES:
        if not (our_pawns & (1 << sq)):
            continue
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        if us == chess.WHITE:
            if r >= 6:
                continue
            ahead = chess.BB_FILES[f] & _ranks_bb(r + 1, 7)
            behind = chess.BB_FILES[f] & _ranks_bb(0, r - 1)
            left = chess.BB_FILES[f - 1] & _ranks_bb(0, r - 1) if f > 0 else 0
            right = chess.BB_FILES[f + 1] & _ranks_bb(0, r - 1) if f < 7 else 0
        else:
            if r <= 1:
                continue
            ahead = chess.BB_FILES[f] & _ranks_bb(0, r - 1)
            behind = chess.BB_FILES[f] & _ranks_bb(r + 1, 7)
            left = chess.BB_FILES[f - 1] & _ranks_bb(r + 1, 7) if f > 0 else 0
            right = chess.BB_FILES[f + 1] & _ranks_bb(r + 1, 7) if f < 7 else 0
        if not (their_pawns & ahead):
            continue
        support = our_pawns & (behind | left | right)
        if not support:
            result |= 1 << sq
    return result


BB_RANK7_WHITE = chess.BB_RANK_7
BB_RANK7_BLACK = chess.BB_RANK_2


def rooks_on_seventh_bb(board: chess.Board, us: chess.Color) -> int:
    """Bitboard of our rooks on the 7th rank (2nd for black)."""
    rank7 = BB_RANK7_WHITE if us == chess.WHITE else BB_RANK7_BLACK
    return board.pieces_mask(chess.ROOK, us) & rank7
