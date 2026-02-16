#!/usr/bin/env python3
"""
CLI for the worst-move chess engine.
Usage: python main.py [--depth 3] [--time 5] [--fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]
Prints the worst move in UCI (e.g. e2e4).
"""
import argparse
import chess
from src.engine import WorstEngine


def main():
    parser = argparse.ArgumentParser(description="Get the worst legal move from a position.")
    parser.add_argument("--depth", type=int, default=2, help="Search depth")
    parser.add_argument("--time", type=float, default=1.0, help="Max time per move (seconds)")
    parser.add_argument("--fen", type=str, default=chess.STARTING_FEN, help="Position in FEN")
    args = parser.parse_args()

    board = chess.Board(args.fen)
    engine = WorstEngine(depth=args.depth, max_time=args.time)
    move = engine.get_worst_move(board)
    if move:
        print(move.uci())
    else:
        print("(no legal moves)")


if __name__ == "__main__":
    main()
