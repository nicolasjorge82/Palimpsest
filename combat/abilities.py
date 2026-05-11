from dataclasses import dataclass

PLACE = "place"
PASS = "pass"


@dataclass(frozen=True)
class Action:
    side: str
    kind: str
    target: tuple[int, int] | None = None


def place_action(side: str, x: int, y: int) -> Action:
    return Action(side=side, kind=PLACE, target=(x, y))


def pass_action(side: str) -> Action:
    return Action(side=side, kind=PASS)