#!/usr/bin/env python3
"""
Engine protocol over stdin/stdout for match play.
Reads "fen <fen>" lines, outputs "move <uci>" lines. "quit" to exit.
"""
import os
import sys
import chess
from src.engine import WorstEngine


def main():
    depth = int(os.environ.get("DEPTH", "2"))
    try:
        max_time = float(os.environ.get("TIME", "1"))
    except ValueError:
        max_time = 1.0
    engine = WorstEngine(depth=depth, max_time=max_time)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "quit":
            break
        if line.startswith("fen "):
            fen = line[4:].strip()
            try:
                board = chess.Board(fen)
                move = engine.get_worst_move(board)
                if move:
                    print("move", move.uci(), flush=True)
                else:
                    print("move", "", flush=True)
            except Exception:
                try:
                    board = chess.Board(fen)
                    legal = list(board.legal_moves)
                    print("move", legal[0].uci() if legal else "", flush=True)
                except Exception:
                    print("move", "", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
