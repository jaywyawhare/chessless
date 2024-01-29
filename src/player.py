class ChessPlayer:
    def __init__(self):
        pass

    def make_move(self, board):
        legal_moves = board.get_legal_moves()

        print("Available moves:")

        legal_moves.append("Quit (q)")

        for i, move in enumerate(legal_moves):
            print(f"{i + 1}. {move}")

        while True:
            try:
                choice = int(input("Enter the number of your move: "))
                if 1 <= choice <= len(legal_moves):
                    return legal_moves[choice - 1]

                else:
                    print("Invalid choice. Please enter a valid number.")
            except ValueError:
                print("Invalid input. Please enter a number.")

