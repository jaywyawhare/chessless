# Chessless - The "Worst" Chess Engine

## Introduction

Chessless is a chess engine written in Python that explores the concept of using Stockfish to evaluate random FEN positions. The engine converts board representations into 64-bit unsigned integers, focusing solely on six features: Pawn, Rook, Knight, Bishop, Queen, and King.

## Requirements

- Python 3.x

## Installation

1. Clone the Chessless repository to your local machine:

    ```bash
    git clone https://github.com/jaywyawhare/chessless.git
    ```

2. Navigate to the Chessless directory:

    ```bash
    cd chessless
    ```

3. Run the setup script:

    ```bash
    bash setup.sh
    ```

4. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

After installation, you can run the script with the following command:

```bash
python main.py
```

You can also provide a FEN string as an argument to evaluate specific positions.

## Features

- Converts chess board representations to a 64-bit integer format.
- Trains on a limited feature set focusing on basic chess pieces.

## Contributing

Contributions to Chessless are welcome! If you have ideas for improvements or new features, feel free to submit a pull request.

## License

This project is licensed under the [DBaJ-NC-CFL](./LICENCE.md).

---

Special thanks to George Hotz's [Twitch Stream](https://www.twitch.tv/georgehotz) and Google DeepMind's [Searchless Chess](https://github.com/google-deepmind/searchless_chess) for inspiration!
