import chess
from src.evaluator import Evaluator
from src.move_ordering import order_moves
from src.search import WorstMoveSearch
from typing import Optional


class WorstEngine:
    def __init__(self, depth: int = 3, max_time: int = 5):
        self.depth = depth
        self.max_time = max_time
        self.evaluator = Evaluator()
        self.search = WorstMoveSearch(self.evaluator, max_time=max_time)
        self.move_history = {}
        self.last_move = None

    def evaluate(self, board):
        return self.evaluator.evaluate_position(board)

    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Find the worst possible move using alpha-beta search"""
        if not list(board.legal_moves):
            return None

        try:
            # Clear history if too many positions stored
            if len(self.evaluator.position_history) > 1000:
                self.evaluator.clear_history()

            # Use history table for move ordering
            key = board.fen()
            move, score = self.search.get_worst_move(board, self.depth)

            if move and not move in board.legal_moves:
                # Fallback to any legal move if search returns invalid move
                move = list(board.legal_moves)[0]

            # If we're just shuffling pieces, try to find a different bad move
            if self.last_move and move:
                if (
                    move.from_square == self.last_move.to_square
                    and move.to_square == self.last_move.from_square
                ):
                    # Try to find second worst move
                    legal_moves = list(board.legal_moves)
                    if len(legal_moves) > 1:
                        legal_moves.remove(move)
                        move = legal_moves[0]

            if move:
                # Validate move is legal before returning
                if move in board.legal_moves:
                    self.last_move = move
                    return move

            # Fallback to first legal move
            return list(board.legal_moves)[0]

        except Exception as e:
            print(f"Engine error: {str(e)}")
            # Fallback to random legal move
            moves = list(board.legal_moves)
            return moves[0] if moves else None
