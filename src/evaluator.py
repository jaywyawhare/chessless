"""
Position evaluation for the worst-move engine.
Score is from the side-to-move perspective: positive = good for side to move.
The search minimizes this score, so we add penalties for bad traits (hanging
pieces, exposed king, bad structure) to make the engine prefer terrible positions.
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
        them = not us
        score = (
            self._material(board)
            + self._mobility(board)
            - self._hanging_and_attacked(board, us)
            - self._king_danger(board, us)
            - self._bad_pawn_structure(board, us)
            - self._center_control_bonus(board, us)
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
            # Attacked: add penalty. If undefended or we're losing material, bigger penalty.
            val = self._piece_val(p)
            min_attacker_val = min(
                self._piece_val(board.piece_at(s)) for s in attackers_them if board.piece_at(s)
            ) if attackers_them else 999
            penalty += 30
            if not attackers_us:
                penalty += val * 2
            elif min_attacker_val < val:
                penalty += (val - min_attacker_val) * 1.5
        return penalty

    def _king_danger(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for our king being attacked or exposed."""
        ksq = board.king(us)
        if ksq is None:
            return 0.0
        penalty = 0.0
        n_attackers = len(board.attackers(not us, ksq))
        penalty += n_attackers * 80
        return penalty

    def _bad_pawn_structure(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for doubled/isolated pawns (we want to encourage them)."""
        penalty = 0.0
        for f in range(8):
            file_sqs = [chess.square(f, r) for r in range(8)]
            count = sum(1 for sq in file_sqs if board.piece_at(sq) == chess.Piece(chess.PAWN, us))
            if count >= 2:
                penalty += 25
            if count >= 1:
                # Isolated: no pawn on adjacent files
                adj = [f - 1, f + 1]
                has_neighbor = any(
                    0 <= af < 8 and any(
                        board.piece_at(chess.square(af, r)) == chess.Piece(chess.PAWN, us)
                        for r in range(8)
                    )
                    for af in adj
                )
                if not has_neighbor:
                    penalty += 20
        return penalty

    def _center_control_bonus(self, board: chess.Board, us: chess.Color) -> float:
        """Penalty for controlling center (we want to avoid it)."""
        center = [chess.D4, chess.D5, chess.E4, chess.E5]
        penalty = 0.0
        for sq in center:
            if board.attackers(us, sq):
                penalty += 8
        return penalty

    def clear_history(self) -> None:
        self.position_history.clear()
