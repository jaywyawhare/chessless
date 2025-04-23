import chess
import logging
import random
from typing import Dict


class Evaluator:
    def __init__(self):
        self.piece_values = {
            chess.PAWN: -2,
            chess.KNIGHT: -6,
            chess.BISHOP: -6,
            chess.ROOK: -10,
            chess.QUEEN: -20,
            chess.KING: -0.1,
        }

        # Add positional penalties
        self.center_squares = {chess.E4, chess.E5, chess.D4, chess.D5}
        self.development_squares = {chess.B1, chess.G1, chess.B8, chess.G8}

        # Anti-positional piece-square tables
        self.piece_square_tables = {
            chess.PAWN: [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                50,
                10,
                10,
                20,
                30,
                30,
                20,
                10,
                10,
                5,
                5,
                10,
                25,
                25,
                10,
                5,
                5,
                0,
                0,
                0,
                20,
                20,
                0,
                0,
                0,
                5,
                -5,
                -10,
                0,
                0,
                -10,
                -5,
                5,
                5,
                10,
                10,
                -20,
                -20,
                10,
                10,
                5,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ],
            chess.KNIGHT: [
                -50,
                -40,
                -30,
                -30,
                -30,
                -30,
                -40,
                -50,
                -40,
                -20,
                0,
                0,
                0,
                0,
                -20,
                -40,
                -30,
                0,
                10,
                15,
                15,
                10,
                0,
                -30,
                -30,
                5,
                15,
                20,
                20,
                15,
                5,
                -30,
                -30,
                0,
                15,
                20,
                20,
                15,
                0,
                -30,
                -30,
                5,
                10,
                15,
                15,
                10,
                5,
                -30,
                -40,
                -20,
                0,
                5,
                5,
                0,
                -20,
                -40,
                -50,
                -40,
                -30,
                -30,
                -30,
                -30,
                -40,
                -50,
            ],
        }

        self.pawn_structure_penalty = 0.2
        self.king_safety_bonus = 0.3
        self.mobility_penalty = 0.15

        # Caching
        self._cache = {}
        self.max_cache_size = 100000

        # Add repetition tracking
        self.position_history = {}
        self.repetition_bonus = 5.0  # Bonus for repeating positions

        # Checkmate seeking behavior
        self.checkmate_value = 10000
        self.potential_mate_bonus = 500
        self.king_exposure_bonus = 50

    def evaluate_position(self, board):
        # Add repetition bonus
        key = board.fen().split(" ")[0]  # Only use piece positions
        self.position_history[key] = self.position_history.get(key, 0) + 1
        repetition_score = 0

        # Give bonus for repeating positions
        if self.position_history[key] > 1:
            repetition_score = self.repetition_bonus * self.position_history[key]

        key = board.fen()
        if key in self._cache:
            return self._cache[key]

        try:
            # Highest priority: if we're getting checkmated
            if board.is_checkmate():
                return self.checkmate_value if board.turn else -self.checkmate_value

            # Check for potential immediate checkmate for opponent
            if self._can_be_mated_next_move(board):
                return self.potential_mate_bonus

            if board.is_stalemate():
                return 0

            score = (
                self._evaluate_material(board) * 1.0
                + self._evaluate_piece_squares(board) * 0.6
                + self._evaluate_king_safety(board) * 0.4
                + self._evaluate_pawn_structure(board) * 0.3
                + self._evaluate_mobility(board) * 0.2
                + repetition_score  # Add repetition score
            )
            score += self._evaluate_position(board)
            score += self._evaluate_piece_vulnerability(board)
            score += self._evaluate_development(board)
            score += self._evaluate_control(board)
            score += (
                self._evaluate_king_vulnerability(board) * 2.0
            )  # Doubled importance

            # Randomization to avoid repetitive play
            score += random.uniform(-0.1, 0.1)

            # Cache the result
            if len(self._cache) >= self.max_cache_size:
                self._cache.clear()
            self._cache[key] = score

            return score
        except Exception as e:
            logging.error(f"Evaluation error: {e}")
            return 0

    def clear_history(self):
        """Clear position history"""
        self.position_history.clear()

    def _can_be_mated_next_move(self, board):
        """Check if opponent can checkmate in one move"""
        board.turn = not board.turn  # Switch to opponent's perspective
        for move in board.legal_moves:
            board.push(move)
            is_mate = board.is_checkmate()
            board.pop()
            if is_mate:
                board.turn = not board.turn  # Switch back
                return True
        board.turn = not board.turn  # Switch back
        return False

    def _evaluate_king_vulnerability(self, board):
        """Evaluate how exposed the king is to potential checkmate"""
        score = 0
        for color in [chess.WHITE, chess.BLACK]:
            king_square = board.king(color)
            if not king_square:
                continue

            # Count attacking pieces near king
            king_attackers = len(board.attackers(not color, king_square))

            # Check squares around king
            for square in chess.SQUARES:
                if chess.square_distance(king_square, square) <= 2:
                    attackers = len(board.attackers(not color, square))
                    score += attackers * self.king_exposure_bonus * (1 if color else -1)

            # Bonus for checked king
            if board.is_check():
                score += self.potential_mate_bonus // 2

            # Bonus for fewer legal moves (less escape squares)
            if board.turn == color:
                score -= len(list(board.legal_moves)) * 10

        return score

    def _evaluate_material(self, board):
        score = 0
        for piece_type in self.piece_values:
            score += (
                len(board.pieces(piece_type, chess.WHITE))
                * self.piece_values[piece_type]
            )
            score -= (
                len(board.pieces(piece_type, chess.BLACK))
                * self.piece_values[piece_type]
            )
        return score

    def _evaluate_position(self, board):
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue
            if board.attackers(not piece.color, square):
                score += 2 if piece.color == chess.WHITE else -2
        return score

    def _evaluate_piece_vulnerability(self, board):
        """Reward having pieces under attack and undefended"""
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue
            attackers = board.attackers(not piece.color, square)
            defenders = board.attackers(piece.color, square)

            # Heavily reward hanging pieces
            if attackers and not defenders:
                score += 5 if piece.color == chess.WHITE else -5

            # Reward overloaded pieces
            if len(attackers) > len(defenders):
                score += 3 if piece.color == chess.WHITE else -3

        return score

    def _evaluate_development(self, board):
        """Penalize good development"""
        score = 0
        for square in self.development_squares:
            piece = board.piece_at(square)
            if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                score -= 2 if piece.color == chess.WHITE else 2
        return score

    def _evaluate_control(self, board):
        """Penalize center control"""
        score = 0
        for square in self.center_squares:
            if board.attackers(chess.WHITE, square):
                score -= 1
            if board.attackers(chess.BLACK, square):
                score += 1
        return score

    def _evaluate_piece_squares(self, board) -> float:
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue

            if piece.piece_type in self.piece_square_tables:
                table_value = self.piece_square_tables[piece.piece_type][square]
                score += table_value if piece.color else -table_value

        return score

    def _evaluate_king_safety(self, board) -> float:
        score = 0
        for color in [chess.WHITE, chess.BLACK]:
            king_square = board.king(color)
            if not king_square:
                continue

            # Reward exposed king
            attackers = len(board.attackers(not color, king_square))
            score += attackers * self.king_safety_bonus * (1 if color else -1)

        return score

    def _evaluate_pawn_structure(self, board) -> float:
        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece or piece.piece_type != chess.PAWN:
                continue

            # Reward doubled/isolated pawns
            file_pawns = len(list(board.pieces(chess.PAWN, piece.color)))
            if file_pawns > 1:
                score += self.pawn_structure_penalty * (1 if piece.color else -1)

        return score

    def _evaluate_mobility(self, board) -> float:
        score = 0
        # Penalize piece mobility
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if not piece:
                continue
            moves = len(list(board.attacks(square)))
            score -= moves * self.mobility_penalty * (1 if piece.color else -1)
        return score
