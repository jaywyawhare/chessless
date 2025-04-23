class ChesslessEngine:
    def __init__(self):
        self.position = None
        self.piece_values = {
            "P": 1,  # Pawn
            "N": 3,  # Knight
            "B": 3,  # Bishop
            "R": 5,  # Rook
            "Q": 9,  # Queen
            "K": 0,  # King (0 because we don't want to encourage king sacrifices)
        }

    def set_position(self, fen):
        """Set the current position using FEN notation."""
        self.position = fen

    def evaluate_position(self, position):
        """
        Evaluate a position. Returns a high score for bad positions.
        The worse the position, the higher the score!
        """
        # TODO: Implement position evaluation
        pass

    def find_worst_move(self):
        """Find the objectively worst legal move in the current position."""
        # TODO: Implement move search
        pass

    def is_move_legal(self, move):
        """Check if a move is legal in the current position."""
        # TODO: Implement move legality checking
        pass
