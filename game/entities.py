import random
import pygame


class Attacker:
    def __init__(self, pos, kind, cfg, route, uid):
        self.kind = kind
        self.label = cfg.get("label", kind)
        self.short_label = cfg.get("short_label", self.label)
        self.display_name = f"{self.short_label} {uid:02d}"

        self.pos = pygame.Vector2(pos)
        self.spawn = pygame.Vector2(pos)
        self.route = [pygame.Vector2(p) for p in route]
        self.route_index = 0

        self.speed = float(cfg["speed"])
        self.resistance = float(cfg["resistance"])
        self.max_resistance = float(cfg["resistance"])
        self.flee_threshold = float(cfg.get("flee_threshold", 0.0))
        self.police_avoidance = float(cfg.get("police_avoidance", 0.0))
        self.radius = int(cfg["radius"])
        self.color = tuple(cfg.get("color", [210, 70, 70]))
        self.breach_power = float(cfg.get("breach_power", 8.0))
        self.barrier_damage = float(cfg.get("barrier_damage", 5.0))

        # Behaviour is intentionally non-deterministic: attackers can loiter,
        # advance, regroup locally or retreat after deterrence.
        self.behavior_state = random.choices(
            ["advance", "loiter"],
            weights=[cfg.get("advance_weight", 0.68), cfg.get("loiter_weight", 0.32)],
            k=1,
        )[0]
        self.behavior_timer = random.uniform(2.5, 6.5)
        self.loiter_target = pygame.Vector2(self.pos)
        self.retreat_timer = 0.0

        self.deterrence = 0.0
        self.deterrence_threshold = float(cfg.get("deterrence_threshold", 70.0))

        self.alive = True
        self.reached_goal = False
        self.fled = False
        self.detained = False

        self.slow_factor = 1.0
        self.slow_timer = 0.0
        self.attracted_to = None
        self.attraction_timer = 0.0

    def apply_control(self, power, slow=1.0, slow_seconds=0.7):
        """Physical/control units reduce resistance and can detain/remove."""
        self.resistance -= power
        if slow < self.slow_factor:
            self.slow_factor = slow
            self.slow_timer = max(self.slow_timer, slow_seconds)

        ratio = max(0.0, self.resistance / self.max_resistance)
        if self.flee_threshold > 0 and ratio <= self.flee_threshold:
            self.fled = True
            self.alive = False
        elif self.resistance <= 0:
            self.detained = True
            self.alive = False

    def apply_deterrence(self, amount, slow=0.55, seconds=1.3):
        """Hydrant-like effects delay and can force temporary retreat."""
        self.deterrence = min(100.0, self.deterrence + amount)
        if slow < self.slow_factor:
            self.slow_factor = slow
            self.slow_timer = max(self.slow_timer, seconds)

        if self.deterrence >= self.deterrence_threshold or random.random() < amount / 300.0:
            self.behavior_state = "retreat"
            self.retreat_timer = random.uniform(2.5, 6.0)
            self.deterrence *= 0.55

    def attract(self, point, seconds):
        self.attracted_to = pygame.Vector2(point)
        self.attraction_timer = max(self.attraction_timer, seconds)

    def _choose_behavior(self):
        self.behavior_state = random.choices(
            ["advance", "loiter"],
            weights=[0.72, 0.28],
            k=1,
        )[0]
        self.behavior_timer = random.uniform(2.5, 7.0)

    def _choose_loiter_target(self, world_map):
        for _ in range(16):
            candidate = self.pos + pygame.Vector2(
                random.uniform(-95, 95),
                random.uniform(-95, 95),
            )
            if world_map.can_enter(candidate, "attacker"):
                self.loiter_target = candidate
                return
        self.loiter_target = pygame.Vector2(self.pos)

    def _advance_target(self):
        return self.route[min(self.route_index, len(self.route) - 1)]

    def _retreat_target(self):
        if self.route_index > 1:
            return self.route[self.route_index - 2]
        return self.spawn

    def update(self, dt, barriers, security_units, world_map):
        if not self.alive:
            return

        self.deterrence = max(0.0, self.deterrence - 5.0 * dt)

        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_factor = 1.0

        using_attraction = self.attraction_timer > 0 and self.attracted_to is not None
        if using_attraction:
            self.attraction_timer -= dt
            target = self.attracted_to
        else:
            self.attracted_to = None

            if self.behavior_state == "retreat":
                self.retreat_timer -= dt
                target = self._retreat_target()
                if self.retreat_timer <= 0:
                    self._choose_behavior()
            elif self.behavior_state == "loiter":
                self.behavior_timer -= dt
                if self.loiter_target.distance_to(self.pos) < 14:
                    self._choose_loiter_target(world_map)
                target = self.loiter_target
                if self.behavior_timer <= 0:
                    self._choose_behavior()
            else:
                self.behavior_timer -= dt
                target = self._advance_target()
                if self.behavior_timer <= 0 and random.random() < 0.30:
                    self.behavior_state = "loiter"
                    self.behavior_timer = random.uniform(2.0, 5.0)
                    self._choose_loiter_target(world_map)

        direction = target - self.pos

        if self.behavior_state == "advance" and not using_attraction and direction.length_squared() < 18 ** 2:
            self.route_index += 1
            if self.route_index >= len(self.route):
                self.alive = False
                self.reached_goal = True
                return
            target = self._advance_target()
            direction = target - self.pos

        avoidance = pygame.Vector2()
        if self.police_avoidance > 0:
            for unit in security_units:
                delta = self.pos - unit.pos
                dist = delta.length()
                if 0 < dist < 105:
                    avoidance += delta.normalize() * (105 - dist) / 105

        if direction.length_squared() > 0:
            direction = direction.normalize()

        if avoidance.length_squared() > 0:
            direction += avoidance.normalize() * self.police_avoidance
            if direction.length_squared() > 0:
                direction = direction.normalize()

        barrier_factor = 1.0
        for barrier in barriers:
            if barrier.alive and self.pos.distance_to(barrier.pos) < barrier.radius:
                barrier.take_damage(self.barrier_damage * dt)
                barrier_factor = min(barrier_factor, barrier.block_factor)

        proposed = self.pos + direction * self.speed * self.slow_factor * barrier_factor * dt
        self.pos = world_map.clamp_motion(self.pos, proposed, "attacker")

    def push_away(self, source, amount, world_map=None):
        delta = self.pos - pygame.Vector2(source)
        if delta.length_squared() == 0:
            return
        proposed = self.pos + delta.normalize() * amount
        if world_map is None:
            self.pos = proposed
        else:
            self.pos = world_map.clamp_motion(self.pos, proposed, "attacker")

    def draw(self, screen, font=None):
        p = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(screen, self.color, p, self.radius)
        pygame.draw.circle(screen, (45, 45, 45), p, self.radius, 1)

        ratio = max(0.0, self.resistance / self.max_resistance)
        pygame.draw.rect(screen, (55, 55, 55), (p[0] - 12, p[1] - 17, 24, 4))
        pygame.draw.rect(screen, (80, 190, 90), (p[0] - 12, p[1] - 17, int(24 * ratio), 4))

        if font:
            name = font.render(self.display_name, True, (35, 35, 35))
            screen.blit(name, name.get_rect(center=(p[0], p[1] - 27)))
            if self.behavior_state == "retreat":
                mark = font.render("retrocede", True, (90, 50, 130))
                screen.blit(mark, mark.get_rect(center=(p[0], p[1] - 39)))


class SecurityUnit:
    def __init__(self, pos, kind, cfg, uid):
        self.kind = kind
        self.label = cfg.get("label", kind)
        self.short_label = cfg.get("short_label", self.label)
        self.display_name = f"{self.short_label} {uid:02d}"

        self.pos = pygame.Vector2(pos)
        self.target_pos = pygame.Vector2(pos)
        self.move_speed = float(cfg.get("move_speed", 85))
        self.range = float(cfg["range"])
        self.power = float(cfg.get("power", 0))
        self.cooldown = float(cfg.get("cooldown", 0.5))
        self.radius = int(cfg["radius"])
        self.effect_type = cfg.get("effect_type", "single")
        self.slow = float(cfg.get("slow", 1.0))
        self.area_radius = float(cfg.get("area_radius", 0))
        self.push = float(cfg.get("push", 0))
        self.deterrence = float(cfg.get("deterrence", 0))
        self.attraction_chance = float(cfg.get("attraction_chance", 0))
        self.attraction_seconds = float(cfg.get("attraction_seconds", 0))
        self.color = tuple(cfg.get("color", [70, 110, 210]))
        self.movement_terrain = cfg.get("movement_terrain", "foot")

        self.timer = 0.0
        self.selected = False
        self.hold_position = False

    def move_to(self, point):
        self.target_pos = pygame.Vector2(point)
        self.hold_position = False

    def hold(self):
        self.target_pos = pygame.Vector2(self.pos)
        self.hold_position = True

    def update_movement(self, dt, world_map):
        delta = self.target_pos - self.pos
        if delta.length_squared() < 4:
            return

        step = self.move_speed * dt
        if delta.length() <= step:
            proposed = pygame.Vector2(self.target_pos)
        else:
            proposed = self.pos + delta.normalize() * step

        mode = "motorized" if self.movement_terrain == "street_only" else "foot"
        self.pos = world_map.clamp_motion(self.pos, proposed, mode)

    def update(self, dt, attackers, world_map):
        self.update_movement(dt, world_map)
        self.timer = max(0.0, self.timer - dt)

        valid = [a for a in attackers if a.alive and self.pos.distance_to(a.pos) <= self.range]
        if not valid:
            return []

        if self.effect_type == "attract":
            affected = []
            for attacker in valid:
                if random.random() < self.attraction_chance * dt * 60:
                    attacker.attract(self.pos, self.attraction_seconds)
                    affected.append(attacker)
            return affected

        if self.timer > 0:
            return []

        if self.effect_type == "deterrent_area":
            target = min(valid, key=lambda a: self.pos.distance_to(a.pos))
            affected = [
                a for a in attackers
                if a.alive and a.pos.distance_to(target.pos) <= self.area_radius
            ]
            for attacker in affected:
                attacker.apply_deterrence(self.deterrence, self.slow, 1.4)
                attacker.push_away(self.pos, self.push, world_map)
            self.timer = self.cooldown
            return affected

        target = min(valid, key=lambda a: self.pos.distance_to(a.pos))
        target.apply_control(self.power, self.slow, 0.9)
        self.timer = self.cooldown
        return [target]

    def draw(self, screen, font=None, show_range=False):
        p = (int(self.pos.x), int(self.pos.y))
        if self.selected:
            pygame.draw.circle(screen, (255, 220, 80), p, self.radius + 6, 2)
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
        else:
            pygame.draw.circle(screen, self.color, p, self.radius)
            pygame.draw.circle(screen, (225, 235, 255), p, max(3, self.radius // 3))

        if font:
            name = font.render(self.display_name, True, (20, 35, 65))
            screen.blit(name, name.get_rect(center=(p[0], p[1] - 27)))


class Barrier:
    def __init__(self, pos, cfg):
        self.pos = pygame.Vector2(pos)
        self.width = int(cfg["width"])
        self.height = int(cfg["height"])
        self.radius = float(cfg["radius"])
        self.block_factor = float(cfg.get("block_factor", 0.08))
        self.health = float(cfg.get("health", 180))
        self.max_health = self.health
        self.alive = True

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return

        rect = pygame.Rect(
            int(self.pos.x - self.width / 2),
            int(self.pos.y - self.height / 2),
            self.width,
            self.height,
        )
        pygame.draw.rect(screen, (170, 140, 80), rect)
        pygame.draw.rect(screen, (90, 70, 40), rect, 2)

        ratio = max(0.0, self.health / self.max_health)
        bar = pygame.Rect(rect.left, rect.top - 7, rect.width, 4)
        pygame.draw.rect(screen, (65, 65, 65), bar)
        pygame.draw.rect(screen, (70, 170, 80), (bar.left, bar.top, int(bar.width * ratio), bar.height))
