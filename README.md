# Chessless - The "Worst Move" Chess Engine

## Introduction

A chess engine written in Python that always plays the worst move on the board. Whether you're a beginner looking for a relaxed game or an experienced player seeking a unique challenge, Chessless is here to provide a lighthearted and amusing chess experience.

## Features

- Always Makes the Worst Move: Chessless is designed to choose the least optimal move in any given position, making it the perfect opponent for those who want to enjoy a more casual game of chess.

- User-Friendly Interface: Chessless provides a simple and intuitive interface for users to make their moves. It accepts standard algebraic notation for moves.

- Single-Player Mode: Play against Chessless as a single player for a fun and stress-free gaming experience.

## Requirements

- Python 3.x

## Installation

1. Clone the Chessless repository to your local machine:

    ```bash
    git clone https://github.com/jaywyawhare/chessless.git
    ```

1. Navigate to the Chessless directory:

    ```bash
    cd chessless
    ```

1. Run the setup script:

    ```bash
    bash setup.sh
    ```
1. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```
    
1. Run the Chessless engine:

    ```bash
    python chessless.py
    ```

## How to Play

1. Run the Chessless engine by following the [installation instructions](#installation).

1. Make your moves using standard algebraic notation. For example, if you want to move a pawn from e2 to e4, type e2e4.

1. Chessless will respond with the worst possible move.

1. Continue the game until checkmate, stalemate, or until you decide to end the game.

## Example Gameplay
    ```less
    Welcome to Chessless - The "Worst Move" Chess Engine!

    Current Board:

    8   r n b q k b n r
    7   p p p p p p p p
    6
    5
    4           P
    3
    2   P P P P   P P P
    1   R N B Q K B N R

    Enter your move (e.g., e2e4): e2e4
    ```

## Contributing

Contributions to Chessless are welcome! If you have ideas for improvements or new features, feel free to submit a pull request.

## License
This project is licensed under the [DBaJ-NC-CFL](./LICENCE.md).