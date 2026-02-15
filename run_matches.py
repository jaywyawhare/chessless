#!/usr/bin/env python3
"""
Run 100 matches: current algorithm (working tree) vs last commit.
Uses git worktree to run the previous revision. Reports wins/draws and centipawn (avg after move).
"""
import argparse
import os
import subprocess
import sys
import tempfile
import chess
from src.evaluator import Evaluator


def find_repo_root(start: str) -> str:
    path = os.path.abspath(start)
    while path != os.path.dirname(path):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return os.path.abspath(start)


def ensure_clean_or_allow() -> bool:
    if os.environ.get("CHESSLESS_ALLOW_DIRTY") == "1":
        return True
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    return out.returncode == 0 and not out.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 100 matches: current algo vs last commit.")
    parser.add_argument("--depth", type=int, default=2, help="Search depth (default 2)")
    parser.add_argument("--time", type=int, default=2, help="Max time per move in seconds (default 2)")
    parser.add_argument("--games", type=int, default=100, help="Number of games (default 100)")
    parser.add_argument("--no-allow-dirty", action="store_true", help="Require clean working tree")
    args = parser.parse_args()

    if not args.no_allow_dirty:
        os.environ["CHESSLESS_ALLOW_DIRTY"] = "1"

    repo_root = find_repo_root(os.getcwd())
    script = os.path.join(repo_root, "engine_stdin.py")
    if not os.path.isfile(script):
        print("engine_stdin.py not found in repo root", file=sys.stderr)
        sys.exit(1)

    if not ensure_clean_or_allow():
        print("Working tree has uncommitted changes. Commit or omit --no-allow-dirty.", file=sys.stderr)
        sys.exit(1)

    try:
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
    except FileNotFoundError:
        print("git not found.", file=sys.stderr)
        sys.exit(1)

    worktree_path = tempfile.mkdtemp(prefix="chessless_old_")
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

        current_cp_after_move: list = []
        old_cp_after_move: list = []
        env = os.environ.copy()
        env["DEPTH"] = str(args.depth)
        env["TIME"] = str(args.time)
        move_timeout = args.time + 10

        wins_current = 0
        wins_old = 0
        draws = 0
        results = []
        draw_reasons = {"repetition": 0, "fifty_moves": 0, "stalemate": 0, "insufficient_material": 0, "max_plies": 0, "other": 0}
        evaluator = Evaluator()

        for game_id in range(args.games):
            current_is_white = game_id % 2 == 0
            white_cwd = repo_root if current_is_white else worktree_path
            black_cwd = worktree_path if current_is_white else repo_root

            proc_white = subprocess.Popen(
                [sys.executable, script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=white_cwd,
                env=env,
                bufsize=1,
            )
            proc_black = subprocess.Popen(
                [sys.executable, script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=black_cwd,
                env=env,
                bufsize=1,
            )

            board = chess.Board()
            white_stdin = proc_white.stdin
            black_stdin = proc_black.stdin
            white_stdout = proc_white.stdout
            black_stdout = proc_black.stdout
            plies_played = 0

            try:
                while not _game_over_decisive_only(board, plies_played):
                    fen = board.fen()
                    if board.turn == chess.WHITE:
                        white_stdin.write("fen " + fen + "\n")
                        white_stdin.flush()
                        uci = _read_move(white_stdout, move_timeout)
                    else:
                        black_stdin.write("fen " + fen + "\n")
                        black_stdin.flush()
                        uci = _read_move(black_stdout, move_timeout)

                    if not uci:
                        break
                    try:
                        move = chess.Move.from_uci(uci)
                        if move in board.legal_moves:
                            board.push(move)
                            plies_played += 1
                            try:
                                cp = evaluator.evaluate_position(board)
                                mover_view_cp = -cp
                                mover_was_current = (board.turn == chess.BLACK) == current_is_white
                                if mover_was_current:
                                    current_cp_after_move.append(mover_view_cp)
                                else:
                                    old_cp_after_move.append(mover_view_cp)
                            except Exception:
                                pass
                        else:
                            break
                    except ValueError:
                        break

                result = board.result() if _game_over_decisive_only(board, plies_played) else "*"
                if result == "1-0":
                    white_wins = True
                    black_wins = False
                elif result == "0-1":
                    white_wins = False
                    black_wins = True
                else:
                    white_wins = black_wins = False
                    if result == "1/2-1/2":
                        if board.is_stalemate():
                            draw_reasons["stalemate"] += 1
                        elif board.is_insufficient_material():
                            draw_reasons["insufficient_material"] += 1
                        elif plies_played >= 800:
                            draw_reasons["max_plies"] = draw_reasons.get("max_plies", 0) + 1
                        else:
                            draw_reasons["other"] += 1
                    elif result == "*":
                        draw_reasons["other"] += 1

                if white_wins and current_is_white:
                    wins_current += 1
                    results.append("current")
                elif black_wins and current_is_white:
                    wins_old += 1
                    results.append("old")
                elif white_wins and not current_is_white:
                    wins_old += 1
                    results.append("old")
                elif black_wins and not current_is_white:
                    wins_current += 1
                    results.append("current")
                else:
                    draws += 1
                    results.append("draw")

            finally:
                for p, stdin in [(proc_white, white_stdin), (proc_black, black_stdin)]:
                    try:
                        stdin.write("quit\n")
                        stdin.flush()
                        stdin.close()
                    except Exception:
                        pass
                    p.wait(timeout=2)
                    try:
                        p.kill()
                    except Exception:
                        pass

            if (game_id + 1) % 10 == 0:
                print(f"  Games {game_id + 1}/{args.games} — current: {wins_current}, old: {wins_old}, draws: {draws}", flush=True)

    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            capture_output=True,
            cwd=repo_root,
        )
        if os.path.isdir(worktree_path):
            import shutil
            shutil.rmtree(worktree_path, ignore_errors=True)

    print()
    print("=" * 50)
    print(f"Result ({args.games} matches: current algo vs last commit)")
    print("=" * 50)
    print(f"  Current (this tree):  {wins_current} wins")
    print(f"  Last commit:          {wins_old} wins")
    print(f"  Draws:                {draws}")
    if draws:
        reasons = [k for k, v in draw_reasons.items() if v]
        if reasons:
            print("  Draw breakdown:")
            for k in ["repetition", "fifty_moves", "stalemate", "insufficient_material", "max_plies", "other"]:
                if draw_reasons[k]:
                    print(f"    - {k}: {draw_reasons[k]}")
    print("=" * 50)
    if current_cp_after_move or old_cp_after_move:
        def avg(xs):
            return sum(xs) / len(xs) if xs else 0.0
        acpl_current = avg(current_cp_after_move)
        acpl_old = avg(old_cp_after_move)
        print()
        print("Centipawn (avg eval after own move, mover's view; lower = worse play):")
        print(f"  Current (this tree):  {acpl_current:+.1f}  (n={len(current_cp_after_move)})")
        print(f"  Last commit:           {acpl_old:+.1f}  (n={len(old_cp_after_move)})")
        if acpl_current < acpl_old:
            print("  -> Current is playing worse (more negative) = better for a worst-move engine.")
        elif acpl_old < acpl_current:
            print("  -> Last commit is playing worse (more negative) = current is less bad.")
        else:
            print("  -> Similar centipawn on average.")
    print("=" * 50)
    if draws == args.games and wins_current == 0 and wins_old == 0:
        print()
        print("Why all draws? Matches ignore draw by repetition and fifty-move rule")
        print("so games only end by checkmate, stalemate, insufficient material, or max plies.")
        print("If all are draws, games hit max plies or stalemate before checkmate.")


def _game_over_decisive_only(board: chess.Board, plies_played: int = 0, max_plies: int = 800) -> bool:
    """True if game is over; only checkmate, stalemate, insufficient material, or max_plies (no rep/fifty-move)."""
    if board.is_checkmate() or board.is_stalemate():
        return True
    if board.is_insufficient_material():
        return True
    if plies_played >= max_plies:
        return True
    return False


def _read_move(stream, timeout_sec: int) -> str:
    if stream is None:
        return ""
    try:
        import select
        r, _, _ = select.select([stream], [], [], max(1, timeout_sec))
        if not r:
            return ""
    except (ImportError, OSError):
        pass
    line = stream.readline()
    if not line:
        return ""
    line = line.strip()
    if line.startswith("move "):
        return line[5:].strip()
    return _read_move(stream, timeout_sec - 1) if timeout_sec > 1 else ""


if __name__ == "__main__":
    main()
