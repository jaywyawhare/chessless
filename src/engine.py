"""
Worst-move chess engine - consolidated implementation.
All components in a single module for maximum performance.
"""
import chess
import time
from typing import Optional, Dict, Tuple, List

# === CONSTANTS ===
PIECE_VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
PIECE_VALUES_LIGHT = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

BB_CENTER = chess.BB_D4 | chess.BB_D5 | chess.BB_E4 | chess.BB_E5
BB_RIM = chess.BB_FILE_A | chess.BB_FILE_H | chess.BB_RANK_1 | chess.BB_RANK_8
BB_KING_SHIELD_WHITE = chess.BB_E2 | chess.BB_D2 | chess.BB_F2
BB_KING_SHIELD_BLACK = chess.BB_E7 | chess.BB_D7 | chess.BB_F7

RIM_SQUARES = frozenset({chess.A1, chess.H1, chess.A8, chess.H8, chess.A2, chess.H2, chess.A7, chess.H7})
KNIGHT_RIM_SQUARES = frozenset({chess.A3, chess.H3, chess.A6, chess.H6})

# Scoring constants for move ordering
SCORE_CHECKMATE = -300000
SCORE_HANGING_QUEEN = -50000
SCORE_HANGING_ROOK = -25000
SCORE_BAD_CAPTURE = -25000
SCORE_PAWN_SHIELD = -4000
SCORE_KING_MOVE = -4000
SCORE_KING_CENTER = -2000
SCORE_QUEEN_RIM = -2500
SCORE_KNIGHT_RIM = -2200
SCORE_BISHOP_RIM = -2000
SCORE_DEVELOP = -4000
SCORE_CASTLE = 10000
SCORE_RIM_SQ = -1500
SCORE_RIM_FILE = -500
SCORE_EQUAL_CAPTURE = -8000
SCORE_CHECK = -20000
SCORE_DRAW = -80000


# === UTILITY FUNCTIONS ===
def popcount(bb: int) -> int:
    return bb.bit_count() if bb else 0


def lsb(bb: int) -> int:
    return (bb & -bb).bit_length() - 1 if bb else -1


def square_bb(sq: int) -> int:
    return 1 << sq


def file_of(sq: int) -> int:
    return sq & 7


def rank_of(sq: int) -> int:
    return sq >> 3


def board_hash(board: chess.Board) -> int:
    return hash((
        board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK],
        board.pawns, board.knights, board.bishops, board.rooks, board.queens,
        board.kings, board.turn, board.castling_rights, board.ep_square
    ))


# === EVALUATOR ===
class Evaluator:
    __slots__ = ['_cache', 'max_cache_size']
    
    def __init__(self):
        self._cache: Dict[int, float] = {}
        self.max_cache_size = 50000
    
    def evaluate(self, board: chess.Board) -> float:
        if board.is_checkmate():
            return -50000 if board.turn else 50000
        if board.is_stalemate():
            return 25000
        if board.can_claim_draw():
            return 15000
        
        key = board_hash(board)
        if key in self._cache:
            return self._cache[key]
        
        us = board.turn
        score = self._eval(board, us)
        
        if len(self._cache) >= self.max_cache_size:
            self._cache.clear()
        self._cache[key] = score
        return score
    
    def _eval(self, board: chess.Board, us: bool) -> float:
        them = not us
        score = 0.0
        
        # Material
        for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            v = PIECE_VALUES[pt]
            score += popcount(board.pieces_mask(pt, chess.WHITE)) * v
            score -= popcount(board.pieces_mask(pt, chess.BLACK)) * v
        if us == chess.BLACK:
            score = -score
        
        # King danger
        ksq = board.king(us)
        if ksq is not None:
            attackers = popcount(board.attackers_mask(them, ksq))
            score -= attackers * 1500
            
            # King escape squares
            king_att = board.attacks_mask(ksq)
            their_att = 0
            for pt in range(1, 7):
                bb = board.pieces_mask(pt, them)
                while bb:
                    sq = lsb(bb)
                    bb &= bb - 1
                    their_att |= board.attacks_mask(sq)
            bad_escape = popcount(king_att & (their_att | board.occupied))
            score -= bad_escape * 300
        
        # Hanging pieces
        our_bb = board.occupied_co[us]
        bb = our_bb
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
                p = board.piece_at(sq)
                if p:
                    score -= 600 + PIECE_VALUES_LIGHT.get(p.piece_type, 0) * 100
        
        # King shield
        our_pawns = board.pieces_mask(chess.PAWN, us)
        shield = BB_KING_SHIELD_WHITE if us else BB_KING_SHIELD_BLACK
        score -= popcount(shield & ~our_pawns) * 500
        
        # Pieces on back rank (bad - we want them developed)
        backrank = chess.BB_RANK_1 if us else chess.BB_RANK_8
        our_non_king = our_bb & ~board.pieces_mask(chess.KING, us)
        score -= popcount(our_non_king & backrank) * 100
        
        # Center control (bad for worst engine)
        score -= popcount(our_non_king & BB_CENTER) * 300
        
        # Rim pieces (good for worst engine)
        score += popcount(our_non_king & BB_RIM) * 200
        
        # Bishop pair penalty
        bishops = board.pieces_mask(chess.BISHOP, us)
        if popcount(bishops) >= 2:
            score -= 400
        
        # In check bonus
        if board.is_check():
            score -= 800
        
        # Few legal moves (bad)
        legal_count = sum(1 for _ in board.legal_moves)
        if legal_count <= 1:
            score -= 1500
        elif legal_count <= 3:
            score -= 800
        elif legal_count <= 5:
            score -= 300
        
        # Defenders (we want to remove them)
        bb = our_non_king
        while bb:
            sq = lsb(bb)
            bb &= bb - 1
            defenders = board.attackers_mask(us, sq)
            if defenders and not (defenders & square_bb(sq)):
                score -= popcount(defenders) * 150
        
        return float(score)


# === MOVE ORDERING ===
def score_move(board: chess.Board, move: chess.Move) -> float:
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)
    
    if not moving_piece:
        return 0.0
    
    us = board.turn
    them = not us
    pt = moving_piece.piece_type
    pv = PIECE_VALUES_LIGHT[pt]
    to_file = file_of(to_sq)
    to_rank = rank_of(to_sq)
    
    score = 0.0
    
    # Piece-specific bad moves
    if pt == chess.PAWN:
        shield = BB_KING_SHIELD_WHITE if us else BB_KING_SHIELD_BLACK
        if square_bb(from_sq) & shield:
            score += SCORE_PAWN_SHIELD
        if to_file in (0, 7):
            score -= 1000
    
    elif pt == chess.KING:
        if not board.is_castling(move):
            score += SCORE_KING_MOVE
        if to_file in (2, 3, 4, 5):
            score += SCORE_KING_CENTER
    
    elif pt == chess.QUEEN:
        if to_file in (0, 7) or to_rank in (0, 7):
            score += SCORE_QUEEN_RIM
    
    elif pt == chess.KNIGHT:
        if to_file in (0, 7):
            score += SCORE_KNIGHT_RIM
        if to_sq in KNIGHT_RIM_SQUARES:
            score -= 400
    
    elif pt == chess.BISHOP:
        if to_file in (0, 7):
            score += SCORE_BISHOP_RIM
    
    # Development penalty
    backrank = chess.BB_RANK_1 if us else chess.BB_RANK_8
    if square_bb(from_sq) & backrank and pt in (chess.KNIGHT, chess.BISHOP):
        score += SCORE_DEVELOP
    
    # Castling (good, avoid)
    if board.is_castling(move):
        score -= SCORE_CASTLE
    
    # Rim squares
    if to_sq in RIM_SQUARES:
        score += SCORE_RIM_SQ
    elif to_file in (0, 7):
        score += SCORE_RIM_FILE
    
    # Captures
    if board.is_capture(move):
        captured = board.piece_at(to_sq)
        if captured:
            cv = PIECE_VALUES_LIGHT[captured.piece_type]
            if cv > pv:
                score += SCORE_BAD_CAPTURE
            elif cv == pv:
                score += SCORE_EQUAL_CAPTURE
    
    # Push and check for mate/hanging
    board.push(move)
    
    if board.is_checkmate():
        board.pop()
        return float(SCORE_CHECKMATE)
    
    if board.is_check():
        score += SCORE_CHECK
    
    if board.is_stalemate() or board.can_claim_draw():
        score -= SCORE_DRAW
    
    # Check for hanging pieces after move
    our_bb = board.occupied_co[us]
    has_hanging_queen = False
    has_hanging_rook = False
    
    bb = our_bb
    while bb:
        sq = lsb(bb)
        bb &= bb - 1
        if board.attackers_mask(them, sq) and not board.attackers_mask(us, sq):
            p = board.piece_at(sq)
            if p:
                if p.piece_type == chess.QUEEN:
                    has_hanging_queen = True
                elif p.piece_type == chess.ROOK:
                    has_hanging_rook = True
    
    if has_hanging_queen:
        score += SCORE_HANGING_QUEEN
    if has_hanging_rook:
        score += SCORE_HANGING_ROOK
    
    board.pop()
    return score


def order_moves(board: chess.Board, killer: Optional[chess.Move] = None) -> List[chess.Move]:
    moves = list(board.legal_moves)
    scored = [(score_move(board, m), m) for m in moves]
    
    if killer:
        for i, (s, m) in enumerate(scored):
            if m == killer:
                scored[i] = (s - 15000, m)
    
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored]


# === ENGINES ===
class GreedyEngine:
    """Fast greedy worst-move finder - no search tree."""
    __slots__ = ['evaluator']
    
    def __init__(self):
        self.evaluator = Evaluator()
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        moves = list(board.legal_moves)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]
        
        ordered = order_moves(board)
        
        # Check for immediate mate
        for move in ordered:
            board.push(move)
            if board.is_checkmate():
                board.pop()
                return move
            board.pop()
        
        # Evaluate top candidates
        best_move = ordered[0]
        best_score = float('inf')
        
        for move in ordered[:12]:
            board.push(move)
            score = self.evaluator.evaluate(board)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
        
        return best_move


class SearchEngine:
    """Search-based worst-move finder with shallow lookahead."""
    __slots__ = ['evaluator', 'max_time', 'depth', 'start_time']
    
    def __init__(self, depth: int = 2, max_time: float = 1.0):
        self.evaluator = Evaluator()
        self.max_time = max_time
        self.depth = min(depth, 5)
        self.start_time = 0.0
    
    def _is_timeout(self) -> bool:
        import time
        return time.time() - self.start_time >= self.max_time
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        import time
        moves = list(board.legal_moves)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]
        
        self.start_time = time.time()
        ordered = order_moves(board)
        
        # Check for immediate mate
        for move in ordered:
            board.push(move)
            if board.is_checkmate():
                board.pop()
                return move
            board.pop()
        
        best_move = ordered[0]
        best_score = float('inf')
        
        # Evaluate fewer moves at higher depth to stay fast
        num_moves = max(4, 8 - self.depth)
        
        for move in ordered[:num_moves]:
            if self._is_timeout():
                break
            board.push(move)
            score = -self._search(board, self.depth - 1)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _search(self, board: chess.Board, depth: int) -> float:
        if self._is_timeout() or depth <= 0:
            return self.evaluator.evaluate(board)
        
        moves = list(board.legal_moves)
        if not moves:
            return -50000 if board.is_check() else 15000
        
        ordered = order_moves(board)
        best = -1e9
        
        # Search fewer moves at deeper levels
        num_moves = max(2, 5 - (self.depth - depth))
        
        for move in ordered[:num_moves]:
            if self._is_timeout():
                break
            board.push(move)
            score = -self._search(board, depth - 1)
            board.pop()
            if score > best:
                best = score
        
        return best


# === MAIN ENGINE ===
class WorstEngine:
    """
    Chess engine that finds the worst legal move.
    Uses greedy selection for depth 1, search for depth 2+.
    """
    __slots__ = ['_engine', 'depth', 'max_time']
    
    def __init__(self, depth: int = 2, max_time: float = 1.0):
        self.depth = depth
        self.max_time = max_time
        if depth <= 1:
            self._engine = GreedyEngine()
        else:
            self._engine = SearchEngine(depth=depth, max_time=max_time)
    
    def get_worst_move(self, board: chess.Board) -> Optional[chess.Move]:
        return self._engine.get_worst_move(board)
