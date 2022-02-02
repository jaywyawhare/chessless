import chess
from chess import Board, Move, STARTING_FEN

positions = []
piece_values = {
    'p': 1,
    'n': 3,
    'b': 3.25,
    'r': 5,
    'q': 9,
    'k': 0
}

board = chess.Board(chess.STARTING_FEN)
white_material = 0
black_material = 0

for square in chess.SQUARES:
    piece = board.piece_at(square)
    if piece is not None:
        if piece.color == chess.WHITE:
            white_material += piece_values[piece.symbol()]
        else:
            black_material += piece_values[piece.symbol()]

def maxmini(board, depth, alpha, beta, color):
    if depth == 0 or board.is_game_over():
        return board.result()
    if color == chess.WHITE:
        best_value = -9999
        for move in board.legal_moves:
            board.push(move)
            value = maxmini(board, depth - 1, alpha, beta, chess.BLACK)
            board.pop()
            best_value = max(best_value, value)
            alpha = max(alpha, best_value)
            if beta <= alpha:
                break
        return best_value
    else:
        best_value = 9999
        for move in board.legal_moves:
            board.push(move)
            value = maxmini(board, depth - 1, alpha, beta, chess.WHITE)
            board.pop()
            best_value = min(best_value, value)
            beta = min(beta, best_value)
            if beta <= alpha:
                break
        return best_value

def generate_tree(fen):
    board = chess.Board(fen)
    legal_moves = list(board.legal_moves)
    if fen in positions:
        return positions[fen]
    else:
        for move in legal_moves:
            board.push(move)
            value = maxmini(board, 3, -9999, 9999, chess.WHITE)
            board.pop()
            positions[fen] = value
        return value

        generate_tree(next_fen)
        try:
            generate_tree(STARTING_FEN)
        
        except RecursionError:
            print('RecursionError')
            return
        except:
            print('Error')
            return
