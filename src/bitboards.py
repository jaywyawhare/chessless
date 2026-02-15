"""
Bitboard helpers for the worst-move engine.
Optimized with bit_count and scan_reversed for fast iteration.
"""
import chess
from typing import Optional

BB_CENTER = chess.BB_D4 | chess.BB_D5 | chess.BB_E4 | chess.BB_E5
BB_KING_SHIELD_WHITE = chess.BB_E2 | chess.BB_D2 | chess.BB_F2
BB_KING_SHIELD_BLACK = chess.BB_E7 | chess.BB_D7 | chess.BB_F7
BB_BACKRANK_WHITE = chess.BB_RANK_1
BB_BACKRANK_BLACK = chess.BB_RANK_8
BB_KNIGHT_HOME_WHITE = chess.BB_B1 | chess.BB_G1
BB_KNIGHT_HOME_BLACK = chess.BB_B8 | chess.BB_G8
BB_BISHOP_HOME_WHITE = chess.BB_C1 | chess.BB_F1
BB_BISHOP_HOME_BLACK = chess.BB_C8 | chess.BB_F8
BB_KING_ZONE_WHITE = chess.BB_RANK_1 | chess.BB_RANK_2
BB_KING_ZONE_BLACK = chess.BB_RANK_7 | chess.BB_RANK_8
BB_CENTER_FILES = chess.BB_FILE_C | chess.BB_FILE_D | chess.BB_FILE_E | chess.BB_FILE_F
BB_RANK7_WHITE = chess.BB_RANK_7
BB_RANK7_BLACK = chess.BB_RANK_2
BB_RIM = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

PIECE_VALUES_LIGHT = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def popcount(bb: int) -> int:
    return bb.bit_count() if bb else 0


def lsb(bb: int) -> int:
    return (bb & -bb).bit_length() - 1


def square_bb(sq: chess.Square) -> int:
    return 1 << sq


def our_pieces_bb(board: chess.Board, color: chess.Color) -> int:
    bb = 0
    for pt in chess.PIECE_TYPES:
        bb |= board.pieces_mask(pt, color)
    return bb


def their_attacks_bb(board: chess.Board, color: chess.Color) -> int:
    attacks = 0
    for pt in chess.PIECE_TYPES:
        bb = board.pieces_mask(pt, color)
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            attacks |= board.attacks_mask(sq)
    return attacks


def hanging_bb(board: chess.Board, us: chess.Color) -> int:
    them = not us
    our_bb = our_pieces_bb(board, us)
    result = 0
    bb = our_bb
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        att_them = board.attackers_mask(them, sq)
        if att_them:
            att_us = board.attackers_mask(us, sq)
            if not att_us:
                result |= (1 << sq)
            elif popcount(att_them) > popcount(att_us):
                result |= (1 << sq)
    return result


def king_in_center_bb(board: chess.Board, us: chess.Color) -> bool:
    ksq = board.king(us)
    if ksq is None:
        return False
    r = chess.square_rank(ksq)
    f = chess.square_file(ksq)
    if us == chess.WHITE:
        return 2 <= f <= 5 and r <= 1
    return 2 <= f <= 5 and r >= 6


def isolated_files_bb(board: chess.Board, us: chess.Color) -> int:
    our_pawns = board.pieces_mask(chess.PAWN, us)
    isolated = 0
    bb = our_pawns
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        f = chess.square_file(sq)
        left = chess.BB_FILES[f - 1] & our_pawns if f > 0 else 0
        right = chess.BB_FILES[f + 1] & our_pawns if f < 7 else 0
        if not left and not right:
            isolated |= (1 << sq)
    return isolated


def _front_span(us: chess.Color, sq: int) -> int:
    f = chess.square_file(sq)
    r = chess.square_rank(sq)
    if us == chess.WHITE:
        return (chess.BB_FILES[f] | (chess.BB_FILES[f - 1] if f > 0 else 0) | (chess.BB_FILES[f + 1] if f < 7 else 0)) & _ranks_bb(r + 1, 7)
    return (chess.BB_FILES[f] | (chess.BB_FILES[f - 1] if f > 0 else 0) | (chess.BB_FILES[f + 1] if f < 7 else 0)) & _ranks_bb(0, r - 1)


def _ranks_bb(start: int, end: int) -> int:
    bb = 0
    for i in range(max(0, start), min(8, end + 1)):
        bb |= chess.BB_RANKS[i]
    return bb


def passed_pawns_bb(board: chess.Board, us: chess.Color) -> int:
    our_pawns = board.pieces_mask(chess.PAWN, us)
    their_pawns = board.pieces_mask(chess.PAWN, not us)
    result = 0
    bb = our_pawns
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        front = _front_span(us, sq)
        if not (their_pawns & front):
            result |= (1 << sq)
    return result


def backward_pawns_bb(board: chess.Board, us: chess.Color) -> int:
    our_pawns = board.pieces_mask(chess.PAWN, us)
    their_pawns = board.pieces_mask(chess.PAWN, not us)
    result = 0
    bb = our_pawns
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        if us == chess.WHITE:
            if r >= 6:
                continue
            behind = _ranks_bb(0, r - 1)
            ahead_bb = _ranks_bb(r + 1, 7)
        else:
            if r <= 1:
                continue
            behind = _ranks_bb(r + 1, 7)
            ahead_bb = _ranks_bb(0, r - 1)
        left_behind = chess.BB_FILES[f - 1] & behind if f > 0 else 0
        right_behind = chess.BB_FILES[f + 1] & behind if f < 7 else 0
        support = our_pawns & (left_behind | right_behind | (chess.BB_FILES[f] & behind))
        ahead = chess.BB_FILES[f] & ahead_bb
        if (their_pawns & ahead) and not support:
            result |= (1 << sq)
    return result


def rooks_on_seventh_bb(board: chess.Board, us: chess.Color) -> int:
    rank7 = BB_RANK7_WHITE if us == chess.WHITE else BB_RANK7_BLACK
    return board.pieces_mask(chess.ROOK, us) & rank7


def pinned_bb(board: chess.Board, color: chess.Color) -> int:
    result = 0
    bb = our_pieces_bb(board, color)
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        if board.is_pinned(color, sq):
            result |= (1 << sq)
    return result


def see_capture_fast(board: chess.Board, move: chess.Move) -> int:
    if not board.is_capture(move):
        return 0
    to_sq = move.to_square
    from_sq = move.from_square
    victim = board.piece_at(to_sq)
    attacker = board.piece_at(from_sq)
    if not victim or not attacker:
        return 0
    gain = PIECE_VALUES.get(victim.piece_type, 0)
    loss = PIECE_VALUES.get(attacker.piece_type, 0)
    them = not attacker.color
    recapture_value = _see_recapture(board, to_sq, them, loss)
    return gain - recapture_value


def _see_recapture(board: chess.Board, sq: chess.Square, color: chess.Color, current_value: int) -> int:
    attackers = board.attackers_mask(color, sq)
    if not attackers:
        return 0
    min_attacker_val = 10000
    min_sq = None
    bb = attackers
    while bb:
        s = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(s)
        if p:
            v = PIECE_VALUES.get(p.piece_type, 0)
            if v < min_attacker_val:
                min_attacker_val = v
                min_sq = s
    if min_sq is None:
        return 0
    return min(min_attacker_val, current_value)


def count_attackers(board: chess.Board, color: chess.Color, sq: int) -> int:
    return popcount(board.attackers_mask(color, sq))


def king_escape_squares(board: chess.Board, us: chess.Color) -> int:
    ksq = board.king(us)
    if ksq is None:
        return 8
    king_attacks = board.attacks_mask(ksq)
    their_attacks = their_attacks_bb(board, not us)
    occupied = board.occupied
    bad = king_attacks & (their_attacks | occupied)
    return popcount(bad)


def defenders_of(board: chess.Board, us: chess.Color, sq: int) -> int:
    return popcount(board.attackers_mask(us, sq))


def find_pieces_defending_others(board: chess.Board, us: chess.Color) -> dict:
    result = {}
    our_bb = our_pieces_bb(board, us)
    bb = our_bb
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(sq)
        if p and p.piece_type != chess.KING:
            attacks = board.attacks_mask(sq)
            defended = attacks & our_bb
            if defended:
                result[sq] = popcount(defended)
    return result


def allows_mate_in_1(board: chess.Board) -> bool:
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return True
        board.pop()
    return False
