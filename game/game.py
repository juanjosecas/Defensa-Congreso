import random
import yaml
import pygame

from game.entities import Attacker, SecurityUnit, Barrier
from game.events import EventSystem
from game.map import CongressMap


class Game:
    def __init__(self, config_file):
        self.config_file = config_file
        with open(config_file, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        pygame.init()
        self.width = int(self.cfg["screen"]["width"])
        self.height = int(self.cfg["screen"]["height"])
        self.fps = int(self.cfg["screen"]["fps"])
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Defensa del Congreso - Operativo Caotico")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("Arial", 19)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.tiny_font = pygame.font.SysFont("Arial", 11)

        self.map = CongressMap(self.cfg["map"])

        ev_cfg = self.cfg.get("event_system", {})
        self.events = EventSystem(
            self.cfg.get("events", []),
            ev_cfg.get("min_delay", 18),
            ev_cfg.get("max_delay", 32),
        )

        self.attackers = []
        self.security_units = []
        self.barriers = []
        self.effects = []
        self.selected_units = []

        self.reserves = dict(self.cfg["reserves"])
        self.placement_mode = "infanteria"

        self.invasion_pressure = 0.0
        self.survival_time = 0.0
        self.preparation_time = float(self.cfg["game"].get("preparation_time", 12))
        self.game_over = False
        self.paused = False
        self.time_scale = 1.0

        self.wave_index = 0
        self.wave_running = False
        self.wave_queue = []
        self.spawn_timer = 0.0
        self.next_wave_timer = 0.0

        self.event_message = "Prepare el operativo."
        self.event_message_timer = 4.0

        self.attacker_uid = 0
        self.security_uid = 0

        self.selection_start = None
        self.selection_current = None
        self.dragging_selection = False

        self.cordon_mode = False
        self.cordon_start = None

        self.reinforcements = list(self.cfg.get("reinforcements", []))
        self.reinforcement_index = 0

        self.sector_integrity = {
            name: 100.0 for name in self.map.sectors
        }

        self.stats = {
            "detained": 0,
            "fled": 0,
            "barriers_broken": 0,
            "breaches": 0,
        }

    def begin_wave(self):
        wave = self.cfg["waves"][self.wave_index % len(self.cfg["waves"])]
        escalation = 1 + self.wave_index // len(self.cfg["waves"])
        queue = []

        for kind, count in wave["composition"].items():
            queue.extend([kind] * int(count * escalation))

        random.shuffle(queue)
        self.wave_queue = queue
        self.spawn_timer = 0.0
        self.wave_running = True

    def spawn_attacker(self, kind):
        spawn = random.choice(self.cfg["spawn_points"])
        pos = pygame.Vector2(spawn["pos"])
        pos.y += random.randint(-16, 16)

        route = self.cfg["routes"][spawn["route"]]

        self.attacker_uid += 1
        self.attackers.append(
            Attacker(
                pos,
                kind,
                self.cfg["attackers"][kind],
                route,
                self.attacker_uid,
            )
        )

    def deploy(self, pos):
        point = pygame.Vector2(pos)

        if self.placement_mode == "barrier":
            if self.reserves.get("barrier", 0) <= 0:
                return
            if not self.map.can_enter(point, "attacker"):
                return

            self.barriers.append(Barrier(point, self.cfg["barrier"]))
            self.reserves["barrier"] -= 1
            return

        if self.reserves.get(self.placement_mode, 0) <= 0:
            return

        unit_cfg = self.cfg["security"][self.placement_mode]
        terrain_mode = (
            "motorized"
            if unit_cfg.get("movement_terrain") == "street_only"
            else "foot"
        )

        point = self.map.nearest_valid_point(point, terrain_mode)
        if point is None:
            return

        self.security_uid += 1
        unit = SecurityUnit(
            point,
            self.placement_mode,
            unit_cfg,
            self.security_uid,
        )
        self.security_units.append(unit)
        self.reserves[self.placement_mode] -= 1

    def clear_selection(self):
        for unit in self.security_units:
            unit.selected = False
        self.selected_units = []

    def select_at(self, pos, additive=False):
        point = pygame.Vector2(pos)
        candidates = [
            unit
            for unit in self.security_units
            if unit.pos.distance_to(point) <= unit.radius + 8
        ]

        if not additive:
            self.clear_selection()

        if not candidates:
            return False

        unit = min(candidates, key=lambda item: item.pos.distance_to(point))
        unit.selected = True

        if unit not in self.selected_units:
            self.selected_units.append(unit)

        return True

    def select_rect(self, start, end, additive=False):
        if not additive:
            self.clear_selection()

        x1, x2 = sorted((start[0], end[0]))
        y1, y2 = sorted((start[1], end[1]))
        rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)

        for unit in self.security_units:
            if rect.collidepoint(unit.pos.x, unit.pos.y):
                unit.selected = True
                if unit not in self.selected_units:
                    self.selected_units.append(unit)

    def order_move(self, pos):
        if not self.selected_units:
            return

        target = pygame.Vector2(pos)
        spacing = 24
        n = len(self.selected_units)

        for i, unit in enumerate(self.selected_units):
            offset = pygame.Vector2(
                (i - (n - 1) / 2) * spacing,
                0,
            )
            desired = target + offset
            terrain_mode = (
                "motorized"
                if unit.movement_terrain == "street_only"
                else "foot"
            )
            valid = self.map.nearest_valid_point(desired, terrain_mode)
            if valid is not None:
                unit.move_to(valid)

    def hold_selected(self):
        for unit in self.selected_units:
            unit.hold()

    def begin_cordon(self):
        if not self.selected_units:
            return
        self.cordon_mode = True
        self.cordon_start = None
        self.event_message = "Cordon: marque inicio y fin."
        self.event_message_timer = 3.0

    def place_cordon(self, start, end):
        if not self.selected_units:
            return

        start = pygame.Vector2(start)
        end = pygame.Vector2(end)

        if len(self.selected_units) == 1:
            targets = [start]
        else:
            targets = [
                start.lerp(end, i / (len(self.selected_units) - 1))
                for i in range(len(self.selected_units))
            ]

        for unit, target in zip(self.selected_units, targets):
            terrain_mode = (
                "motorized"
                if unit.movement_terrain == "street_only"
                else "foot"
            )
            valid = self.map.nearest_valid_point(target, terrain_mode, search_radius=60)
            if valid is not None:
                unit.move_to(valid)

        self.cordon_mode = False
        self.cordon_start = None
        self.event_message = "Cordon desplegado."
        self.event_message_timer = 2.0

    def update_wave(self, dt):
        if self.preparation_time > 0:
            self.preparation_time -= dt
            return

        if not self.wave_running:
            self.next_wave_timer -= dt
            if self.next_wave_timer <= 0:
                self.begin_wave()
            return

        wave = self.cfg["waves"][self.wave_index % len(self.cfg["waves"])]

        if self.wave_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_attacker(self.wave_queue.pop())
                self.spawn_timer = float(wave["interval"])

        elif not any(attacker.alive for attacker in self.attackers):
            self.wave_running = False
            self.wave_index += 1
            self.next_wave_timer = max(2.0, 7.0 - self.wave_index * 0.25)

    def handle_event(self, event):
        if not event:
            return

        self.event_message = event["message"]
        self.event_message_timer = 5.5

        for kind, count in event.get("composition", {}).items():
            self.wave_queue.extend([kind] * int(count))

        random.shuffle(self.wave_queue)

        if event.get("pressure"):
            self.invasion_pressure += float(event["pressure"])

    def update_reinforcements(self):
        while self.reinforcement_index < len(self.reinforcements):
            item = self.reinforcements[self.reinforcement_index]
            if self.survival_time < float(item["time"]):
                break

            for kind, count in item.get("add", {}).items():
                self.reserves[kind] = self.reserves.get(kind, 0) + int(count)

            self.event_message = item.get(
                "message",
                "Llegaron refuerzos.",
            )
            self.event_message_timer = 5.0
            self.reinforcement_index += 1

    def update_sector_pressure(self, dt):
        damage_rate = float(self.cfg["game"].get("sector_damage_rate", 2.8))
        recovery_rate = float(self.cfg["game"].get("sector_recovery_rate", 0.6))

        for name, rect in self.map.sectors.items():
            attackers = [
                attacker
                for attacker in self.attackers
                if attacker.alive and rect.collidepoint(attacker.pos.x, attacker.pos.y)
            ]

            if attackers:
                local_pressure = sum(
                    max(0.3, attacker.breach_power / 8.0)
                    for attacker in attackers
                )
                self.sector_integrity[name] -= local_pressure * damage_rate * dt
            else:
                self.sector_integrity[name] += recovery_rate * dt

            self.sector_integrity[name] = max(
                0.0,
                min(100.0, self.sector_integrity[name]),
            )

            if self.sector_integrity[name] <= 0:
                self.invasion_pressure += float(
                    self.cfg["game"].get("sector_breach_pressure", 0.9)
                ) * dt

    def update(self, dt):
        if self.paused or self.game_over:
            return

        dt *= self.time_scale

        self.survival_time += dt
        self.event_message_timer = max(0.0, self.event_message_timer - dt)

        self.update_wave(dt)
        self.update_reinforcements()
        self.handle_event(self.events.update(dt))

        for attacker in self.attackers:
            attacker.update(
                dt,
                self.barriers,
                self.security_units,
                self.map,
            )

            if attacker.reached_goal:
                self.invasion_pressure += attacker.breach_power
                self.stats["breaches"] += 1
                attacker.reached_goal = False

        for unit in self.security_units:
            affected = unit.update(
                dt,
                self.attackers,
                self.map,
            )

            if affected and unit.effect_type != "attract":
                for target in affected[:5]:
                    self.effects.append(
                        [
                            pygame.Vector2(unit.pos),
                            pygame.Vector2(target.pos),
                            0.08,
                        ]
                    )

        for attacker in self.attackers:
            if not attacker.alive:
                if getattr(attacker, "detained", False):
                    self.stats["detained"] += 1
                elif getattr(attacker, "fled", False):
                    self.stats["fled"] += 1

        previous_barriers = len(self.barriers)
        self.attackers = [attacker for attacker in self.attackers if attacker.alive]
        self.barriers = [barrier for barrier in self.barriers if barrier.alive]
        self.stats["barriers_broken"] += previous_barriers - len(self.barriers)

        self.update_sector_pressure(dt)

        for effect in self.effects:
            effect[2] -= dt

        self.effects = [
            effect for effect in self.effects
            if effect[2] > 0
        ]

        if self.invasion_pressure >= 100:
            self.invasion_pressure = 100
            self.game_over = True
            self.event_message = "El Congreso fue invadido."

    def draw_selection_box(self):
        if not self.dragging_selection:
            return

        if self.selection_start is None or self.selection_current is None:
            return

        x1, x2 = sorted(
            (self.selection_start[0], self.selection_current[0])
        )
        y1, y2 = sorted(
            (self.selection_start[1], self.selection_current[1])
        )

        rect = pygame.Rect(
            x1,
            y1,
            x2 - x1,
            y2 - y1,
        )

        overlay = pygame.Surface(
            (max(1, rect.width), max(1, rect.height)),
            pygame.SRCALPHA,
        )
        overlay.fill((80, 130, 220, 38))
        self.screen.blit(overlay, rect.topleft)
        pygame.draw.rect(self.screen, (70, 120, 220), rect, 1)

    def draw_cordon_preview(self):
        if not self.cordon_mode or self.cordon_start is None:
            return

        pygame.draw.line(
            self.screen,
            (255, 210, 70),
            self.cordon_start,
            pygame.mouse.get_pos(),
            2,
        )

    def draw_sector_ui(self):
        x = self.width - 250
        y = 94

        for name, value in self.sector_integrity.items():
            label = self.tiny_font.render(
                f"{name}: {value:05.1f}%",
                True,
                (55, 55, 55),
            )
            self.screen.blit(label, (x, y))

            pygame.draw.rect(
                self.screen,
                (70, 70, 70),
                (x + 105, y + 2, 110, 7),
            )
            pygame.draw.rect(
                self.screen,
                (80, 170, 90),
                (x + 105, y + 2, int(110 * value / 100), 7),
            )
            y += 16

    def draw_ui(self):
        pygame.draw.rect(
            self.screen,
            (35, 40, 48),
            (0, 0, self.width, 88),
        )

        mins = int(self.survival_time // 60)
        secs = int(self.survival_time % 60)
        prep = max(0, int(self.preparation_time))

        status = (
            f"Tiempo {mins:02d}:{secs:02d}   "
            f"Presion {self.invasion_pressure:05.1f}%   "
            f"Oleada {self.wave_index + 1}   "
            f"Velocidad x{self.time_scale:g}"
        )
        self.screen.blit(
            self.font.render(status, True, (240, 240, 240)),
            (14, 8),
        )

        reserve_text = "  ".join(
            f"{key}:{value}"
            for key, value in self.reserves.items()
        )

        self.screen.blit(
            self.tiny_font.render(
                "Reservas  " + reserve_text,
                True,
                (210, 215, 220),
            ),
            (14, 35),
        )

        controls = (
            "[1-6] despliegue  drag: seleccionar  RMB: mover  "
            "[C] cordon  [H] mantener  [[]/[]] velocidad  [P] pausa  [R] reset"
        )

        self.screen.blit(
            self.small_font.render(
                controls,
                True,
                (205, 210, 215),
            ),
            (14, 54),
        )

        mode = self.cfg["security"].get(
            self.placement_mode,
            {},
        ).get(
            "label",
            "Valla",
        )

        self.screen.blit(
            self.small_font.render(
                f"Despliegue: {mode}   Seleccionadas: {len(self.selected_units)}",
                True,
                (255, 220, 120),
            ),
            (14, 72),
        )

        if prep > 0:
            txt = self.font.render(
                f"PREPARACION: {prep}s",
                True,
                (150, 40, 40),
            )
            self.screen.blit(
                txt,
                txt.get_rect(center=(self.width // 2, 108)),
            )

        if self.event_message_timer > 0 or self.game_over:
            txt = self.font.render(
                self.event_message,
                True,
                (120, 35, 35),
            )
            self.screen.blit(
                txt,
                txt.get_rect(center=(self.width // 2, 132)),
            )

        stats = (
            f"Detenidos {self.stats['detained']}   "
            f"Huyeron {self.stats['fled']}   "
            f"Vallas rotas {self.stats['barriers_broken']}   "
            f"Brechas {self.stats['breaches']}"
        )

        self.screen.blit(
            self.tiny_font.render(
                stats,
                True,
                (70, 70, 70),
            ),
            (14, 96),
        )

        if self.game_over:
            result = self.font.render(
                f"OPERATIVO FINALIZADO - resistio {mins:02d}:{secs:02d} - R para reiniciar",
                True,
                (165, 25, 25),
            )
            self.screen.blit(
                result,
                result.get_rect(center=(self.width // 2, 160)),
            )

    def draw(self):
        self.map.draw(self.screen, self.tiny_font)
        mouse = pygame.Vector2(pygame.mouse.get_pos())

        for barrier in self.barriers:
            barrier.draw(self.screen)

        for unit in self.security_units:
            unit.draw(
                self.screen,
                self.tiny_font,
                show_range=(
                    mouse.distance_to(unit.pos) < 28
                    or unit.selected
                ),
            )

        for attacker in self.attackers:
            attacker.draw(
                self.screen,
                self.tiny_font,
            )

        for start, end, _ in self.effects:
            pygame.draw.line(
                self.screen,
                (50, 50, 50),
                start,
                end,
                2,
            )

        self.draw_selection_box()
        self.draw_cordon_preview()
        self.draw_sector_ui()
        self.draw_ui()

        pygame.display.flip()

    def reset(self):
        self.__init__(self.config_file)

    def run(self):
        running = True

        while running:
            raw_dt = self.clock.tick(self.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    key_modes = {
                        pygame.K_1: "infanteria",
                        pygame.K_2: "goma",
                        pygame.K_3: "hidrante",
                        pygame.K_4: "motorizada",
                        pygame.K_5: "infiltrado",
                        pygame.K_6: "barrier",
                    }

                    if event.key in key_modes:
                        self.placement_mode = key_modes[event.key]

                    elif event.key == pygame.K_c:
                        self.begin_cordon()

                    elif event.key == pygame.K_h:
                        self.hold_selected()

                    elif event.key == pygame.K_LEFTBRACKET:
                        self.time_scale = max(
                            0.5,
                            self.time_scale / 2,
                        )

                    elif event.key == pygame.K_RIGHTBRACKET:
                        self.time_scale = min(
                            4.0,
                            self.time_scale * 2,
                        )

                    elif event.key == pygame.K_p:
                        self.paused = not self.paused

                    elif event.key == pygame.K_r:
                        self.reset()

                    elif event.key == pygame.K_ESCAPE:
                        self.cordon_mode = False
                        self.cordon_start = None
                        self.clear_selection()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.pos[1] <= 88:
                        continue

                    if event.button == 1:
                        if self.cordon_mode:
                            if self.cordon_start is None:
                                self.cordon_start = pygame.Vector2(event.pos)
                            else:
                                self.place_cordon(
                                    self.cordon_start,
                                    event.pos,
                                )
                            continue

                        self.selection_start = event.pos
                        self.selection_current = event.pos
                        self.dragging_selection = True

                    elif event.button == 3:
                        self.order_move(event.pos)

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_selection:
                        self.selection_current = event.pos

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button != 1 or not self.dragging_selection:
                        continue

                    self.dragging_selection = False
                    self.selection_current = event.pos

                    start = pygame.Vector2(self.selection_start)
                    end = pygame.Vector2(self.selection_current)
                    distance = start.distance_to(end)
                    additive = bool(
                        pygame.key.get_mods() & pygame.KMOD_SHIFT
                    )

                    if distance >= 8:
                        self.select_rect(
                            self.selection_start,
                            self.selection_current,
                            additive=additive,
                        )
                    else:
                        selected = self.select_at(
                            event.pos,
                            additive=additive,
                        )

                        if not selected and not additive:
                            self.clear_selection()
                            self.deploy(event.pos)

                    self.selection_start = None
                    self.selection_current = None

            self.update(raw_dt)
            self.draw()

        pygame.quit()
