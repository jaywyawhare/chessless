import chess
import time
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Optional, List


class WorstMoveSearch:
    def __init__(self, evaluator, max_time=5):
        self.evaluator = evaluator
        self.nodes = 0
        self.start_time = 0
        self.max_time = max_time  # seconds
        self.transposition_table = {}
        self.max_table_size = 1000000
        self.num_threads = mp.cpu_count()
        self.null_move_R = 2
        self.lmr_threshold = 4
        self.futility_margin = 100
        self.history_table = {}
        self.aspiration_window = 50
        self.razoring_margin = 300
        self.futility_margins = [0, 100, 200, 300]

    def is_timeout(self) -> bool:
        return time.time() - self.start_time > self.max_time

    def get_worst_move(
        self, board: chess.Board, depth: int
    ) -> Tuple[Optional[chess.Move], float]:
        try:
            self.start_time = time.time()
            self.nodes = 0
            return self._iterative_deepening(board, depth)
        except TimeoutError:
            # Return the best move found so far
            return self.best_move, self.best_value
        except Exception as e:
            print(f"Search error: {str(e)}")
            # Return a random legal move as fallback
            moves = list(board.legal_moves)
            return moves[0] if moves else None, 0.0

    def _iterative_deepening(self, board: chess.Board, max_depth: int):
        self.best_move = None
        self.best_value = float("inf")

        for depth in range(1, max_depth + 1):
            if self.is_timeout():
                raise TimeoutError()

            try:
                move, value = self._negamax_root(board, depth)
                self.best_move = move
                self.best_value = value
            except TimeoutError:
                break
            except Exception as e:
                print(f"Search error at depth {depth}: {str(e)}")
                break

        if self.best_move is None:
            # Fallback to any legal move
            moves = list(board.legal_moves)
            if moves:
                self.best_move = moves[0]
                self.best_value = 0.0

        return self.best_move, self.best_value

    def _check_time(self):
        if time.time() - self.start_time > self.max_time:
            raise TimeoutError

    def _negamax_root(
        self, board: chess.Board, depth: int
    ) -> Tuple[Optional[chess.Move], float]:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None, 0

        # Parallel search for root moves
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            for move in legal_moves:
                board_copy = board.copy()
                board_copy.push(move)
                futures.append(
                    executor.submit(
                        self._negamax,
                        board_copy,
                        depth - 1,
                        float("-inf"),
                        float("inf"),
                    )
                )

            results = []
            for f in futures:
                try:
                    results.append(f.result())
                except Exception as e:
                    print(f"Search error: {e}")
                    results.append(float("inf"))

            if not results:
                return None, 0

            worst_score = min(results)
            worst_move = legal_moves[results.index(worst_score)]

            return worst_move, -worst_score

    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
        can_null: bool = True,
    ) -> float:
        self._check_time()
        key = board.fen()
        if key in self.transposition_table:
            return self.transposition_table[key]

        if depth == 0:
            return self._quiescence(board, alpha, beta)

        # Razoring
        if depth <= 3 and not board.is_check():
            score = self.evaluator.evaluate_position(board)
            if score + self.razoring_margin * depth <= alpha:
                return self._quiescence(board, alpha, beta)

        # Reverse futility pruning
        if depth <= 3 and not board.is_check():
            score = self.evaluator.evaluate_position(board)
            if score - self.futility_margins[depth] >= beta:
                return beta

        # Null move pruning (reversed - skip good positions)
        if can_null and depth >= 3 and not board.is_check():
            board.push(chess.Move.null())
            value = -self._negamax(
                board, depth - self.null_move_R - 1, -beta, -alpha, False
            )
            board.pop()
            if value >= beta:
                return beta

        # Internal iterative reduction
        if depth >= 4 and not self.transposition_table.get(board.fen()):
            depth -= 1

        moves = self._get_moves_ordered(board)
        if not moves:
            if board.is_check():
                return -10000
            return 0

        # Late move reductions
        value = float("inf")
        for i, move in enumerate(moves):
            # Futility pruning
            if depth <= 2 and not board.is_check():
                if value > -self.futility_margin:
                    continue

            board.push(move)
            # Late move reduction
            if i >= self.lmr_threshold and depth >= 3 and not board.is_check():
                new_depth = depth - 2
            else:
                new_depth = depth - 1

            curr_value = -self._negamax(board, new_depth, -beta, -alpha)
            board.pop()

            value = min(value, curr_value)
            alpha = min(alpha, value)
            if alpha <= beta:
                break

        # Store in transposition table
        if len(self.transposition_table) >= self.max_table_size:
            self.transposition_table.clear()
        self.transposition_table[key] = value

        return value

    def _quiescence(self, board: chess.Board, alpha: float, beta: float) -> float:
        stand_pat = self.evaluator.evaluate_position(board)

        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        # Delta pruning
        worst_possible = stand_pat - 9  # Value of queen
        if worst_possible >= beta:
            return beta

        for move in self._get_captures(board):
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _get_captures(self, board: chess.Board) -> List[chess.Move]:
        return [move for move in board.legal_moves if board.is_capture(move)]

    def _get_moves_ordered(self, board: chess.Board) -> list:
        # Order moves to check tactically bad moves first
        # (captures that lose material, moves that walk into attacks, etc)
        moves = list(board.legal_moves)
        # TODO: Implement move ordering heuristics
        return moves
