import random
import yaml
import pygame

from game.entities import Attacker, SecurityUnit, Barrier


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
        pygame.display.set_caption("Congreso Defense - Prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.tiny_font = pygame.font.SysFont("Arial", 11)

        self.money = int(self.cfg["game"]["money"])
        self.lives = int(self.cfg["game"]["lives"])

        self.attackers = []
        self.security_units = []
        self.barriers = []
        self.effects = []

        g = self.cfg["goal"]
        self.goal_rect = pygame.Rect(g["x"], g["y"], g["width"], g["height"])
        self.goal_center = self.goal_rect.center

        self.wave_index = 0
        self.wave_running = False
        self.wave_queue = []
        self.spawn_timer = 0.0

        self.mode = "infanteria"
        self.paused = False
        self.game_over = False

    def start_wave(self):
        if self.wave_running or self.wave_index >= len(self.cfg["waves"]):
            return

        wave = self.cfg["waves"][self.wave_index]
        queue = []
        for kind, count in wave["composition"].items():
            queue.extend([kind] * int(count))
        random.shuffle(queue)
        self.wave_queue = queue
        self.spawn_timer = 0.0
        self.wave_running = True

    def spawn_attacker(self, kind):
        spawn = random.choice(self.cfg["spawn_points"])
        pos = (spawn[0], spawn[1] + random.randint(-28, 28))
        self.attackers.append(
            Attacker(pos, kind, self.cfg["attackers"][kind], self.goal_center)
        )

    def place_object(self, pos):
        if self.mode == "barrier":
            cost = int(self.cfg["barrier"]["cost"])
            if self.money >= cost:
                self.barriers.append(Barrier(pos, self.cfg["barrier"]))
                self.money -= cost
            return

        cfg = self.cfg["security"][self.mode]
        cost = int(cfg["cost"])
        if self.money >= cost:
            self.security_units.append(SecurityUnit(pos, self.mode, cfg))
            self.money -= cost

    def update_wave(self, dt):
        if not self.wave_running:
            return

        wave = self.cfg["waves"][self.wave_index]
        if self.wave_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_attacker(self.wave_queue.pop())
                self.spawn_timer = float(wave["interval"])
        elif not any(a.alive for a in self.attackers):
            self.wave_running = False
            self.wave_index += 1

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.update_wave(dt)

        for attacker in self.attackers:
            attacker.update(dt, self.barriers, self.security_units)
            if attacker.reached_goal:
                self.lives -= 1
                attacker.reached_goal = False

        for unit in self.security_units:
            affected = unit.update(dt, self.attackers)
            if affected and unit.effect_type != "attract":
                for target in affected[:5]:
                    self.effects.append([pygame.Vector2(unit.pos), pygame.Vector2(target.pos), 0.08])

        for attacker in self.attackers:
            if not attacker.alive and not attacker.rewarded and not attacker.fled:
                self.money += attacker.reward
                attacker.rewarded = True

        self.attackers = [a for a in self.attackers if a.alive]

        for effect in self.effects:
            effect[2] -= dt
        self.effects = [e for e in self.effects if e[2] > 0]

        if self.lives <= 0:
            self.game_over = True

    def draw_map(self):
        self.screen.fill((225, 220, 205))
        for y in (120, 300, 480):
            pygame.draw.rect(self.screen, (190, 185, 170), (0, y, self.width, 120))
            for x in range(0, self.width, 60):
                pygame.draw.line(self.screen, (230, 225, 215), (x, y + 60), (x + 25, y + 60), 3)

        pygame.draw.rect(self.screen, (185, 170, 140), self.goal_rect)
        pygame.draw.rect(self.screen, (100, 90, 75), self.goal_rect, 3)
        title = self.font.render("CONGRESO", True, (60, 50, 40))
        self.screen.blit(title, title.get_rect(center=self.goal_rect.center))

    def draw_ui(self):
        pygame.draw.rect(self.screen, (35, 40, 48), (0, 0, self.width, 86))

        status = (
            f"Fondos: ${self.money}   Integridad: {self.lives}   "
            f"Oleada: {min(self.wave_index + 1, len(self.cfg['waves']))}/{len(self.cfg['waves'])}"
        )
        self.screen.blit(self.font.render(status, True, (240, 240, 240)), (15, 8))

        controls = (
            "[1] Infanteria  [2] Goma  [3] Hidrante  [4] Motorizada  "
            "[5] Infiltrado  [6] Barrera  [SPACE] Oleada  [P] Pausa  [R] Reset"
        )
        self.screen.blit(self.small_font.render(controls, True, (205, 210, 215)), (15, 39))

        if self.mode == "barrier":
            label = f"Modo: Barrera (${self.cfg['barrier']['cost']})"
        else:
            c = self.cfg["security"][self.mode]
            label = f"Modo: {c['label']} (${c['cost']})"
        self.screen.blit(self.small_font.render(label, True, (255, 220, 120)), (15, 62))

        counts = {}
        for attacker in self.attackers:
            counts[attacker.kind] = counts.get(attacker.kind, 0) + 1
        if counts:
            x = 810
            text = "  ".join(f"{k}:{v}" for k, v in counts.items())
            self.screen.blit(self.tiny_font.render(text, True, (225, 225, 225)), (x, 11))

        if self.game_over:
            text = self.font.render("OPERATIVO SUPERADO - R para reiniciar", True, (180, 30, 30))
            self.screen.blit(text, text.get_rect(center=(self.width // 2, 105)))
        elif self.wave_index >= len(self.cfg["waves"]) and not self.wave_running:
            text = self.font.render("ESCENARIO COMPLETADO", True, (30, 120, 50))
            self.screen.blit(text, text.get_rect(center=(self.width // 2, 105)))

    def draw(self):
        self.draw_map()
        mouse = pygame.Vector2(pygame.mouse.get_pos())

        for barrier in self.barriers:
            barrier.draw(self.screen)
        for unit in self.security_units:
            unit.draw(self.screen, show_range=mouse.distance_to(unit.pos) < 28)
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
                        self.mode = key_modes[event.key]
                    elif event.key == pygame.K_SPACE:
                        self.start_wave()
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.reset()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if event.pos[1] > 86:
                        self.place_object(event.pos)

            self.update(dt)
            self.draw()

        pygame.quit()
