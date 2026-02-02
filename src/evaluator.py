"""
Position evaluation for the worst-move engine.
Score is from the side-to-move perspective: positive = good for side to move.
The search minimizes this score, so we heavily penalize bad traits so the
engine actively seeks terrible positions.
"""
import chess
from typing import Dict


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
            self._material(board)
            + self._mobility(board) * 0.5
            - self._hanging_and_attacked(board, us) * 3
            - self._king_danger(board, us) * 2
            - self._bad_pawn_structure(board, us) * 2
            - self._center_control_bonus(board, us) * 2
            - self._undeveloped_and_passive(board, us)
            - self._king_in_center(board, us)
            - self._pieces_on_back_rank(board, us)
        )
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score

    def _material(self, board: chess.Board) -> float:
        s = 0.0
        for pt, v in self.piece_values.items():
            s += len(board.pieces(pt, chess.WHITE)) * v
            s -= len(board.pieces(pt, chess.BLACK)) * v
        return s if board.turn else -s

    def _mobility(self, board: chess.Board) -> float:
        s = 0.0
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p:
                continue
            n = len(list(board.attacks(sq)))
            s += n * (1 if p.color == board.turn else -1)
        return s * 5.0

    def _piece_val(self, piece: chess.Piece) -> int:
        return self.piece_values.get(piece.piece_type, 0)

    def _hanging_and_attacked(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our pieces that are attacked and not defended or under-defended."""
        them = not us
        penalty = 0.0
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p or p.color != us:
                continue
            attackers_them = board.attackers(them, sq)
            attackers_us = board.attackers(us, sq)
            if not attackers_them:
                continue
            val = self._piece_val(p)
            min_attacker_val = min(
                self._piece_val(board.piece_at(s)) for s in attackers_them if board.piece_at(s)
            ) if attackers_them else 999
            penalty += 60
            if not attackers_us:
                penalty += val * 4
            elif min_attacker_val < val:
                penalty += (val - min_attacker_val) * 3
        return penalty

    def _king_danger(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our king being attacked or exposed."""
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        penalty = 0.0
        n_attackers = len(board.attackers(not us, ksq))
        penalty += n_attackers * 150
        return penalty

    def _bad_pawn_structure(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for doubled/isolated/backward pawns."""
        penalty = 0.0
        for f in range(8):
            file_sqs = [chess.square(f, r) for r in range(8)]
            count = sum(1 for sq in file_sqs if board.piece_at(sq) == chess.Piece(chess.PAWN, us))
            if count >= 2:
                penalty += 50
            if count >= 1:
                adj = [f - 1, f + 1]
                has_neighbor = any(
                    0 <= af < 8 and any(
                        board.piece_at(chess.square(af, r)) == chess.Piece(chess.PAWN, us)
                        for r in range(8)
                    )
                    for af in adj
                )
                if not has_neighbor:
                    penalty += 45
        return penalty

    def _center_control_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for controlling center."""
        center = [chess.D4, chess.D5, chess.E4, chess.E5]
        penalty = 0.0
        for sq in center:
            if board.attackers(us, sq):
                penalty += 20
        return penalty

    def _undeveloped_and_passive(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for having pieces on back rank (we want to avoid developing)."""
        penalty = 0.0
        back_rank = 0 if us == chess.WHITE else 7
        for f in range(8):
            sq = chess.square(f, back_rank)
            p = board.piece_at(sq)
            if p and p.color == us and p.piece_type != chess.KING:
                penalty += 15
        return penalty

    def _king_in_center(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for king still in center (we want to avoid castling)."""
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        file_, rank = chess.square_file(ksq), chess.square_rank(ksq)
        if 2 <= file_ <= 5 and (rank <= 1 if us == chess.WHITE else rank >= 6):
            return 40
        return 0.0

    def _pieces_on_back_rank(self, board: chess.Board, us: chess.Color) -> float:
        """Extra penalty for knights/bishops still at home (blocking castling)."""
        penalty = 0.0
        home_knights = [chess.B1, chess.G1] if us == chess.WHITE else [chess.B8, chess.G8]
        home_bishops = [chess.C1, chess.F1] if us == chess.WHITE else [chess.C8, chess.F8]
        for sq in home_knights + home_bishops:
            p = board.piece_at(sq)
            if p and p.color == us:
                penalty += 25
        return penalty

    def clear_history(self) -> None:
        self.position_history.clear()
