import pygame
import chess
import sys
import os
from src.worst_engine import WorstEngine
import argparse


pygame.init()


WINDOW_SIZE = 600
BOARD_SIZE = 512
SQUARE_SIZE = BOARD_SIZE // 8
PIECE_SIZE = SQUARE_SIZE


LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (130, 151, 105)
SELECTED = (186, 202, 43)


class ChessGUI:
    def __init__(self, depth=3, max_time=5):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("ChessLess - The Worst Chess Engine")

        self.offset_x = (WINDOW_SIZE - BOARD_SIZE) // 2
        self.offset_y = (WINDOW_SIZE - BOARD_SIZE) // 2

        self.pieces = {}
        for color in ["w", "b"]:
            for piece in ["p", "n", "b", "r", "q", "k"]:
                img_path = os.path.join("assets", "pieces", f"{color}{piece}.png")
                try:
                    img = pygame.image.load(img_path)
                    self.pieces[f"{color}{piece}"] = pygame.transform.scale(
                        img, (PIECE_SIZE, PIECE_SIZE)
                    )
                except:
                    print(f"Error loading piece image: {img_path}")
                    sys.exit(1)

        self.board = chess.Board()
        self.engine = WorstEngine(depth=depth, max_time=max_time)
        self.selected_square = None
        self.player_color = None
        self.valid_moves = []

    def get_square_from_pos(self, pos):
        x, y = pos
        x = (x - self.offset_x) // SQUARE_SIZE
        y = (y - self.offset_y) // SQUARE_SIZE
        if 0 <= x < 8 and 0 <= y < 8:
            return chess.square(x, 7 - y)
        return None

    def get_pos_from_square(self, square):
        file_idx = chess.square_file(square)
        rank_idx = 7 - chess.square_rank(square)
        return (
            file_idx * SQUARE_SIZE + self.offset_x,
            rank_idx * SQUARE_SIZE + self.offset_y,
        )

    def draw_board(self):
        self.screen.fill((40, 40, 40))
        for rank in range(8):
            for file in range(8):
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        file * SQUARE_SIZE + self.offset_x,
                        rank * SQUARE_SIZE + self.offset_y,
                        SQUARE_SIZE,
                        SQUARE_SIZE,
                    ),
                )

    def draw_pieces(self):
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                color = "w" if piece.color else "b"
                piece_type = piece.symbol().lower()
                img = self.pieces[f"{color}{piece_type}"]
                pos = self.get_pos_from_square(square)
                self.screen.blit(img, pos)

    def draw_highlights(self):
        if self.selected_square is not None:
            pos = self.get_pos_from_square(self.selected_square)
            pygame.draw.rect(
                self.screen, SELECTED, (pos[0], pos[1], SQUARE_SIZE, SQUARE_SIZE), 3
            )

            for move in self.valid_moves:
                pos = self.get_pos_from_square(move.to_square)
                pygame.draw.rect(
                    self.screen,
                    HIGHLIGHT,
                    (pos[0], pos[1], SQUARE_SIZE, SQUARE_SIZE),
                    3,
                )

    def draw_game_end_state(self):
        font = pygame.font.Font(None, 36)
        result = self.board.result()
        if result == "1-0":
            text = "White Wins!"
        elif result == "0-1":
            text = "Black Wins!"
        else:
            text = "Draw!"

        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2))

        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        self.screen.blit(text_surface, text_rect)

    def draw(self):
        self.draw_board()
        self.draw_highlights()
        self.draw_pieces()
        if self.board.is_game_over():
            self.draw_game_end_state()
        pygame.display.flip()

    def choose_color(self):
        font = pygame.font.Font(None, 36)
        white_text = font.render("Play as White", True, (255, 255, 255))
        black_text = font.render("Play as Black", True, (255, 255, 255))
        time_text = font.render(
            f"Engine Time: {self.engine.max_time}s", True, (255, 255, 255)
        )
        time_up = font.render("+", True, (255, 255, 255))
        time_down = font.render("-", True, (255, 255, 255))

        while self.player_color is None:
            self.screen.fill((40, 40, 40))

            white_rect = white_text.get_rect(
                center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 50)
            )
            black_rect = black_text.get_rect(
                center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 50)
            )
            time_rect = time_text.get_rect(
                center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 120)
            )
            time_up_rect = time_up.get_rect(
                center=(WINDOW_SIZE // 2 + 100, WINDOW_SIZE // 2 - 120)
            )
            time_down_rect = time_down.get_rect(
                center=(WINDOW_SIZE // 2 - 100, WINDOW_SIZE // 2 - 120)
            )

            self.screen.blit(white_text, white_rect)
            self.screen.blit(black_text, black_rect)
            self.screen.blit(time_text, time_rect)
            self.screen.blit(time_up, time_up_rect)
            self.screen.blit(time_down, time_down_rect)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if white_rect.collidepoint(event.pos):
                        self.player_color = chess.WHITE
                    elif black_rect.collidepoint(event.pos):
                        self.player_color = chess.BLACK
                        move = self.engine.get_worst_move(self.board)
                        self.board.push(move)
                    elif time_up_rect.collidepoint(event.pos):
                        self.engine.max_time = min(30, self.engine.max_time + 1)
                        time_text = font.render(
                            f"Engine Time: {self.engine.max_time}s",
                            True,
                            (255, 255, 255),
                        )
                    elif time_down_rect.collidepoint(event.pos):
                        self.engine.max_time = max(1, self.engine.max_time - 1)
                        time_text = font.render(
                            f"Engine Time: {self.engine.max_time}s",
                            True,
                            (255, 255, 255),
                        )

    def run(self):
        self.choose_color()
        clock = pygame.time.Clock()
        running = True
        game_end_time = None

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()

                if not self.board.is_game_over():
                    if (
                        self.board.turn == self.player_color
                        and event.type == pygame.MOUSEBUTTONDOWN
                    ):
                        square = self.get_square_from_pos(event.pos)
                        if square is not None:
                            if self.selected_square is None:
                                piece = self.board.piece_at(square)
                                if piece and piece.color == self.player_color:
                                    self.selected_square = square
                                    self.valid_moves = [
                                        move
                                        for move in self.board.legal_moves
                                        if move.from_square == square
                                    ]
                            else:
                                move = chess.Move(self.selected_square, square)
                                if move in self.valid_moves:
                                    self.board.push(move)
                                    self.selected_square = None
                                    self.valid_moves = []
                                    if not self.board.is_game_over():
                                        engine_move = self.engine.get_worst_move(
                                            self.board
                                        )
                                        if engine_move:
                                            self.board.push(engine_move)
                                else:
                                    self.selected_square = None
                                    self.valid_moves = []

            if self.board.is_game_over():
                if game_end_time is None:
                    game_end_time = pygame.time.get_ticks()
                elif pygame.time.get_ticks() - game_end_time > 3000:
                    running = False

            self.draw()
            clock.tick(60)

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Play chess against the worst engine")
    parser.add_argument("--depth", type=int, default=3, help="Engine search depth")
    parser.add_argument(
        "--max-time",
        type=int,
        default=5,
        help="Maximum time to think per move (seconds)",
    )
    args = parser.parse_args()

    gui = ChessGUI(depth=args.depth, max_time=args.max_time)
    gui.run()


if __name__ == "__main__":
    main()
