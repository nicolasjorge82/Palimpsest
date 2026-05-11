import random

from combat.abilities import Action, pass_action, place_action


class RandomEnemyAI:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_action(self, board) -> Action:
        moves = board.legal_moves(board.current_side)
        if not moves:
            return pass_action(board.current_side)
        x, y = self.rng.choice(moves)
        return place_action(board.current_side, x, y)