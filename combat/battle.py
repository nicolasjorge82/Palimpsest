from combat.abilities import pass_action, place_action
from combat.ai import RandomEnemyAI
from combat.board import ENEMY, PLAYER, Board

DEFAULT_BLOCKERS = {(1, 1), (3, 1), (1, 3), (3, 3)}


class Battle:
    def __init__(self, turns_per_side: int = 6):
        self.turns_per_side = turns_per_side
        self.ai = RandomEnemyAI()
        self.board = Board(turns_per_side=turns_per_side, blocked_tiles=DEFAULT_BLOCKERS)

    def restart(self) -> None:
        self.board.reset(DEFAULT_BLOCKERS)

    def handle_player_move(self, x: int, y: int) -> dict[str, object]:
        if self.board.current_side != PLAYER or self.board.game_over:
            return {"success": False, "message": self.status_text()}
        result = self.board.apply_action(place_action(PLAYER, x, y))
        if result["success"]:
            self._play_enemy_turns()
        return result

    def end_player_turn(self) -> dict[str, object]:
        if self.board.current_side != PLAYER or self.board.game_over:
            return {"success": False, "message": self.status_text()}
        result = self.board.apply_action(pass_action(PLAYER))
        if result["success"]:
            self._play_enemy_turns()
        return result

    def status_text(self) -> str:
        if self.board.game_over:
            return self.board.last_message
        if self.board.current_side == PLAYER and not self.board.legal_moves(PLAYER):
            return "No legal moves. Press Space to pass."
        return self.board.last_message

    def score_text(self) -> str:
        scores = self.board.score()
        return f"Territory  Player {scores[PLAYER]}  Enemy {scores[ENEMY]}"

    def turn_text(self) -> str:
        player_turns = self.board.remaining_turns[PLAYER]
        enemy_turns = self.board.remaining_turns[ENEMY]
        active = self.board.current_side.title() if not self.board.game_over else "Final"
        return f"Turn  {active}   P:{player_turns}   E:{enemy_turns}"

    def _play_enemy_turns(self) -> None:
        while self.board.current_side == ENEMY and not self.board.game_over:
            action = self.ai.choose_action(self.board)
            result = self.board.apply_action(action)
            if not result["success"]:
                break