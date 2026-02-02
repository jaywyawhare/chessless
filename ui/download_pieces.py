"""
Download chess piece images (cburnett set) as PNG into ui/assets/pieces/.
Requires: pip install -r ../requirements.txt (CairoSVG, requests).
Run from project root: python ui/download_pieces.py
"""
import pathlib
import requests


def download_pieces():
    try:
        import cairosvg
    except ModuleNotFoundError as e:
        raise SystemExit(
            "Missing dependency 'CairoSVG'. Install it with:\n"
            "  pip install -r requirements.txt\n"
        ) from e

    ui_dir = pathlib.Path(__file__).resolve().parent
    pieces_dir = ui_dir / "assets" / "pieces"
    pieces_dir.mkdir(parents=True, exist_ok=True)

    base_url = "https://raw.githubusercontent.com/lichess-org/lila/master/public/piece/cburnett"
    pieces = {"w": ["P", "N", "B", "R", "Q", "K"], "b": ["P", "N", "B", "R", "Q", "K"]}

    for color in pieces:
        for piece in pieces[color]:
            piece_name = piece if color == "w" else piece.lower()
            url = f"{base_url}/{color}{piece}.svg"
            output_path = pieces_dir / f"{color}{piece_name.lower()}.png"

            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    cairosvg.svg2png(
                        bytestring=response.content,
                        write_to=str(output_path),
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
