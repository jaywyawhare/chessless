import chess
import numpy as np


def convert_algebraic_to_san(algebraic_notation):
    board = chess.Board()
    moves = algebraic_notation.split()
    fen_list = []

    for move in moves:
        if move.endswith("."):
            continue

        move = move.replace("+", "").replace("#", "")

        try:
            board.push_san(move)
            fen_list.append(board.fen())
        except ValueError:
            print(f"Invalid move: {move}")
            continue

    return fen_list


def convert_fen_to_bitboard(fen):
    bitboards = {
        "P": 0,
        "p": 0,  # white pawns, black pawns
        "R": 0,
        "r": 0,  # white rooks, black rooks
        "N": 0,
        "n": 0,  # white knights, black knights
        "B": 0,
        "b": 0,  # white bishops, black bishops
        "Q": 0,
        "q": 0,  # white queens, black queens
        "K": 0,
        "k": 0,  # white king, black king
    }

    board_part = fen.split()[0]
    rank = 0
    file = 0

    for char in board_part:
        if char.isdigit():
            file += int(char)
        elif char in bitboards:
            index = (rank * 8) + (7 - file)
            bitboards[char] |= 1 << index
            file += 1
        elif char == "/":
            rank += 1
            file = 0

    return bitboards


def serialize_position(fen):
    bitboards = convert_fen_to_bitboard(fen)
    # Order: white pieces then black pieces
    pieces = ["P", "R", "N", "B", "Q", "K", "p", "r", "n", "b", "q", "k"]
    return np.array([bitboards[p] for p in pieces], dtype=np.uint64)


def deserialize_position(serialized_array):
    pieces = ["P", "R", "N", "B", "Q", "K", "p", "r", "n", "b", "q", "k"]
    bitboards = serialized_array.strip("[]").split()
    bitboards = [int(x) for x in bitboards if x]
    return {piece: format(bb, "064b") for piece, bb in zip(pieces, bitboards)}
