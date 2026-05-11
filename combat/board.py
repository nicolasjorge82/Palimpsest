from collections import deque

from combat.abilities import PASS, PLACE, Action

PLAYER = "player"
ENEMY = "enemy"
SIDES = (PLAYER, ENEMY)


class Board:
    def __init__(self, size: int = 5, turns_per_side: int = 6, blocked_tiles: set[tuple[int, int]] | None = None):
        self.size = size
        self.turns_per_side = turns_per_side
        self.reset(blocked_tiles or set())

    def reset(self, blocked_tiles: set[tuple[int, int]] | None = None) -> None:
        self.blocked_tiles = set(blocked_tiles or set())
        self.grid = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.remaining_turns = {PLAYER: self.turns_per_side, ENEMY: self.turns_per_side}
        self.current_side = PLAYER
        self.game_over = False
        self.last_message = "Claim territory. Surround enemy influence to remove it."

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def is_blocked(self, x: int, y: int) -> bool:
        return (x, y) in self.blocked_tiles

    def tile_owner(self, x: int, y: int) -> str | None:
        if not self.in_bounds(x, y) or self.is_blocked(x, y):
            return None
        return self.grid[y][x]

    def can_place(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and not self.is_blocked(x, y) and self.grid[y][x] is None

    def legal_moves(self, side: str | None = None) -> list[tuple[int, int]]:
        active_side = side or self.current_side
        if self.game_over or self.remaining_turns[active_side] <= 0:
            return []

        moves: list[tuple[int, int]] = []
        for y in range(self.size):
            for x in range(self.size):
                if self.can_place(x, y):
                    moves.append((x, y))
        return moves

    def apply_action(self, action: Action) -> dict[str, object]:
        if self.game_over:
            return {"success": False, "captured": 0, "message": "Battle is over."}
        if action.side != self.current_side:
            return {"success": False, "captured": 0, "message": "It is not that side's turn."}
        if self.remaining_turns[action.side] <= 0:
            return {"success": False, "captured": 0, "message": "That side has no turns left."}
        if action.kind == PASS:
            return self._finish_turn(0, f"{action.side.title()} passed.")
        if action.kind != PLACE or action.target is None:
            return {"success": False, "captured": 0, "message": "Unknown action."}

        x, y = action.target
        if not self.can_place(x, y):
            return {"success": False, "captured": 0, "message": "Illegal move."}

        self.grid[y][x] = action.side
        captured = self._capture_adjacent_groups(x, y, action.side)
        if not self._group_has_liberties(x, y) and captured == 0:
            self.grid[y][x] = None
            return {"success": False, "captured": 0, "message": "Move has no liberties."}

        message = f"{action.side.title()} placed influence at {x + 1},{y + 1}."
        if captured:
            message = f"{message} Captured {captured}."
        return self._finish_turn(captured, message)

    def territory_map(self) -> list[list[str | None]]:
        territory = [[None for _ in range(self.size)] for _ in range(self.size)]
        seen: set[tuple[int, int]] = set()

        for y in range(self.size):
            for x in range(self.size):
                if self.is_blocked(x, y):
                    territory[y][x] = "blocked"
                elif self.grid[y][x] in SIDES:
                    territory[y][x] = self.grid[y][x]

        for y in range(self.size):
            for x in range(self.size):
                if territory[y][x] is not None or (x, y) in seen:
                    continue

                region: list[tuple[int, int]] = []
                border_owners: set[str] = set()
                touches_edge = False
                queue = deque([(x, y)])
                seen.add((x, y))

                while queue:
                    cx, cy = queue.popleft()
                    region.append((cx, cy))
                    if cx in (0, self.size - 1) or cy in (0, self.size - 1):
                        touches_edge = True
                    for nx, ny in self._neighbors(cx, cy):
                        if self.is_blocked(nx, ny):
                            continue
                        owner = self.grid[ny][nx]
                        if owner in SIDES:
                            border_owners.add(owner)
                            continue
                        if (nx, ny) not in seen:
                            seen.add((nx, ny))
                            queue.append((nx, ny))

                owner = next(iter(border_owners)) if len(border_owners) == 1 and not touches_edge else None
                for rx, ry in region:
                    territory[ry][rx] = owner

        return territory

    def score(self) -> dict[str, int]:
        totals = {PLAYER: 0, ENEMY: 0}
        for row in self.territory_map():
            for cell in row:
                if cell in totals:
                    totals[cell] += 1
        return totals

    def winner(self) -> str | None:
        scores = self.score()
        if scores[PLAYER] == scores[ENEMY]:
            return None
        return PLAYER if scores[PLAYER] > scores[ENEMY] else ENEMY

    def _finish_turn(self, captured: int, message: str) -> dict[str, object]:
        self.remaining_turns[self.current_side] -= 1
        self.last_message = message
        if self._should_end_battle():
            self.game_over = True
            scores = self.score()
            victor = self.winner()
            if victor is None:
                self.last_message = f"Draw. Player {scores[PLAYER]} - Enemy {scores[ENEMY]}."
            else:
                self.last_message = f"{victor.title()} controls more territory: {scores[PLAYER]} - {scores[ENEMY]}."
        else:
            self.current_side = self._next_side()
        return {"success": True, "captured": captured, "message": self.last_message}

    def _should_end_battle(self) -> bool:
        if all(turns <= 0 for turns in self.remaining_turns.values()):
            return True
        return not self.legal_moves(PLAYER) and not self.legal_moves(ENEMY)

    def _next_side(self) -> str:
        other_side = PLAYER if self.current_side == ENEMY else ENEMY
        if self.remaining_turns[other_side] > 0:
            return other_side
        return self.current_side

    def _capture_adjacent_groups(self, x: int, y: int, side: str) -> int:
        enemy_side = PLAYER if side == ENEMY else ENEMY
        captured = 0
        visited: set[tuple[int, int]] = set()
        for nx, ny in self._neighbors(x, y):
            if (nx, ny) in visited or self.grid[ny][nx] != enemy_side:
                continue
            group, liberties = self._collect_group(nx, ny)
            visited.update(group)
            if liberties:
                continue
            for gx, gy in group:
                self.grid[gy][gx] = None
            captured += len(group)
        return captured

    def _group_has_liberties(self, x: int, y: int) -> bool:
        _, liberties = self._collect_group(x, y)
        return bool(liberties)

    def _collect_group(self, x: int, y: int) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        owner = self.grid[y][x]
        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        queue = deque([(x, y)])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in group:
                continue
            group.add((cx, cy))
            for nx, ny in self._neighbors(cx, cy):
                if self.is_blocked(nx, ny):
                    continue
                neighbor = self.grid[ny][nx]
                if neighbor is None:
                    liberties.add((nx, ny))
                elif neighbor == owner and (nx, ny) not in group:
                    queue.append((nx, ny))

        return group, liberties

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        points = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        return [(nx, ny) for nx, ny in points if self.in_bounds(nx, ny)]