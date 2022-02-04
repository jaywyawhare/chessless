import chess
import random

opponent_color = chess.BLACK
engine_color = chess.WHITE

def random_chess_move():
    return str(random.choice(list(chess.Board().legal_moves)))

def check_move_legal(board, move):
    if move in list(board.legal_moves):
        return True
    else:
        return False


if __name__ == "__main__":
    game = chess.Board()
    while not game.is_game_over():
        print(game)
        if game.turn == opponent_color:
            move = input("Your move: ")
            #check legal move
            game.push_san(move)
        else:
            move = str(random_chess_move()[2:4])
            print(move)
            game.push_san(move)
            
    print("Game over!")
    if game.is_checkmate():
        print("Checkmate!")
    elif game.is_stalemate():
        print("Stalemate!")
    elif game.is_insufficient_material():
        print("Insufficient material!")
    elif game.is_seventyfive_moves():
        print("Fifty-five moves rule!")
    elif game.is_fivefold_repetition():
        print("Fivefold repetition!")
    else:
        print("Draw!")


    
