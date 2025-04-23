import os
import requests
import cairosvg
import pathlib


def download_pieces():
    pathlib.Path("assets/pieces").mkdir(parents=True, exist_ok=True)

    base_url = "https://raw.githubusercontent.com/lichess-org/lila/master/public/piece/cburnett"
    pieces = {"w": ["P", "N", "B", "R", "Q", "K"], "b": ["P", "N", "B", "R", "Q", "K"]}

    for color in pieces:
        for piece in pieces[color]:
            piece_name = piece if color == "w" else piece.lower()
            url = f"{base_url}/{color}{piece}.svg"
            output_path = f"assets/pieces/{color}{piece_name.lower()}.png"

            try:
                response = requests.get(url)
                if response.status_code == 200:
                    cairosvg.svg2png(
                        bytestring=response.content,
                        write_to=output_path,
                        output_width=200,
                        output_height=200,
                    )
                    print(f"Downloaded and converted: {output_path}")
                else:
                    print(f"Failed to download: {url}")
            except Exception as e:
                print(f"Error processing {url}: {e}")


if __name__ == "__main__":
    download_pieces()
