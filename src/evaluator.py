import chess
import chess.engine

class Evaluator:
    def __init__(self, engine_path):
        self.engine_path = engine_path

    def evaluate_position(self, fen):
        with chess.engine.SimpleEngine.popen_uci(self.engine_path) as engine:
            board = chess.Board(fen)
            info = engine.analyse(board, chess.engine.Limit(time=0.01))
            score = info.get("score")

            if score is None:
                return 0

            score_value = score.white()
            if score_value.is_mate():
                mate_in_moves = int(str(score_value).replace("#", ""))
                return (
                    10000 - (mate_in_moves * 100)
                    if mate_in_moves > 0
                    else -10000 + (-mate_in_moves * 100)
                )
            return int(str(score_value))
