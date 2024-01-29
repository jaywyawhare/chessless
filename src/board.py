import chess
import sys

class ChessBoard:
    def __init__(self):
        self.board = chess.Board()

    def display_board(self):
        print(self.board)

    def make_move(self, move):
        self.board.push(chess.Move.from_uci(move))

    @property
    def game_over_status(self):
        return self.board.is_game_over()

    def get_legal_moves(self):
        return [move.uci() for move in self.board.legal_moves]
