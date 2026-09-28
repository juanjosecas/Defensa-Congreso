import random
import pygame


class Attacker:
    def __init__(self, pos, kind, cfg, goal_center):
        self.kind = kind
        self.label = cfg.get("label", kind)
        self.pos = pygame.Vector2(pos)
        self.spawn = pygame.Vector2(pos)
        self.goal = pygame.Vector2(goal_center)
        self.speed = float(cfg["speed"])
        self.resistance = float(cfg["resistance"])
        self.max_resistance = float(cfg["resistance"])
        self.flee_threshold = float(cfg.get("flee_threshold", 0.0))
        self.police_avoidance = float(cfg.get("police_avoidance", 0.0))
        self.reward = int(cfg["reward"])
        self.radius = int(cfg["radius"])
        self.color = tuple(cfg.get("color", [210, 70, 70]))

        self.alive = True
        self.reached_goal = False
        self.fled = False
        self.rewarded = False
        self.slow_factor = 1.0
        self.slow_timer = 0.0
        self.attracted_to = None
        self.attraction_timer = 0.0

    def apply_control(self, power, slow=1.0, slow_seconds=0.7):
        self.resistance -= power
        if slow < self.slow_factor:
            self.slow_factor = slow
            self.slow_timer = max(self.slow_timer, slow_seconds)

        ratio = max(0.0, self.resistance / self.max_resistance)
        if self.flee_threshold > 0 and ratio <= self.flee_threshold:
            self.fled = True
            self.alive = False
        elif self.resistance <= 0:
            self.alive = False

    def attract(self, point, seconds):
        self.attracted_to = pygame.Vector2(point)
        self.attraction_timer = max(self.attraction_timer, seconds)

    def update(self, dt, barriers, security_units):
        if not self.alive:
            return

        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_factor = 1.0

        if self.attraction_timer > 0 and self.attracted_to is not None:
            self.attraction_timer -= dt
            target = self.attracted_to
        else:
            self.attracted_to = None
            target = self.goal

        # Transeuntes y otros arquetipos con avoidance se apartan de unidades cercanas.
        avoidance = pygame.Vector2(0, 0)
        if self.police_avoidance > 0:
            for unit in security_units:
                delta = self.pos - unit.pos
                dist = delta.length()
                if 0 < dist < 105:
                    avoidance += delta.normalize() * (105 - dist) / 105

        direction = target - self.pos
        if target == self.goal and direction.length_squared() < 20**2:
            self.alive = False
            self.reached_goal = True
            return

        if direction.length_squared() > 0:
            direction = direction.normalize()

        if avoidance.length_squared() > 0:
            direction += avoidance.normalize() * self.police_avoidance
            if direction.length_squared() > 0:
                direction = direction.normalize()

        barrier_factor = 1.0
        for barrier in barriers:
            if self.pos.distance_to(barrier.pos) < barrier.radius:
                barrier_factor = min(barrier_factor, barrier.slow_factor)

        self.pos += direction * self.speed * self.slow_factor * barrier_factor * dt

    def push_away(self, source, amount):
        delta = self.pos - pygame.Vector2(source)
        if delta.length_squared() > 0:
            self.pos += delta.normalize() * amount

    def draw(self, screen, font=None):
        p = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(screen, self.color, p, self.radius)
        pygame.draw.circle(screen, (45, 45, 45), p, self.radius, 1)

        bar_w = 24
        ratio = max(0.0, self.resistance / self.max_resistance)
        pygame.draw.rect(screen, (55, 55, 55), (p[0] - 12, p[1] - 17, bar_w, 4))
        pygame.draw.rect(screen, (80, 190, 90), (p[0] - 12, p[1] - 17, int(bar_w * ratio), 4))

        if font and self.attraction_timer > 0:
            mark = font.render("?", True, (50, 20, 70))
            screen.blit(mark, (p[0] - 3, p[1] - 32))


class SecurityUnit:
    def __init__(self, pos, kind, cfg):
        self.kind = kind
        self.label = cfg.get("label", kind)
        self.pos = pygame.Vector2(pos)
        self.range = float(cfg["range"])
        self.power = float(cfg.get("power", 0))
        self.cooldown = float(cfg.get("cooldown", 0.5))
        self.radius = int(cfg["radius"])
        self.effect_type = cfg.get("effect_type", "single")
        self.slow = float(cfg.get("slow", 1.0))
        self.area_radius = float(cfg.get("area_radius", 0))
        self.push = float(cfg.get("push", 0))
        self.attraction_chance = float(cfg.get("attraction_chance", 0))
        self.attraction_seconds = float(cfg.get("attraction_seconds", 0))
        self.color = tuple(cfg.get("color", [70, 110, 210]))
        self.timer = 0.0

    def update(self, dt, attackers):
        self.timer = max(0.0, self.timer - dt)
        valid = [a for a in attackers if a.alive and self.pos.distance_to(a.pos) <= self.range]
        if not valid:
            return []

        if self.effect_type == "attract":
            affected = []
            for attacker in valid:
                if random.random() < self.attraction_chance:
                    attacker.attract(self.pos, self.attraction_seconds)
                    affected.append(attacker)
            return affected

        if self.timer > 0:
            return []

        if self.effect_type == "area":
            target = min(valid, key=lambda a: self.pos.distance_to(a.pos))
            affected = [
                a for a in attackers
                if a.alive and a.pos.distance_to(target.pos) <= self.area_radius
            ]
            for attacker in affected:
                attacker.apply_control(self.power, self.slow, 1.1)
                attacker.push_away(self.pos, self.push)
            self.timer = self.cooldown
            return affected

        target = min(valid, key=lambda a: self.pos.distance_to(a.pos))
        target.apply_control(self.power, self.slow, 0.8)
        self.timer = self.cooldown
        return [target]

    def draw(self, screen, show_range=False):
        p = (int(self.pos.x), int(self.pos.y))
        if show_range:
            pygame.draw.circle(screen, (85, 90, 105), p, int(self.range), 1)

        if self.kind == "hidrante":
            rect = pygame.Rect(p[0] - 18, p[1] - 11, 36, 22)
            pygame.draw.rect(screen, self.color, rect, border_radius=4)
            pygame.draw.circle(screen, (35, 35, 35), (p[0] - 11, p[1] + 12), 4)
            pygame.draw.circle(screen, (35, 35, 35), (p[0] + 11, p[1] + 12), 4)
        elif self.kind == "motorizada":
            pygame.draw.circle(screen, (35, 35, 35), p, self.radius + 2)
            pygame.draw.circle(screen, self.color, p, self.radius - 2)
        elif self.kind == "infiltrado":
            pygame.draw.circle(screen, self.color, p, self.radius)
            pygame.draw.circle(screen, (225, 205, 235), p, max(3, self.radius // 3))
        else:
            pygame.draw.circle(screen, self.color, p, self.radius)
            pygame.draw.circle(screen, (225, 235, 255), p, max(3, self.radius // 3))


class Barrier:
    def __init__(self, pos, cfg):
        self.pos = pygame.Vector2(pos)
        self.width = int(cfg["width"])
        self.height = int(cfg["height"])
        self.slow_factor = float(cfg["slow_factor"])
        self.radius = float(cfg["radius"])

    def draw(self, screen):
        rect = pygame.Rect(
            int(self.pos.x - self.width / 2),
            int(self.pos.y - self.height / 2),
            self.width,
            self.height,
        )
        pygame.draw.rect(screen, (170, 140, 80), rect)
        pygame.draw.rect(screen, (90, 70, 40), rect, 2)
