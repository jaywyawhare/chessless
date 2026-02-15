"""
Position evaluation for the worst-move engine (bitboard-based).
Score is from the side-to-move perspective: positive = good for side to move.
The search minimizes this score; we heavily penalize bad traits so the
engine seeks terrible positions.
"""
import chess
from typing import Dict
from src.bitboards import (
    popcount,
    our_pieces_bb,
    their_attacks_bb,
    hanging_bb,
    pawns_on_file_bb,
    isolated_files_bb,
    pinned_bb,
    passed_pawns_bb,
    backward_pawns_bb,
    rooks_on_seventh_bb,
    BB_CENTER,
    BB_KING_SHIELD_WHITE,
    BB_KING_SHIELD_BLACK,
    BB_BACKRANK_WHITE,
    BB_BACKRANK_BLACK,
    BB_KNIGHT_HOME_WHITE,
    BB_KNIGHT_HOME_BLACK,
    BB_BISHOP_HOME_WHITE,
    BB_BISHOP_HOME_BLACK,
    king_in_center_bb,
    square_bb,
)


class Evaluator:
    def __init__(self) -> None:
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }
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
            self._material_bb(board)
            + self._mobility_bb(board) * 0.8
            - self._hanging_bb_penalty(board, us) * 45
            - self._king_danger_bb(board, us) * 35
            - self._bad_pawn_structure_bb(board, us) * 20
            - self._center_control_bb(board, us) * 25
            - self._undeveloped_bb(board, us) * 12
            - self._king_in_center_penalty(board, us) * 22
            - self._pieces_on_back_rank_bb(board, us) * 8
            - self._weakened_king_shield_bb(board, us) * 30
            - self._pieces_on_rim_bb(board, us) * 3.5
            + self._their_pieces_on_rim_bb(board, us) * 2.0
            - self._queen_on_good_square_bb(board, us) * 6
            - self._rooks_on_open_file_penalty(board, us) * 3
            - self._blocked_pieces_bonus(board, us) * 3
            - self._our_pieces_in_center_penalty(board, us) * 4
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

    def _material_bb(self, board: chess.Board) -> float:
        s = 0.0
        for pt, v in self.piece_values.items():
            s += popcount(board.pieces_mask(pt, chess.WHITE)) * v
            s -= popcount(board.pieces_mask(pt, chess.BLACK)) * v
        return s if board.turn else -s

    def _mobility_bb(self, board: chess.Board) -> float:
        us = board.turn
        them = not us
        our_attacks = their_attacks_bb(board, us)
        their_attacks = their_attacks_bb(board, them)
        s = (popcount(our_attacks) - popcount(their_attacks)) * 5.0
        return s

    def _piece_val(self, piece: chess.Piece) -> int:
        return self.piece_values.get(piece.piece_type, 0)

    def _hanging_bb_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our pieces that are attacked and not defended (bitboard)."""
        them = not us
        hanging = hanging_bb(board, us)
        penalty = popcount(hanging) * 420
        for sq in chess.SQUARES:
            if not (hanging & square_bb(sq)):
                continue
            p = board.piece_at(sq)
            if p:
                penalty += self._piece_val(p) * 12
                att_them = board.attackers_mask(them, sq)
                att_us = board.attackers_mask(us, sq)
                if att_them and att_us:
                    min_them = min(
                        self._piece_val(board.piece_at(s))
                        for s in chess.SQUARES
                        if (att_them & square_bb(s)) and board.piece_at(s)
                    )
                    if min_them < self._piece_val(p):
                        penalty += (self._piece_val(p) - min_them) * 10
        return penalty

    def _king_danger_bb(self, board: chess.Board, us: chess.Color) -> float:
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        n = popcount(board.attackers_mask(not us, ksq))
        return n * 850

    def _bad_pawn_structure_bb(self, board: chess.Board, us: chess.Color) -> float:
        penalty = 0.0
        our_pawns = board.pieces_mask(chess.PAWN, us)
        for f in range(8):
            file_bb = pawns_on_file_bb(board, us, f)
            cnt = popcount(file_bb)
            if cnt >= 2:
                penalty += 320
        isolated = isolated_files_bb(board, us)
        penalty += popcount(isolated) * 240
        return penalty

    def _center_control_bb(self, board: chess.Board, us: chess.Color) -> float:
        our_attacks = their_attacks_bb(board, us)
        return popcount(our_attacks & BB_CENTER) * 185

    def _undeveloped_bb(self, board: chess.Board, us: chess.Color) -> float:
        backrank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        our_bb = our_pieces_bb(board, us)
        non_king = our_bb & ~board.pieces_mask(chess.KING, us)
        return popcount(non_king & backrank) * 125

    def _king_in_center_penalty(self, board: chess.Board, us: chess.Color) -> float:
        return 380.0 if king_in_center_bb(board, us) else 0.0

    def _pieces_on_back_rank_bb(self, board: chess.Board, us: chess.Color) -> float:
        knights_home = BB_KNIGHT_HOME_WHITE if us == chess.WHITE else BB_KNIGHT_HOME_BLACK
        bishops_home = BB_BISHOP_HOME_WHITE if us == chess.WHITE else BB_BISHOP_HOME_BLACK
        n = popcount(board.pieces_mask(chess.KNIGHT, us) & knights_home)
        n += popcount(board.pieces_mask(chess.BISHOP, us) & bishops_home)
        return n * 165

    def _weakened_king_shield_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for missing pawns in front of king (we want to open the king)."""
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        our_pawns = board.pieces_mask(chess.PAWN, us)
        missing = popcount(shield & ~our_pawns)
        return missing * 185

    def _pieces_on_rim_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our pieces on rim so we prefer to put them there (lower score)."""
        rim_bb = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.KING, us)
        return -popcount(our_bb & rim_bb) * 480

    def _their_pieces_on_rim_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Positive when opponent has pieces on rim; we subtract it so their score drops (we prefer that)."""
        them = not us
        rim_bb = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
        their_bb = our_pieces_bb(board, them) & ~board.pieces_mask(chess.KING, them)
        return popcount(their_bb & rim_bb) * 520

    def _queen_on_good_square_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our queen on center/active squares (we want queen on rim or blocked)."""
        queen_bb = board.pieces_mask(chess.QUEEN, us)
        if not queen_bb:
            return 0.0
        good_bb = BB_CENTER | chess.BB_RANK_4 | chess.BB_RANK_5
        return popcount(queen_bb & good_bb) * 210

    def _rooks_on_open_file_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our rooks on open/half-open files (we want them blocked)."""
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

    def _blocked_pieces_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus (negative term) for our pieces that are blocked by our own pawns/pieces."""
        our_bb = our_pieces_bb(board, us)
        occupied = board.occupied
        bonus = 0.0
        for sq in chess.SQUARES:
            if not (our_bb & square_bb(sq)):
                continue
            p = board.piece_at(sq)
            if not p or p.piece_type == chess.PAWN:
                continue
            attacks = board.attacks_mask(sq)
            blocked = attacks & occupied & our_bb
            bonus += popcount(blocked) * 85
        return -bonus

    def _our_pieces_in_center_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our non-pawn pieces occupying or attacking center (we want them passive)."""
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.PAWN, us) & ~board.pieces_mask(chess.KING, us)
        in_center = popcount(our_bb & BB_CENTER) * 180
        our_attacks = their_attacks_bb(board, us)
        attacking_center = popcount(our_attacks & BB_CENTER & ~our_bb) * 75
        return in_center + attacking_center

    def _pinned_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus (negative term) for our pinned pieces; we want to be pinned."""
        pinned = pinned_bb(board, us)
        penalty = 0.0
        for sq in chess.SQUARES:
            if not (pinned & square_bb(sq)):
                continue
            p = board.piece_at(sq)
            if p:
                penalty += 165 + self._piece_val(p)
        return -penalty

    def _passed_pawn_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our passed pawns; we don't want them."""
        passed_bb = passed_pawns_bb(board, us)
        r_bonus = {0: 0, 1: 30, 2: 50, 3: 70, 4: 90, 5: 110, 6: 130, 7: 0}
        penalty = 0.0
        for sq in chess.SQUARES:
            if not (passed_bb & square_bb(sq)):
                continue
            r = chess.square_rank(sq)
            r = r if us == chess.WHITE else 7 - r
            penalty += 160 + r_bonus.get(r, 0) * 2
        return penalty

    def _backward_pawn_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus (negative term) for our backward pawns; we want weak pawns."""
        backward = backward_pawns_bb(board, us)
        return -popcount(backward) * 125

    def _bishop_pair_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for having the bishop pair; we want to give one away."""
        bishops = board.pieces_mask(chess.BISHOP, us)
        if popcount(bishops) >= 2:
            return 195
        return 0.0

    def _rook_on_seventh_penalty(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our rooks on 7th rank; we want them passive."""
        rooks7 = rooks_on_seventh_bb(board, us)
        return popcount(rooks7) * 155

    def _pst_score(self, board: chess.Board, us: chess.Color) -> float:
        """Inverted PST: reward bad squares (rim, back rank for pieces; center for king)."""
        score = 0.0
        rim = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
        back_rank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != us:
                continue
            pt = p.piece_type
            sq_bb = square_bb(sq)
            if pt == chess.KING:
                if sq_bb & BB_CENTER:
                    score -= 250
                continue
            if sq_bb & rim:
                score -= 70
            if pt != chess.PAWN and (sq_bb & back_rank):
                score -= 55
        return score

    def _in_check_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus (negative term) for being in check; we want to be in check."""
        if not board.is_check():
            return 0.0
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        n = popcount(board.attackers_mask(not us, ksq))
        return -n * 380

    def _trapped_piece_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus for pieces with no legal moves (trapped)."""
        bonus = 0.0
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != us or p.piece_type == chess.KING:
                continue
            moves_from_sq = [m for m in board.legal_moves if m.from_square == sq]
            if len(moves_from_sq) == 0:
                bonus -= 300 + self._piece_val(p)
            elif len(moves_from_sq) == 1:
                to_sq = moves_from_sq[0].to_square
                if board.is_attacked_by(not us, to_sq):
                    bonus -= 200 + self._piece_val(p) // 2
        return bonus

    def _exposed_king_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus for king with few escape squares (exposed)."""
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        king_attacks = board.attacks_mask(ksq)
        their_attacks = their_attacks_bb(board, not us)
        attacked_escape = king_attacks & their_attacks
        occupied_escape = king_attacks & board.occupied
        bad_squares = popcount(attacked_escape | occupied_escape)
        return -bad_squares * 150

    def _no_escape_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Bonus for positions where we have very few legal moves."""
        legal_count = len(list(board.legal_moves))
        if legal_count <= 1:
            return -800
        elif legal_count <= 3:
            return -400
        elif legal_count <= 5:
            return -150
        return 0.0

    def clear_history(self) -> None:
        self.position_history.clear()
