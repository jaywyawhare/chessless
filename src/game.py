from src.board import ChessBoard
from src.player import ChessPlayer
from src.engine import ChessEngine
import sys

class ChessGame:
    def __init__(self):
        self.board = ChessBoard()
        self.player = ChessPlayer()
        self.engine = ChessEngine()

    def play(self):
        print("Welcome to Chessless - The 'Worst Move' Chess Engine!")
        self.board.display_board()
        first_move = "Player"
        while not self.board.game_over_status:
            if first_move == "Player":
                move = self.player.make_move(self.board)
                if move == "Quit (q)":
                    print("Are you sure you want to quit? (y/n)")
                    choice = input()
                    if choice == "y":
                        break
                    else:
                        continue
                self.board.make_move(move)
                self.board.display_board()
                first_move = "Engine"
            else:
                move = self.engine.get_worst_move(self.board)
                self.board.make_move(move)
                self.board.display_board()
                first_move = "Player"
        print("Game over!")
        print("Thanks for playing!")
        
