import torch
import torch.nn as nn


class ChessModel(nn.Module):
    def __init__(self):
        super(ChessModel, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(773, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

    def forward(self, x):
        # Invert the evaluation to favor bad positions
        return -self.network(x)

    def evaluate_position(self, position):
        with torch.no_grad():
            evaluation = self.forward(position)
            return evaluation.item()

    def get_worst_move(self, positions):
        """
        Select the worst move by finding position with lowest evaluation
        positions: List of candidate position tensors
        """
        evaluations = []
        for pos in positions:
            eval_score = self.evaluate_position(pos)
            evaluations.append(eval_score)

        # Get the position with lowest (worst) evaluation
        worst_idx = evaluations.index(min(evaluations))
        return worst_idx
