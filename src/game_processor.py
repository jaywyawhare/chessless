import numpy as np
from src.utils import convert_algebraic_to_san, convert_fen_to_bitboard, serialize_position

class GameProcessor:
    def make_dataset(self, game):
        game = game.split(" ")[0:-1]
        game = " ".join(game)
        fen_list = convert_algebraic_to_san(game)
        dataset = []

        for fen in fen_list:
            try:
                serialized_position = serialize_position(fen)
                dataset.append((fen, serialized_position))
            except Exception as e:
                print(f"Error serializing position for FEN {fen}: {e}")
                continue  

        return dataset

    def process_game(self, file):
        games = []
        try:
            with open(file, "r") as f:
                game = f.read()
            for g in game.split("\n\n"):
                if g.startswith("1"):
                    games.append(g)
        except Exception as e:
            print(f"Error reading file: {file} - {e}")
        return games

    def process_file(self, file):
        processed_games = []
        games = self.process_game(file)
        for game in games:
            dataset = self.make_dataset(game)
            processed_games.extend(dataset)
        return processed_games
