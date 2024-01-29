import chess.engine

class ChessEngine:
    def __init__(self):
        self.engine = chess.engine.SimpleEngine.popen_uci("./engine/stockfish")

    def get_worst_move(self, board):
        result = self.engine.play(board.board, chess.engine.Limit(time=1.0))
        best_move = result.move.uci()

        board.board.pop()

        return best_move
