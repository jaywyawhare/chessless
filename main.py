import chess
from chess import STARTING_FEN
import pygame

material_values = {
    'p': 1,
    'n': 3,
    'b': 3.25,
    'r': 5,
    'q': 9,
    'k': 0
}

def evaluate_material(board):
    total = 0
    for piece in board.pieces():
        total += material_values[piece.symbol()]
    return total

def maxmin(depth, alpha, beta, WHITE, BLACK):
    if depth == 0:
        return evaluate_material(board)
    if WHITE:
        best = -9999
        for move in board.legal_moves:
            board.push(move)
            best = max(best, maxmin(depth - 1, alpha, beta, False, BLACK))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 9999
        for move in board.legal_moves:
            board.push(move)
            best = min(best, maxmin(depth - 1, alpha, beta, WHITE, False))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

def generate_tree(STARTING_FEN, WHITE, BLACK):
    board = chess.Board(STARTING_FEN)
    return maxmin(3, -9999, 9999, WHITE, BLACK)
