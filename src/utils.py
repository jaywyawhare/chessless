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
        "p": 0,
        "r": 0,
        "n": 0,
        "b": 0,
        "q": 0,
        "k": 0,
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

    serialized_array = []
    for piece in ["p", "r", "n", "b", "q", "k"]:
        serialized_array.append(bitboards[piece])

    return np.array(serialized_array, dtype=np.uint64)

def deserialize_position(serialized_array):
    bitboards = serialized_array.strip('[]').split(" ")
    bitboards = [x for x in bitboards if x != '']
    bitboards = [int(x) for x in bitboards]
    pieces = ["p", "r", "n", "b", "q", "k"]
    
    bitboard_dict = {piece: format(bitboards[i], "064b") for i, piece in enumerate(pieces)}
    return bitboard_dict
