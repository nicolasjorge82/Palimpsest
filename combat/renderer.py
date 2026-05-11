import math

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CardMaker, LineSegs, OrthographicLens, Point2, Point3, TextNode, TransparencyAttrib

from combat.battle import Battle
from combat.board import ENEMY, PLAYER


class CombatPrototype(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.battle = Battle()
        self.tile_size = 1.0
        self.board_origin = Point3(-2.5, -2.5, 0.0)
        self.hovered_tile: tuple[int, int] | None = None
        self.palette = {
            "background": (0.06, 0.08, 0.10, 1.0),
            "neutral": (0.66, 0.64, 0.56, 1.0),
            "player_tile": (0.43, 0.66, 0.63, 1.0),
            "enemy_tile": (0.70, 0.46, 0.44, 1.0),
            "player_token": (0.10, 0.86, 0.78, 1.0),
            "enemy_token": (0.93, 0.40, 0.34, 1.0),
            "blocked": (0.20, 0.18, 0.18, 1.0),
            "grid": (0.15, 0.16, 0.18, 1.0),
            "hover": (0.95, 0.91, 0.34, 0.35),
            "text": (0.95, 0.93, 0.88, 1.0),
        }
        self.tile_nodes: list[dict[str, object]] = []

        self._configure_scene()
        self._build_board_nodes()
        self._build_hud()
        self.refresh_scene()

        self.accept("mouse1", self.on_click)
        self.accept("space", self.on_pass)
        self.accept("r", self.on_restart)
        self.taskMgr.add(self._update_hover_task, "update-hover")

    def on_click(self) -> None:
        if self.hovered_tile is None:
            return
        x, y = self.hovered_tile
        self.battle.handle_player_move(x, y)
        self.refresh_scene()

    def on_pass(self) -> None:
        self.battle.end_player_turn()
        self.refresh_scene()

    def on_restart(self) -> None:
        self.battle.restart()
        self.refresh_scene()

    def refresh_scene(self) -> None:
        territory = self.battle.board.territory_map()
        for y in range(self.battle.board.size):
            for x in range(self.battle.board.size):
                entry = self.tile_nodes[y * self.battle.board.size + x]
                owner = self.battle.board.tile_owner(x, y)
                claimed = territory[y][x]
                is_blocked = self.battle.board.is_blocked(x, y)

                if is_blocked:
                    entry["base"].setColor(*self.palette["blocked"])
                    entry["block"].show()
                    entry["token"].hide()
                else:
                    entry["block"].hide()
                    entry["base"].setColor(*self._tile_color(owner, claimed))
                    if owner == PLAYER:
                        entry["token"].setColor(*self.palette["player_token"])
                        entry["token"].show()
                    elif owner == ENEMY:
                        entry["token"].setColor(*self.palette["enemy_token"])
                        entry["token"].show()
                    else:
                        entry["token"].hide()

        self.turn_label.setText(self.battle.turn_text())
        self.score_label.setText(self.battle.score_text())
        self.status_label.setText(self.battle.status_text())
        self._update_hover_node()

    def _configure_scene(self) -> None:
        self.setBackgroundColor(*self.palette["background"])
        lens = OrthographicLens()
        lens.setFilmSize(9.5, 8.0)
        lens.setNearFar(1, 100)
        self.cam.node().setLens(lens)
        self.camera.setPos(0, 0, 20)
        self.camera.setHpr(0, -90, 0)
        self.render.setLightOff()

    def _build_board_nodes(self) -> None:
        root = self.render.attachNewNode("board")
        self.board_root = root
        self.tile_nodes.clear()

        for y in range(self.battle.board.size):
            for x in range(self.battle.board.size):
                tile_node = root.attachNewNode(f"tile-{x}-{y}")
                tile_node.setPos(self.board_origin.x + x * self.tile_size, self.board_origin.y + y * self.tile_size, 0)

                base = self._make_card(tile_node, self.tile_size, 0.0, 0.96)
                token = self._make_card(tile_node, self.tile_size * 0.46, 0.03, 0.0)
                token.setPos(self.tile_size * 0.27, self.tile_size * 0.27, 0.03)

                block = self._make_block_marker(tile_node)
                self.tile_nodes.append({"base": base, "token": token, "block": block})

        grid = self._make_grid_lines()
        grid.reparentTo(root)

        self.hover_node = self._make_card(root, self.tile_size, 0.05, 0.98)
        self.hover_node.setTransparency(TransparencyAttrib.M_alpha)
        self.hover_node.setColor(*self.palette["hover"])
        self.hover_node.hide()

    def _build_hud(self) -> None:
        self.title_label = OnscreenText(
            text="PALIMPSEST / TACTICAL PROTOTYPE",
            pos=(-1.28, 0.92),
            scale=0.06,
            fg=self.palette["text"],
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.turn_label = OnscreenText(
            text="",
            pos=(-1.28, 0.82),
            scale=0.05,
            fg=self.palette["text"],
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.score_label = OnscreenText(
            text="",
            pos=(-1.28, 0.73),
            scale=0.05,
            fg=self.palette["text"],
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.status_label = OnscreenText(
            text="",
            pos=(-1.28, -0.90),
            scale=0.05,
            fg=self.palette["text"],
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.controls_label = OnscreenText(
            text="Click: place influence   Space: pass turn   R: restart battle",
            pos=(-1.28, -0.82),
            scale=0.045,
            fg=self.palette["text"],
            align=TextNode.ALeft,
        )

    def _make_card(self, parent, size: float, z_offset: float, inset_scale: float):
        maker = CardMaker("tile-card")
        inset = (1.0 - inset_scale) * size * 0.5
        maker.setFrame(inset, size - inset, inset, size - inset)
        node = parent.attachNewNode(maker.generate())
        node.setP(-90)
        node.setZ(z_offset)
        node.setTwoSided(True)
        return node

    def _make_block_marker(self, parent):
        lines = LineSegs()
        lines.setThickness(3)
        lines.setColor(*self.palette["grid"])
        inset = 0.18
        lines.moveTo(inset, inset, 0.06)
        lines.drawTo(self.tile_size - inset, self.tile_size - inset, 0.06)
        lines.moveTo(self.tile_size - inset, inset, 0.06)
        lines.drawTo(inset, self.tile_size - inset, 0.06)
        marker = parent.attachNewNode(lines.create())
        return marker

    def _make_grid_lines(self):
        lines = LineSegs()
        lines.setThickness(2)
        lines.setColor(*self.palette["grid"])
        size = self.battle.board.size * self.tile_size

        for index in range(self.battle.board.size + 1):
            offset = index * self.tile_size
            lines.moveTo(self.board_origin.x + offset, self.board_origin.y, 0.01)
            lines.drawTo(self.board_origin.x + offset, self.board_origin.y + size, 0.01)
            lines.moveTo(self.board_origin.x, self.board_origin.y + offset, 0.01)
            lines.drawTo(self.board_origin.x + size, self.board_origin.y + offset, 0.01)

        return self.render.attachNewNode(lines.create())

    def _update_hover_task(self, task):
        self.hovered_tile = self._mouse_to_tile()
        self._update_hover_node()
        return task.cont

    def _update_hover_node(self) -> None:
        if self.hovered_tile is None or self.battle.board.game_over or self.battle.board.current_side != PLAYER:
            self.hover_node.hide()
            return

        x, y = self.hovered_tile
        self.hover_node.setPos(self.board_origin.x + x * self.tile_size, self.board_origin.y + y * self.tile_size, 0.05)
        if self.battle.board.can_place(x, y):
            self.hover_node.setColor(*self.palette["hover"])
        else:
            self.hover_node.setColor(0.95, 0.40, 0.34, 0.25)
        self.hover_node.show()

    def _mouse_to_tile(self) -> tuple[int, int] | None:
        if not self.mouseWatcherNode.hasMouse():
            return None

        mouse = self.mouseWatcherNode.getMouse()
        near_point = Point3()
        far_point = Point3()
        if not self.camLens.extrude(Point2(mouse.x, mouse.y), near_point, far_point):
            return None

        near_world = self.render.getRelativePoint(self.cam, near_point)
        far_world = self.render.getRelativePoint(self.cam, far_point)
        delta = far_world - near_world
        if math.isclose(delta.z, 0.0):
            return None

        distance = -near_world.z / delta.z
        if distance < 0:
            return None

        world_point = near_world + delta * distance
        local_x = world_point.x - self.board_origin.x
        local_y = world_point.y - self.board_origin.y
        tile_x = int(math.floor(local_x / self.tile_size))
        tile_y = int(math.floor(local_y / self.tile_size))

        if not self.battle.board.in_bounds(tile_x, tile_y):
            return None
        return tile_x, tile_y

    def _tile_color(self, owner: str | None, claimed: str | None) -> tuple[float, float, float, float]:
        if owner == PLAYER:
            return self.palette["player_tile"]
        if owner == ENEMY:
            return self.palette["enemy_tile"]
        if claimed == PLAYER:
            return (0.55, 0.68, 0.63, 1.0)
        if claimed == ENEMY:
            return (0.72, 0.54, 0.50, 1.0)
        return self.palette["neutral"]