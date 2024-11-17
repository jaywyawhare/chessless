import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from src.game_processor import GameProcessor
import pandas as pd

def main():
    processor = GameProcessor()

    files = [
        f"data/games/Lichess Elite Database/{file}"
        for file in os.listdir("data/games/Lichess Elite Database")
        if file.endswith(".pgn")
    ]

    files.sort(key=lambda x: os.path.getsize(x), reverse=False)

    files = files[:10]  

    all_processed_games = []

    num_workers = (os.cpu_count() - 1) or 1  
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for processed_games in tqdm(
            executor.map(processor.process_file, files),
            total=len(files),
            desc="Processing files",
        ):
            all_processed_games.extend(processed_games)

    data = [{"current_fen": fen, "serialized_board": serialized_board} for fen, serialized_board in all_processed_games]

    df = pd.DataFrame(data)
    print(len(df))
    df.to_csv("data/processed_games.csv", index=False)
    print("Disk size:", os.path.getsize("data/processed_games.csv"))

if __name__ == "__main__":
    main()
