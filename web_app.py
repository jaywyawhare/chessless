from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from src.engine import WorstEngine
import chess
import os
from typing import Optional
import threading

app = Flask(
    __name__,
    template_folder="ui/templates",
    static_folder="ui/assets",
    static_url_path="",
)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


class GameState:
    def __init__(self):
        self.board = chess.Board()
        self.engine = WorstEngine(depth=2, max_time=2.0)
        self.player_color: Optional[bool] = None
    
    def set_depth(self, depth: int):
        # Give more time for higher depths
        max_time = 1.0 + (depth - 1) * 0.5
        self.engine = WorstEngine(depth=min(depth, 5), max_time=max_time)


game_state = GameState()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/assets/<path:filename>")
def serve_asset(filename):
    try:
        if filename.startswith("pieces/"):
            filename = filename.lower()
        return send_from_directory("ui/assets", filename)
    except Exception as e:
        app.logger.error(f"Error serving asset {filename}: {e}")
        return "", 404


def _game_outcome():
    if not game_state.board.is_game_over():
        return None
    if game_state.board.is_checkmate():
        return "checkmate"
    if game_state.board.is_stalemate():
        return "stalemate"
    if game_state.board.is_insufficient_material():
        return "draw_insufficient_material"
    if game_state.board.is_fifty_moves():
        return "draw_50_moves"
    if game_state.board.is_repetition():
        return "draw_repetition"
    return "draw"


@app.route("/api/game/status")
def game_status():
    return jsonify({
        "fen": game_state.board.fen(),
        "is_game_over": game_state.board.is_game_over(),
        "outcome": _game_outcome(),
        "is_check": game_state.board.is_check(),
        "turn": "white" if game_state.board.turn else "black",
        "player_color": "white" if game_state.player_color else "black",
        "moves": [move.uci() for move in game_state.board.legal_moves],
    })


@socketio.on("select_color")
def handle_color_selection(data):
    game_state.player_color = chess.WHITE if data["color"] == "white" else chess.BLACK
    if game_state.player_color == chess.BLACK:
        move = game_state.engine.get_worst_move(game_state.board)
        if move:
            game_state.board.push(move)
            emit("move_made", {"move": move.uci(), "fen": game_state.board.fen()})


def run_engine_and_emit():
    """Run engine move and emit complete response."""
    try:
        engine_move = game_state.engine.get_worst_move(game_state.board)
        if engine_move:
            game_state.board.push(engine_move)
        
        socketio.emit("engine_move", {
            "engine_move": engine_move.uci() if engine_move else None,
            "fen": game_state.board.fen(),
            "game_over": game_state.board.is_game_over(),
            "outcome": _game_outcome(),
            "check": game_state.board.is_check(),
            "moves": [m.uci() for m in game_state.board.legal_moves],
        })
    except Exception as e:
        app.logger.error(f"Engine error: {e}")


@socketio.on("move")
def handle_move(data):
    try:
        move_uci = data["move"]
        if len(move_uci) not in (4, 5):
            raise ValueError("Invalid move format")
        if move_uci[:2] == move_uci[2:4]:
            raise ValueError("Source and target squares must be different")

        move = chess.Move.from_uci(move_uci)
        if move not in game_state.board.legal_moves:
            raise ValueError("Illegal move")

        game_state.board.push(move)

        # Send immediate response with player's move
        emit("player_move", {
            "valid": True,
            "fen": game_state.board.fen(),
            "last_move": move_uci,
            "game_over": game_state.board.is_game_over(),
            "outcome": _game_outcome() if game_state.board.is_game_over() else None,
            "check": game_state.board.is_check(),
            "moves": [m.uci() for m in game_state.board.legal_moves],
        })

        # If game not over, run engine in background
        if not game_state.board.is_game_over():
            thread = threading.Thread(target=run_engine_and_emit)
            thread.start()
            
    except ValueError as e:
        emit("player_move", {"valid": False, "message": str(e)})
    except Exception as e:
        app.logger.error(f"Error handling move: {e}")
        emit("player_move", {"valid": False, "message": "Invalid move"})


@socketio.on("game_action")
def handle_game_action(data):
    action = data.get("action")
    if action == "flip":
        emit("board_update", {"action": "flip"})
    elif action == "undo":
        if len(game_state.board.move_stack) > 0:
            game_state.board.pop()
            if len(game_state.board.move_stack) > 0:
                game_state.board.pop()
            emit("board_update", {"action": "undo", "fen": game_state.board.fen()})
    elif action == "new_game":
        game_state.board = chess.Board()
        game_state.player_color = None
        emit("board_update", {"action": "new_game", "fen": game_state.board.fen()})


@socketio.on("set_depth")
def handle_set_depth(data):
    depth = data.get("depth", 2)
    game_state.set_depth(depth)
    emit("depth_updated", {"depth": depth})


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
