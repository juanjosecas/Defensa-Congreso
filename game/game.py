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

        self.wave_index = 0
        self.wave_running = False
        self.wave_queue = []
        self.spawn_timer = 0.0
        self.next_wave_timer = 0.0
        self.event_message = "Prepare el operativo."
        self.event_message_timer = 4.0

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
        self.attackers.append(Attacker(pos, kind, self.cfg["attackers"][kind], route))

    def deploy(self, pos):
        if self.placement_mode == "barrier":
            if self.reserves.get("barrier", 0) <= 0:
                return
            self.barriers.append(Barrier(pos, self.cfg["barrier"]))
            self.reserves["barrier"] -= 1
            return

        if self.reserves.get(self.placement_mode, 0) <= 0:
            return
        unit = SecurityUnit(pos, self.placement_mode, self.cfg["security"][self.placement_mode])
        self.security_units.append(unit)
        self.reserves[self.placement_mode] -= 1

    def select_at(self, pos, additive=False):
        point = pygame.Vector2(pos)
        candidates = [u for u in self.security_units if u.pos.distance_to(point) <= u.radius + 8]
        if not additive:
            for unit in self.security_units:
                unit.selected = False
            self.selected_units = []
        if candidates:
            unit = min(candidates, key=lambda u: u.pos.distance_to(point))
            unit.selected = True
            if unit not in self.selected_units:
                self.selected_units.append(unit)
            return True
        return False

    def order_move(self, pos):
        if not self.selected_units:
            return
        target = pygame.Vector2(pos)
        spacing = 24
        n = len(self.selected_units)
        for i, unit in enumerate(self.selected_units):
            offset = pygame.Vector2((i - (n - 1) / 2) * spacing, 0)
            unit.move_to(target + offset)

    def hold_selected(self):
        for unit in self.selected_units:
            unit.hold()

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
        elif not any(a.alive for a in self.attackers):
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

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.survival_time += dt
        self.event_message_timer = max(0.0, self.event_message_timer - dt)
        self.update_wave(dt)
        self.handle_event(self.events.update(dt))

        for attacker in self.attackers:
            attacker.update(dt, self.barriers, self.security_units)
            if attacker.reached_goal:
                self.invasion_pressure += attacker.breach_power
                attacker.reached_goal = False

        for unit in self.security_units:
            affected = unit.update(dt, self.attackers)
            if affected and unit.effect_type != "attract":
                for target in affected[:5]:
                    self.effects.append([pygame.Vector2(unit.pos), pygame.Vector2(target.pos), 0.08])

        self.attackers = [a for a in self.attackers if a.alive]

        for effect in self.effects:
            effect[2] -= dt
        self.effects = [e for e in self.effects if e[2] > 0]

        if self.invasion_pressure >= 100:
            self.invasion_pressure = 100
            self.game_over = True
            self.event_message = "El Congreso fue invadido."

    def draw_ui(self):
        pygame.draw.rect(self.screen, (35, 40, 48), (0, 0, self.width, 88))

        mins = int(self.survival_time // 60)
        secs = int(self.survival_time % 60)
        prep = max(0, int(self.preparation_time))

        status = (
            f"Tiempo {mins:02d}:{secs:02d}   Presion sobre Congreso {self.invasion_pressure:05.1f}%   "
            f"Oleada {self.wave_index + 1}"
        )
        self.screen.blit(self.font.render(status, True, (240, 240, 240)), (14, 8))

        reserve_text = "  ".join(
            f"{key}:{value}" for key, value in self.reserves.items()
        )
        self.screen.blit(self.tiny_font.render("Reservas  " + reserve_text, True, (210, 215, 220)), (14, 35))

        controls = (
            "[1-5] desplegar unidad  [6] valla  click: seleccionar/desplegar  "
            "click derecho: mover  [H] mantener  [P] pausa  [R] reset"
        )
        self.screen.blit(self.small_font.render(controls, True, (205, 210, 215)), (14, 54))

        mode = self.cfg["security"].get(self.placement_mode, {}).get("label", "Valla")
        self.screen.blit(self.small_font.render(f"Despliegue: {mode}", True, (255, 220, 120)), (14, 72))

        if prep > 0:
            txt = self.font.render(f"PREPARACION: {prep}s", True, (150, 40, 40))
            self.screen.blit(txt, txt.get_rect(center=(self.width // 2, 108)))

        if self.event_message_timer > 0 or self.game_over:
            txt = self.font.render(self.event_message, True, (120, 35, 35))
            self.screen.blit(txt, txt.get_rect(center=(self.width // 2, 132)))

        if self.game_over:
            result = self.font.render(
                f"OPERATIVO FINALIZADO - resistio {mins:02d}:{secs:02d} - R para reiniciar",
                True,
                (165, 25, 25),
            )
            self.screen.blit(result, result.get_rect(center=(self.width // 2, 160)))

    def draw(self):
        self.map.draw(self.screen, self.tiny_font)
        mouse = pygame.Vector2(pygame.mouse.get_pos())

        for barrier in self.barriers:
            barrier.draw(self.screen)
        for unit in self.security_units:
            unit.draw(self.screen, show_range=mouse.distance_to(unit.pos) < 28 or unit.selected)
        for attacker in self.attackers:
            attacker.draw(self.screen, self.tiny_font)
        for start, end, _ in self.effects:
            pygame.draw.line(self.screen, (50, 50, 50), start, end, 2)

        self.draw_ui()
        pygame.display.flip()

    def reset(self):
        self.__init__(self.config_file)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(self.fps) / 1000.0

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
                    elif event.key == pygame.K_h:
                        self.hold_selected()
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.reset()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.pos[1] <= 88:
                        continue
                    if event.button == 1:
                        selected = self.select_at(
                            event.pos,
                            additive=bool(pygame.key.get_mods() & pygame.KMOD_SHIFT),
                        )
                        if not selected and not self.selected_units:
                            self.deploy(event.pos)
                    elif event.button == 3:
                        self.order_move(event.pos)

            self.update(dt)
            self.draw()

        pygame.quit()
