import chess
from typing import List, Tuple


def order_moves(board, history_table=None) -> List[chess.Move]:
    scored_moves = []
    for move in board.legal_moves:
        score = score_move(board, move)

        # Add history score if available
        if history_table and board.fen() in history_table:
            if move in history_table[board.fen()]:
                score += history_table[board.fen()][move]

        scored_moves.append((score, move))

    # Sort by score ascending (worst moves first)
    return [move for _, move in sorted(scored_moves)]


def score_move(board: chess.Board, move: chess.Move) -> float:
    score = 0

    # Test if move allows opponent to checkmate
    board.push(move)
    opponent_has_mate = False
    for opponent_move in board.legal_moves:
        board.push(opponent_move)
        if board.is_checkmate():
            opponent_has_mate = True
        board.pop()
    board.pop()

    # Heavily reward moves that allow opponent to checkmate
    if opponent_has_mate:
        return 1000

    # Check if move exposes our king
    board.push(move)
    king_square = board.king(not board.turn)
    if king_square:
        attackers = len(board.attackers(board.turn, king_square))
        score += attackers * 50
    board.pop()

    # Reward moves that reduce our mobility
    board.push(move)
    mobility = len(list(board.legal_moves))
    score += (20 - mobility) * 2  # Reward having fewer legal moves
    board.pop()

    # Prioritize captures that lose material
    if board.is_capture(move):
        moving_piece = board.piece_at(move.from_square)
        captured_piece = board.piece_at(move.to_square)
        if moving_piece and captured_piece:
            piece_value = get_piece_value(moving_piece)
            target_value = get_piece_value(captured_piece)
            # Heavy penalty for good captures
            if target_value >= piece_value:
                score -= 10
            # Reward bad captures
            else:
                score += 5

    # Heavily reward walking into attacks
    board.push(move)
    if board.is_attacked_by(not board.turn, move.to_square):
        attacking_pieces = len(list(board.attackers(not board.turn, move.to_square)))
        score += attacking_pieces * 3
    board.pop()

    # Reward moving pieces to bad squares
    piece = board.piece_at(move.from_square)
    if piece:
        # Reward edge squares for knights/bishops
        if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
            if move.to_square in [0, 7, 56, 63]:
                score += 4

        # Reward blocking own pieces
        if piece.piece_type != chess.PAWN:
            if blocks_own_pieces(board, move):
                score += 3

    return score


def blocks_own_pieces(board: chess.Board, move: chess.Move) -> bool:
    piece = board.piece_at(move.from_square)
    if not piece:
        return False
    board.push(move)
    blocks = False
    for sq in board.attacks(move.to_square):
        if board.piece_at(sq) and board.piece_at(sq).color == piece.color:
            blocks = True
            break
    board.pop()
    return blocks


def get_piece_value(piece):
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }
    return values.get(piece.piece_type, 0)
