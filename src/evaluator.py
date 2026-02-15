"""
Position evaluation for the worst-move engine (bitboard-based).
Optimized with fast bitboard iteration.
"""
import chess
from typing import Dict
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    isolated_files_bb,
    pinned_bb,
    passed_pawns_bb,
    backward_pawns_bb,
    rooks_on_seventh_bb,
    lsb,
    BB_CENTER,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
    BB_BACKRANK_WHITE,
    BB_BACKRANK_BLACK,
    BB_KNIGHT_HOME_WHITE,
    BB_KNIGHT_HOME_BLACK,
    BB_BISHOP_HOME_WHITE,
    BB_BISHOP_HOME_BLACK,
    BB_RIM,
    king_in_center_bb,
    square_bb,
    PIECE_VALUES,
)


class Evaluator:
    def __init__(self) -> None:
        self._cache: Dict[str, float] = {}
        self.max_cache_size = 100_000
        self.position_history: Dict[str, int] = {}

    def evaluate_position(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -50_000 if board.turn else 50_000
        if board.is_stalemate():
            return 25_000
        if board.can_claim_threefold_repetition() or board.is_repetition():
            return 20_000 if board.turn else -20_000
        if board.can_claim_draw():
            return 15_000

        key = board.fen()
        if key in self._cache:
            return self._cache[key]

        us = board.turn
        score = (
            self._material(board)
            + self._mobility(board) * 0.8
            - self._hanging_penalty(board, us) * 45
            - self._king_danger(board, us) * 35
            - self._bad_pawn_structure(board, us) * 20
            - self._center_control(board, us) * 25
            - self._undeveloped(board, us) * 12
            - self._king_in_center_penalty(board, us) * 22
            - self._pieces_on_back_rank(board, us) * 8
            - self._weakened_king_shield(board, us) * 30
            - self._pieces_on_rim(board, us) * 3.5
            + self._their_pieces_on_rim(board, us) * 2.0
            - self._queen_on_good_square(board, us) * 6
            - self._rooks_on_open_file(board, us) * 3
            - self._blocked_pieces(board, us) * 3
            - self._our_pieces_in_center(board, us) * 4
            + self._pinned_bonus(board, us) * 4
            - self._passed_pawn_penalty(board, us) * 3
            + self._backward_pawn_bonus(board, us) * 3
            - self._bishop_pair_penalty(board, us) * 3
            - self._rook_on_seventh_penalty(board, us) * 3
            + self._pst_score(board, us) * 3
            + self._in_check_bonus(board, us) * 2
            + self._trapped_piece_bonus(board, us)
            + self._exposed_king_bonus(board, us)
            + self._no_escape_bonus(board, us)
        )
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score

    def _material(self, board: chess.Board) -> float:
        s = 0
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            v = PIECE_VALUES[pt]
            s += popcount(board.pieces_mask(pt, chess.WHITE)) * v
            s -= popcount(board.pieces_mask(pt, chess.BLACK)) * v
        return float(s if board.turn else -s)

    def _mobility(self, board: chess.Board) -> float:
        us = board.turn
        our_attacks = their_attacks_bb(board, us)
        their_attacks = their_attacks_bb(board, not us)
        return float((popcount(our_attacks) - popcount(their_attacks)) * 5)

    def _hanging_penalty(self, board: chess.Board, us: chess.Color) -> float:
        them = not us
        hanging = hanging_bb(board, us)
        penalty = popcount(hanging) * 420
        bb = hanging
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if p:
                pv = PIECE_VALUES.get(p.piece_type, 0)
                penalty += pv * 12
                att_them = board.attackers_mask(them, sq)
                if att_them:
                    min_them = 100000
                    atb = att_them
                    while atb:
                        s = lsb(atb)
                        atb &= atb - 1
                        piece = board.piece_at(s)
                        if piece:
                            v = PIECE_VALUES.get(piece.piece_type, 0)
                            if v < min_them:
                                min_them = v
                    if min_them < pv:
                        penalty += (pv - min_them) * 10
        return float(penalty)

    def _king_danger(self, board: chess.Board, us: chess.Color) -> float:
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        n = popcount(board.attackers_mask(not us, ksq))
        return float(n * 850)

    def _bad_pawn_structure(self, board: chess.Board, us: chess.Color) -> float:
        penalty = 0.0
        our_pawns = board.pieces_mask(chess.PAWN, us)
        for f in range(8):
            cnt = popcount(our_pawns & chess.BB_FILES[f])
            if cnt >= 2:
                penalty += 320
        isolated = isolated_files_bb(board, us)
        penalty += popcount(isolated) * 240
        return penalty

    def _center_control(self, board: chess.Board, us: chess.Color) -> float:
        our_attacks = their_attacks_bb(board, us)
        return float(popcount(our_attacks & BB_CENTER) * 185)

    def _undeveloped(self, board: chess.Board, us: chess.Color) -> float:
        backrank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        our_bb = our_pieces_bb(board, us)
        non_king = our_bb & ~board.pieces_mask(chess.KING, us)
        return float(popcount(non_king & backrank) * 125)

    def _king_in_center_penalty(self, board: chess.Board, us: chess.Color) -> float:
        return 380.0 if king_in_center_bb(board, us) else 0.0

    def _pieces_on_back_rank(self, board: chess.Board, us: chess.Color) -> float:
        knights_home = BB_KNIGHT_HOME_WHITE if us == chess.WHITE else BB_KNIGHT_HOME_BLACK
        bishops_home = BB_BISHOP_HOME_WHITE if us == chess.WHITE else BB_BISHOP_HOME_BLACK
        n = popcount(board.pieces_mask(chess.KNIGHT, us) & knights_home)
        n += popcount(board.pieces_mask(chess.BISHOP, us) & bishops_home)
        return float(n * 165)

    def _weakened_king_shield(self, board: chess.Board, us: chess.Color) -> float:
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        our_pawns = board.pieces_mask(chess.PAWN, us)
        missing = popcount(shield & ~our_pawns)
        return float(missing * 185)

    def _pieces_on_rim(self, board: chess.Board, us: chess.Color) -> float:
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.KING, us)
        return float(-popcount(our_bb & BB_RIM) * 480)

    def _their_pieces_on_rim(self, board: chess.Board, us: chess.Color) -> float:
        them = not us
        their_bb = our_pieces_bb(board, them) & ~board.pieces_mask(chess.KING, them)
        return float(popcount(their_bb & BB_RIM) * 520)

    def _queen_on_good_square(self, board: chess.Board, us: chess.Color) -> float:
        queen_bb = board.pieces_mask(chess.QUEEN, us)
        if not queen_bb:
            return 0.0
        good_bb = BB_CENTER | chess.BB_RANK_4 | chess.BB_RANK_5
        return float(popcount(queen_bb & good_bb) * 210)

    def _rooks_on_open_file(self, board: chess.Board, us: chess.Color) -> float:
        our_pawns = board.pieces_mask(chess.PAWN, us)
        their_pawns = board.pieces_mask(chess.PAWN, not us)
        rooks = board.pieces_mask(chess.ROOK, us)
        penalty = 0.0
        for f in range(8):
            file_bb = chess.BB_FILES[f]
            if not (rooks & file_bb):
                continue
            our_on_file = bool(our_pawns & file_bb)
            their_on_file = bool(their_pawns & file_bb)
            if not our_on_file:
                penalty += 140 if their_on_file else 240
        return penalty

    def _blocked_pieces(self, board: chess.Board, us: chess.Color) -> float:
        our_bb = our_pieces_bb(board, us)
        occupied = board.occupied
        bonus = 0
        bb = our_bb
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if not p or p.piece_type == chess.PAWN:
                continue
            attacks = board.attacks_mask(sq)
            blocked = attacks & occupied & our_bb
            bonus += popcount(blocked) * 85
        return float(-bonus)

    def _our_pieces_in_center(self, board: chess.Board, us: chess.Color) -> float:
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.PAWN, us) & ~board.pieces_mask(chess.KING, us)
        in_center = popcount(our_bb & BB_CENTER) * 180
        our_attacks = their_attacks_bb(board, us)
        attacking_center = popcount(our_attacks & BB_CENTER & ~our_bb) * 75
        return float(in_center + attacking_center)

    def _pinned_bonus(self, board: chess.Board, us: chess.Color) -> float:
        pinned = pinned_bb(board, us)
        penalty = 0
        bb = pinned
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if p:
                penalty += 165 + PIECE_VALUES.get(p.piece_type, 0)
        return float(-penalty)

    def _passed_pawn_penalty(self, board: chess.Board, us: chess.Color) -> float:
        passed_bb = passed_pawns_bb(board, us)
        r_bonus = {0: 0, 1: 30, 2: 50, 3: 70, 4: 90, 5: 110, 6: 130, 7: 0}
        penalty = 0.0
        bb = passed_bb
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            r = chess.square_rank(sq)
            r = r if us == chess.WHITE else 7 - r
            penalty += 160 + r_bonus.get(r, 0) * 2
        return penalty

    def _backward_pawn_bonus(self, board: chess.Board, us: chess.Color) -> float:
        backward = backward_pawns_bb(board, us)
        return float(-popcount(backward) * 125)

    def _bishop_pair_penalty(self, board: chess.Board, us: chess.Color) -> float:
        bishops = board.pieces_mask(chess.BISHOP, us)
        return 195.0 if popcount(bishops) >= 2 else 0.0

    def _rook_on_seventh_penalty(self, board: chess.Board, us: chess.Color) -> float:
        rooks7 = rooks_on_seventh_bb(board, us)
        return float(popcount(rooks7) * 155)

    def _pst_score(self, board: chess.Board, us: chess.Color) -> float:
        score = 0.0
        back_rank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        our_bb = our_pieces_bb(board, us)
        bb = our_bb
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if not p:
                continue
            pt = p.piece_type
            sq_bb = square_bb(sq)
            if pt == chess.KING:
                if sq_bb & BB_CENTER:
                    score -= 250
                continue
            if sq_bb & BB_RIM:
                score -= 70
            if pt != chess.PAWN and (sq_bb & back_rank):
                score -= 55
        return score

    def _in_check_bonus(self, board: chess.Board, us: chess.Color) -> float:
        if not board.is_check():
            return 0.0
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        n = popcount(board.attackers_mask(not us, ksq))
        return float(-n * 380)

    def _trapped_piece_bonus(self, board: chess.Board, us: chess.Color) -> float:
        bonus = 0.0
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.KING, us)
        bb = our_bb
        legal_moves = list(board.legal_moves)
        move_from = {}
        for m in legal_moves:
            move_from.setdefault(m.from_square, []).append(m)
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            p = board.piece_at(sq)
            if not p:
                continue
            moves = move_from.get(sq, [])
            if len(moves) == 0:
                bonus -= 300 + PIECE_VALUES.get(p.piece_type, 0)
            elif len(moves) == 1:
                to_sq = moves[0].to_square
                if board.is_attacked_by(not us, to_sq):
                    bonus -= 200 + PIECE_VALUES.get(p.piece_type, 0) // 2
        return bonus

    def _exposed_king_bonus(self, board: chess.Board, us: chess.Color) -> float:
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        king_attacks = board.attacks_mask(ksq)
        their_attacks_bb_val = their_attacks_bb(board, not us)
        attacked_escape = king_attacks & their_attacks_bb_val
        occupied_escape = king_attacks & board.occupied
        bad_squares = popcount(attacked_escape | occupied_escape)
        return float(-bad_squares * 150)

    def _no_escape_bonus(self, board: chess.Board, us: chess.Color) -> float:
        legal_count = len(list(board.legal_moves))
        if legal_count <= 1:
            return -800.0
        elif legal_count <= 3:
            return -400.0
        elif legal_count <= 5:
            return -150.0
        return 0.0

    def clear_history(self) -> None:
        self.position_history.clear()
