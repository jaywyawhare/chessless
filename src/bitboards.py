"""
Bitboard helpers for the worst-move engine.
Uses python-chess bitboard API: BB_*, pieces_mask, attacks_mask, attackers_mask, occupied.
"""
import chess
from typing import Tuple

# Popcount (Python 3.10+)
def popcount(bb: int) -> int:
    return bb.bit_count() if bb else 0

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
