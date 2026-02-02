"""
Verify chess edge cases: castling, en passant, promotion, checkmate, stalemate,
illegal move rejection. Uses python-chess; web API uses the same logic.
"""
import chess


def test_castling():
    # Use positions where castling is legal (no need to play full game).
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    for uci in ["e1g1", "e1c1"]:
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves, f"{uci} should be legal"
        board.push(move)
    for uci in ["e8g8", "e8c8"]:
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves, f"{uci} should be legal"
        board.push(move)
    # Kingside: king and rook end up on g1/f1
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    board.push(chess.Move.from_uci("e1g1"))
    assert board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    print("OK castling")


def test_en_passant():
    board = chess.Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
    move = chess.Move.from_uci("e5d6")
    assert move in board.legal_moves
    assert board.is_en_passant(move)
    board.push(move)
    assert board.piece_at(chess.D6) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.piece_at(chess.D5) is None
    print("OK en passant")


def test_promotion():
    # White pawn e7->e8; e8 must be empty (black king elsewhere)
    fen = "5k2/4P3/8/8/8/8/8/4K3 w - - 0 1"
    board = chess.Board(fen)
    for piece in "qrbn":
        board = chess.Board(fen)
        uci = "e7e8" + piece
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves, f"{uci} should be legal"
        board.push(move)
        assert board.piece_at(chess.E8) is not None
    print("OK promotion")


def test_illegal_move_rejected():
    board = chess.Board()
    move = chess.Move.from_uci("e2e5")  # pawn can't move 3 from start like that from e2
    assert move not in board.legal_moves
    move = chess.Move.from_uci("e2e4")
    assert move in board.legal_moves
    board.push(move)
    move = chess.Move.from_uci("e4e5")  # wrong turn / not legal
    assert move not in board.legal_moves
    print("OK illegal move rejected")


def test_checkmate():
    # Back rank mate
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
    move = chess.Move.from_uci("h5f7")
    assert move in board.legal_moves
    board.push(move)
    assert board.is_checkmate()
    assert board.is_game_over()
    assert len(list(board.legal_moves)) == 0
    print("OK checkmate")


def test_stalemate():
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # black to move, stalemate
    assert board.is_stalemate()
    assert board.is_game_over()
    assert len(list(board.legal_moves)) == 0
    print("OK stalemate")


def test_draw_detection():
    # 50-move: halfmove counter 100 in FEN
    board = chess.Board("7k/8/8/8/8/8/8/4K3 w - - 100 1")
    assert board.is_fifty_moves()
    assert board.is_game_over()
    # Insufficient material: K vs K
    board = chess.Board("7k/8/8/8/8/8/8/4K3 w - - 0 1")
    assert board.is_insufficient_material()
    assert board.is_game_over()
    print("OK draw detection")


def test_uci_format():
    # 4-char normal/castling/en passant, 5-char promotion
    assert chess.Move.from_uci("e2e4").uci() == "e2e4"
    assert chess.Move.from_uci("e1g1").uci() == "e1g1"
    assert chess.Move.from_uci("e5d6").uci() == "e5d6"
    assert chess.Move.from_uci("e7e8q").uci() == "e7e8q"
    print("OK UCI format")


def test_move_validation_backend_style():
    """Same checks as web_app handle_move: 4/5 char UCI, from != to, in legal_moves."""
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "g1f3"]:
        assert len(uci) in (4, 5) and uci[:2] != uci[2:4]
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    move = chess.Move.from_uci("e1g1")
    assert move in board.legal_moves
    board.push(move)
    print("OK move validation (backend style)")


if __name__ == "__main__":
    test_castling()
    test_en_passant()
    test_promotion()
    test_illegal_move_rejected()
    test_checkmate()
    test_stalemate()
    test_draw_detection()
    test_uci_format()
    test_move_validation_backend_style()
    print("All chess edge-case tests passed.")
