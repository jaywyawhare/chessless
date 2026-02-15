"""
Precomputed attack tables and fast operations for chess.
Implements magic-bitboard-like lookups where possible in Python.
"""
import chess
from typing import Dict, List, Tuple

PIECE_VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}
PIECE_VALUES_LIGHT = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

KNIGHT_ATTACKS: List[int] = []
KING_ATTACKS: List[int] = []
PAWN_ATTACKS_WHITE: List[int] = []
PAWN_ATTACKS_BLACK: List[int] = []

RAYS_ROOK: List[Dict[int, int]] = []
RAYS_BISHOP: List[Dict[int, int]] = []

BB_RANKS = [chess.BB_RANK_1, chess.BB_RANK_2, chess.BB_RANK_3, chess.BB_RANK_4,
            chess.BB_RANK_5, chess.BB_RANK_6, chess.BB_RANK_7, chess.BB_RANK_8]
BB_FILES = [chess.BB_FILE_A, chess.BB_FILE_B, chess.BB_FILE_C, chess.BB_FILE_D,
            chess.BB_FILE_E, chess.BB_FILE_F, chess.BB_FILE_G, chess.BB_FILE_H]

BB_CENTER = chess.BB_D4 | chess.BB_D5 | chess.BB_E4 | chess.BB_E5
BB_RIM = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
BB_BACKRANK_WHITE = chess.BB_RANK_1
BB_BACKRANK_BLACK = chess.BB_RANK_8
BB_KING_SHIELD_WHITE = chess.BB_E2 | chess.BB_D2 | chess.BB_F2
BB_KING_SHIELD_BLACK = chess.BB_E7 | chess.BB_D7 | chess.BB_F7

KNIGHT_HOME_WHITE = chess.BB_B1 | chess.BB_G1
KNIGHT_HOME_BLACK = chess.BB_B8 | chess.BB_G8
BISHOP_HOME_WHITE = chess.BB_C1 | chess.BB_F1
BISHOP_HOME_BLACK = chess.BB_C8 | chess.BB_F8

RIM_SQUARES = {chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7}
KNIGHT_RIM_SQUARES = {chess.A3, chess.H3, chess.A6, chess.H6}


def _init_tables():
    global KNIGHT_ATTACKS, KING_ATTACKS, PAWN_ATTACKS_WHITE, PAWN_ATTACKS_BLACK
    
    for sq in range(64):
        KNIGHT_ATTACKS.append(chess.BB_KNIGHT_ATTACKS[sq])
        KING_ATTACKS.append(chess.BB_KING_ATTACKS[sq])
        
        f, r = chess.square_file(sq), chess.square_rank(sq)
        
        w_pawn_att = 0
        if r < 7:
            if f > 0:
                w_pawn_att |= 1 << (sq + 7)
            if f < 7:
                w_pawn_att |= 1 << (sq + 9)
        PAWN_ATTACKS_WHITE.append(w_pawn_att)
        
        b_pawn_att = 0
        if r > 0:
            if f > 0:
                b_pawn_att |= 1 << (sq - 9)
            if f < 7:
                b_pawn_att |= 1 << (sq - 7)
        PAWN_ATTACKS_BLACK.append(b_pawn_att)


def popcount(bb: int) -> int:
    return bb.bit_count() if bb else 0


def lsb(bb: int) -> int:
    return (bb & -bb).bit_length() - 1 if bb else -1


def square_bb(sq: int) -> int:
    return 1 << sq


def file_of(sq: int) -> int:
    return sq & 7


def rank_of(sq: int) -> int:
    return sq >> 3


_init_tables()


FAST_PIECE_VALUES = (0, 100, 320, 330, 500, 900, 20000)
FAST_PIECE_VALUES_LIGHT = (0, 1, 3, 3, 5, 9, 0)


def fast_material(board: chess.Board) -> int:
    score = 0
    for pt in range(1, 6):
        v = FAST_PIECE_VALUES[pt]
        score += popcount(board.pieces_mask(pt, chess.WHITE)) * v
        score -= popcount(board.pieces_mask(pt, chess.BLACK)) * v
    return score if board.turn == chess.WHITE else -score


def fast_hanging(board: chess.Board, us: bool) -> int:
    them = not us
    our_bb = 0
    for pt in range(1, 7):
        our_bb |= board.pieces_mask(pt, us)
    
    hanging = 0
    bb = our_bb
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
            hanging |= 1 << sq
    return popcount(hanging)


def fast_king_attackers(board: chess.Board, us: bool) -> int:
    ksq = board.king(us)
    if ksq is None:
        return 0
    return popcount(board.attackers_mask(not us, ksq))


def fast_king_escape(board: chess.Board, us: bool) -> int:
    ksq = board.king(us)
    if ksq is None:
        return 8
    king_att = KING_ATTACKS[ksq]
    occupied = board.occupied
    them_att = 0
    
    their_pieces = 0
    for pt in range(1, 7):
        their_pieces |= board.pieces_mask(pt, not us)
    
    bb = their_pieces
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        p = board.piece_at(sq)
        if p:
            if p.piece_type == chess.KNIGHT:
                them_att |= KNIGHT_ATTACKS[sq]
            elif p.piece_type == chess.KING:
                them_att |= KING_ATTACKS[sq]
            elif p.piece_type == chess.PAWN:
                them_att |= PAWN_ATTACKS_WHITE[sq] if p.color == chess.WHITE else PAWN_ATTACKS_BLACK[sq]
            else:
                them_att |= board.attacks_mask(sq)
    
    bad = king_att & (them_att | occupied)
    return popcount(bad)


def make_move_key(move: chess.Move) -> int:
    return (move.from_square << 6) | move.to_square


MOVE_KEY_MASK = {}
for sq1 in range(64):
    for sq2 in range(64):
        move = chess.Move(sq1, sq2)
        MOVE_KEY_MASK[make_move_key(move)] = move
        for promo in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
            move = chess.Move(sq1, sq2, promotion=promo)
            MOVE_KEY_MASK[make_move_key(move) | (promo << 12)] = move


def board_key(board: chess.Board) -> int:
    return hash((board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK],
                 board.pawns, board.knights, board.bishops, board.rooks, board.queens,
                 board.kings, board.turn, board.castling_rights, board.ep_square))
