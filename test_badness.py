#!/usr/bin/env python3
"""
Compare how "bad" the current worst-move engine is versus the last commit.

Method:
- Create a git worktree at HEAD~1 (old engine).
- Launch two engine processes (current + old) using engine_stdin.py.
- Generate many random midgame positions by playing random legal moves.
- For each position:
  - Ask both engines for a move.
  - Apply each move on a copy of the position.
  - Evaluate the resulting position once using the CURRENT evaluator.
  - Record the score from the mover's point of view (-eval_after_move).

Lower (more negative) average = the engine leaves itself in worse positions
on average, i.e. it plays "worse" in our terms.
"""
import argparse
import os
import random
import subprocess
import sys
import tempfile
from typing import List, Tuple

import chess

from src.evaluator import Evaluator


def find_repo_root(start: str) -> str:
    path = os.path.abspath(start)
    while path != os.path.dirname(path):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return os.path.abspath(start)


def run_engine_move(
    proc: subprocess.Popen,
    fen: str,
    timeout_sec: float,
) -> str:
    """Send FEN to engine_stdin.py process and read back UCI move."""
    stdin = proc.stdin
    stdout = proc.stdout
    if stdin is None or stdout is None:
        return ""
    try:
        stdin.write(f"fen {fen}\n")
        stdin.flush()
    except Exception:
        return ""

    # Simple blocking read; engine_stdin.py is fast for our depths.
    line = stdout.readline()
    if not line:
        return ""
    line = line.strip()
    if not line.startswith("move "):
        return ""
    return line[5:].strip()


def random_midgame_position(
    min_random_plies: int,
    max_random_plies: int,
    max_attempts: int = 20,
) -> Tuple[chess.Board, bool]:
    """Generate a random non-terminal position by random playout from start."""
    for _ in range(max_attempts):
        board = chess.Board()
        plies = random.randint(min_random_plies, max_random_plies)
        for _ in range(plies):
            if board.is_game_over():
                break
            moves = list(board.legal_moves)
            if not moves:
                break
            move = random.choice(moves)
            board.push(move)
        if board.is_game_over() or board.is_insufficient_material():
            continue
        return board, True
    return chess.Board(), False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure how much worse the current engine plays versus the last commit.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=200,
        help="Number of random positions to test (default 200)",
    )
    parser.add_argument(
        "--min-random-plies",
        type=int,
        default=8,
        help="Minimum random plies before sampling a position (default 8)",
    )
    parser.add_argument(
        "--max-random-plies",
        type=int,
        default=40,
        help="Maximum random plies before sampling a position (default 40)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Search depth for both engines (default 2)",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=2.0,
        help="Max time per move (seconds) for both engines (default 2.0)",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(os.getcwd())
    script = os.path.join(repo_root, "engine_stdin.py")
    if not os.path.isfile(script):
        print("engine_stdin.py not found in repo root", file=sys.stderr)
        sys.exit(1)

    # Resolve parent revision.
    rev = subprocess.run(
        ["git", "rev-parse", "HEAD~1"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if rev.returncode != 0:
        print("No parent commit (HEAD~1). Need at least one commit.", file=sys.stderr)
        sys.exit(1)
    parent_rev = rev.stdout.strip()

    worktree_path = tempfile.mkdtemp(prefix="chessless_badness_old_")
    evaluator = Evaluator()

    current_scores: List[float] = []
    old_scores: List[float] = []
    current_better = 0
    old_better = 0
    equal_scores = 0

    try:
        add_out = subprocess.run(
            ["git", "worktree", "add", worktree_path, parent_rev],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if add_out.returncode != 0:
            print("git worktree add failed:", add_out.stderr, file=sys.stderr)
            sys.exit(1)

        env = os.environ.copy()
        env["DEPTH"] = str(args.depth)
        env["TIME"] = str(args.time)

        # Launch engines: current + old.
        proc_current = subprocess.Popen(
            [sys.executable, script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=repo_root,
            env=env,
            bufsize=1,
        )
        proc_old = subprocess.Popen(
            [sys.executable, script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=worktree_path,
            env=env,
            bufsize=1,
        )

        try:
            ok_samples = 0
            attempts = 0
            max_total_attempts = args.samples * 5

            while ok_samples < args.samples and attempts < max_total_attempts:
                attempts += 1
                board, ok = random_midgame_position(
                    args.min_random_plies,
                    args.max_random_plies,
                )
                if not ok:
                    continue
                fen = board.fen()

                # Get moves from both engines.
                uci_current = run_engine_move(proc_current, fen, timeout_sec=args.time + 5)
                uci_old = run_engine_move(proc_old, fen, timeout_sec=args.time + 5)
                if not uci_current or not uci_old:
                    continue

                try:
                    move_current = chess.Move.from_uci(uci_current)
                    move_old = chess.Move.from_uci(uci_old)
                except ValueError:
                    continue

                if move_current not in board.legal_moves or move_old not in board.legal_moves:
                    continue

                # Evaluate resulting positions from mover's perspective.
                b_cur = chess.Board(fen)
                b_cur.push(move_current)
                val_cur = evaluator.evaluate_position(b_cur)
                mover_view_cur = -val_cur  # evaluator is from side-to-move; negate for mover.

                b_old = chess.Board(fen)
                b_old.push(move_old)
                val_old = evaluator.evaluate_position(b_old)
                mover_view_old = -val_old

                current_scores.append(mover_view_cur)
                old_scores.append(mover_view_old)
                ok_samples += 1

                if mover_view_cur < mover_view_old:
                    current_better += 1  # current is worse (more negative) more often.
                elif mover_view_old < mover_view_cur:
                    old_better += 1
                else:
                    equal_scores += 1

                if ok_samples % 20 == 0:
                    print(
                        f"  Positions {ok_samples}/{args.samples} "
                        f"(current worse: {current_better}, old worse: {old_better})",
                        flush=True,
                    )

        finally:
            # Shut down engines.
            for proc in (proc_current, proc_old):
                stdin = proc.stdin
                if stdin:
                    try:
                        stdin.write("quit\n")
                        stdin.flush()
                        stdin.close()
                    except Exception:
                        pass
                try:
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            capture_output=True,
            cwd=repo_root,
        )
        if os.path.isdir(worktree_path):
            import shutil

            shutil.rmtree(worktree_path, ignore_errors=True)

    def avg(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    n = len(current_scores)
    print()
    print("=" * 60)
    print(f"Badness test with {n} positions (current vs last commit)")
    print("=" * 60)
    if n == 0:
        print("No valid samples collected.")
        sys.exit(0)

    acpl_current = avg(current_scores)
    acpl_old = avg(old_scores)
    print("Scores are eval after own move, from mover's view.")
    print("Lower (more negative) = leaves itself in worse positions (better worst-play).")
    print()
    print(f"  Current (this tree):  {acpl_current:+.1f}  (n={n})")
    print(f"  Last commit:          {acpl_old:+.1f}  (n={n})")
    print()
    print(
        f"  Positions where current was worse (more negative): {current_better} "
        f"({current_better / n * 100:.1f}%)",
    )
    print(
        f"  Positions where last commit was worse:             {old_better} "
        f"({old_better / n * 100:.1f}%)",
    )
    print(f"  Positions with equal score:                        {equal_scores}")
    print("=" * 60)
    if acpl_current < acpl_old:
        print("Result: current engine leaves itself worse on average (more 'worst').")
    elif acpl_old < acpl_current:
        print("Result: last commit leaves itself worse; current got slightly less bad.")
    else:
        print("Result: similar average badness between current and last commit.")


if __name__ == "__main__":
    main()

