from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_from_directory,
    send_file,
    abort,
)
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from src.worst_engine import WorstEngine
import chess
import os

app = Flask(__name__, static_folder="assets", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


class GameState:
    def __init__(self):
        self.board = chess.Board()
        self.engine = WorstEngine(depth=3, max_time=5)
        self.player_color = None


game_state = GameState()


@app.route("/")
def index():
    return render_template("index.html") 


@app.route("/assets/<path:filename>")
def serve_asset(filename):
    try:
        if filename.startswith("pieces/"):
            filename = filename.lower()
        return send_from_directory("assets", filename)
    except Exception as e:
        app.logger.error(f"Error serving asset {filename}: {e}")
        return "", 404


@app.route("/api/game/status")
def game_status():
    return jsonify(
        {
            "fen": game_state.board.fen(),
            "is_game_over": game_state.board.is_game_over(),
            "is_check": game_state.board.is_check(),
            "turn": "white" if game_state.board.turn else "black",
            "player_color": "white" if game_state.player_color else "black",
            "moves": [move.uci() for move in game_state.board.legal_moves],
        }
    )


@socketio.on("select_color")
def handle_color_selection(data):
    game_state.player_color = chess.WHITE if data["color"] == "white" else chess.BLACK
    if game_state.player_color == chess.BLACK:
        move = game_state.engine.get_worst_move(game_state.board)
        if move:
            game_state.board.push(move)
            emit("move_made", {"move": move.uci(), "fen": game_state.board.fen()})


@socketio.on("move")
def handle_move(data):
    try:
        move_uci = data["move"]
        # Validate move format
        if len(move_uci) != 4:
            raise ValueError("Invalid move format")

        # Check if source and target squares are different
        if move_uci[:2] == move_uci[2:]:
            raise ValueError("Source and target squares must be different")

        move = chess.Move.from_uci(move_uci)
        if move not in game_state.board.legal_moves:
            raise ValueError("Illegal move")

        game_state.board.push(move)

        response = {
            "valid": True,
            "fen": game_state.board.fen(),
            "last_move": move_uci,
            "game_over": game_state.board.is_game_over(),
            "check": game_state.board.is_check(),
            "moves": [m.uci() for m in game_state.board.legal_moves],
        }

        # Engine response
        if not game_state.board.is_game_over():
            engine_move = game_state.engine.get_worst_move(game_state.board)
            if engine_move:
                game_state.board.push(engine_move)
                response.update(
                    {
                        "engine_move": engine_move.uci(),
                        "fen": game_state.board.fen(),
                        "moves": [m.uci() for m in game_state.board.legal_moves],
                    }
                )

        emit("move_response", response)
    except ValueError as e:
        emit("move_response", {"valid": False, "message": str(e)})
    except Exception as e:
        app.logger.error(f"Error handling move: {e}")
        emit("move_response", {"valid": False, "message": "Invalid move"})


@socketio.on("update_time")
def handle_time_update(data):
    try:
        new_time = min(30, max(1, int(data["time"])))
        game_state.engine.search.max_time = new_time
        emit("time_updated", {"time": new_time})
    except:
        emit("time_updated", {"time": game_state.engine.search.max_time})


@socketio.on("game_action")
def handle_game_action(data):
    action = data.get("action")
    if action == "flip":
        emit("board_update", {"action": "flip"})
    elif action == "undo":
        if len(game_state.board.move_stack) > 0:
            game_state.board.pop()
            emit("board_update", {"action": "undo", "fen": game_state.board.fen()})


if __name__ == "__main__":
    socketio.run(app, debug=True)
