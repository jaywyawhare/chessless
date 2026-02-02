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
            return -10_000 if board.turn else 10_000
        if board.is_stalemate():
            return 0.0

        key = board.fen()
        if key in self._cache:
            return self._cache[key]

        us = board.turn
        score = (
            self._material_bb(board)
            + self._mobility_bb(board) * 0.3
            - self._hanging_bb_penalty(board, us) * 4
            - self._king_danger_bb(board, us) * 2
            - self._bad_pawn_structure_bb(board, us) * 2
            - self._center_control_bb(board, us) * 2
            - self._undeveloped_bb(board, us) * 2
            - self._king_in_center_penalty(board, us) * 2
            - self._pieces_on_back_rank_bb(board, us) * 2
            - self._weakened_king_shield_bb(board, us)
            - self._pieces_on_rim_bb(board, us)
            + self._their_pieces_on_rim_bb(board, us)
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
        penalty = popcount(hanging) * 80
        for sq in chess.SQUARES:
            if not (hanging & square_bb(sq)):
                continue
            p = board.piece_at(sq)
            if p:
                penalty += self._piece_val(p) * 5
                # Under-defended: they attack with smaller piece
                att_them = board.attackers_mask(them, sq)
                att_us = board.attackers_mask(us, sq)
                if att_them and att_us:
                    min_them = min(
                        self._piece_val(board.piece_at(s))
                        for s in chess.SQUARES
                        if (att_them & square_bb(s)) and board.piece_at(s)
                    )
                    if min_them < self._piece_val(p):
                        penalty += (self._piece_val(p) - min_them) * 4
        return penalty

    def _king_danger_bb(self, board: chess.Board, us: chess.Color) -> float:
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        n = popcount(board.attackers_mask(not us, ksq))
        return n * 180

    def _bad_pawn_structure_bb(self, board: chess.Board, us: chess.Color) -> float:
        penalty = 0.0
        our_pawns = board.pieces_mask(chess.PAWN, us)
        for f in range(8):
            file_bb = pawns_on_file_bb(board, us, f)
            cnt = popcount(file_bb)
            if cnt >= 2:
                penalty += 60
        isolated = isolated_files_bb(board, us)
        penalty += popcount(isolated) * 50
        return penalty

    def _center_control_bb(self, board: chess.Board, us: chess.Color) -> float:
        our_attacks = their_attacks_bb(board, us)
        return popcount(our_attacks & BB_CENTER) * 35

    def _undeveloped_bb(self, board: chess.Board, us: chess.Color) -> float:
        backrank = BB_BACKRANK_WHITE if us == chess.WHITE else BB_BACKRANK_BLACK
        our_bb = our_pieces_bb(board, us)
        non_king = our_bb & ~board.pieces_mask(chess.KING, us)
        return popcount(non_king & backrank) * 20

    def _king_in_center_penalty(self, board: chess.Board, us: chess.Color) -> float:
        return 50.0 if king_in_center_bb(board, us) else 0.0

    def _pieces_on_back_rank_bb(self, board: chess.Board, us: chess.Color) -> float:
        knights_home = BB_KNIGHT_HOME_WHITE if us == chess.WHITE else BB_KNIGHT_HOME_BLACK
        bishops_home = BB_BISHOP_HOME_WHITE if us == chess.WHITE else BB_BISHOP_HOME_BLACK
        n = popcount(board.pieces_mask(chess.KNIGHT, us) & knights_home)
        n += popcount(board.pieces_mask(chess.BISHOP, us) & bishops_home)
        return n * 30

    def _weakened_king_shield_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for missing pawns in front of king (we want to open the king)."""
        shield = BB_KING_SHIELD_WHITE if us == chess.WHITE else BB_KING_SHIELD_BLACK
        our_pawns = board.pieces_mask(chess.PAWN, us)
        missing = popcount(shield & ~our_pawns)
        return missing * 35

    def _pieces_on_rim_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our pieces on rim so we prefer to put them there (lower score)."""
        rim_bb = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
        our_bb = our_pieces_bb(board, us) & ~board.pieces_mask(chess.KING, us)
        return -popcount(our_bb & rim_bb) * 120

    def _their_pieces_on_rim_bb(self, board: chess.Board, us: chess.Color) -> float:
        """Positive when opponent has pieces on rim; we subtract it so their score drops (we prefer that)."""
        them = not us
        rim_bb = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
        their_bb = our_pieces_bb(board, them) & ~board.pieces_mask(chess.KING, them)
        return popcount(their_bb & rim_bb) * 150

    def clear_history(self) -> None:
        self.position_history.clear()
