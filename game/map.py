import pygame


class CongressMap:
    """Playable map with explicit terrain constraints and defensive sectors."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = tuple(cfg.get("background", [225, 220, 205]))
        self.road = tuple(cfg.get("road_color", [188, 190, 194]))
        self.road_line = tuple(cfg.get("road_line", [235, 235, 230]))
        self.park = tuple(cfg.get("park_color", [154, 190, 150]))
        self.building = tuple(cfg.get("building_color", [188, 170, 140]))
        self.streets = cfg.get("streets", [])
        self.labels = cfg.get("labels", [])
        self.plaza = pygame.Rect(*cfg["plaza_rect"])
        self.congress = pygame.Rect(*cfg["congress_rect"])
        self.street_rects = [pygame.Rect(*road["rect"]) for road in self.streets]
        self.sectors = {
            item["name"]: pygame.Rect(*item["rect"])
            for item in cfg.get("sectors", [])
        }

    def terrain_at(self, point):
        p = (int(point[0]), int(point[1]))
        if self.congress.collidepoint(p):
            return "building"
        if self.plaza.collidepoint(p):
            return "plaza"
        if any(rect.collidepoint(p) for rect in self.street_rects):
            return "street"
        return "building"

    def can_enter(self, point, unit_type):
        terrain = self.terrain_at(point)
        if unit_type == "motorized":
            return terrain == "street"
        if unit_type in ("attacker", "foot"):
            return terrain in ("street", "plaza")
        return False

    def clamp_motion(self, old_pos, new_pos, unit_type):
        if self.can_enter(new_pos, unit_type):
            return pygame.Vector2(new_pos)

        x_only = pygame.Vector2(new_pos.x, old_pos.y)
        if self.can_enter(x_only, unit_type):
            return x_only

        y_only = pygame.Vector2(old_pos.x, new_pos.y)
        if self.can_enter(y_only, unit_type):
            return y_only

        return pygame.Vector2(old_pos)

    def nearest_valid_point(self, point, unit_type, search_radius=90, step=12):
        point = pygame.Vector2(point)
        if self.can_enter(point, unit_type):
            return point

        for radius in range(step, search_radius + step, step):
            for dx, dy in (
                (radius, 0), (-radius, 0), (0, radius), (0, -radius),
                (radius, radius), (radius, -radius),
                (-radius, radius), (-radius, -radius),
            ):
                candidate = point + pygame.Vector2(dx, dy)
                if self.can_enter(candidate, unit_type):
                    return candidate
        return None

    def sector_for_point(self, point):
        p = (int(point[0]), int(point[1]))
        for name, rect in self.sectors.items():
            if rect.collidepoint(p):
                return name
        return None

    def draw(self, screen, font):
        screen.fill(self.bg)

        for road in self.streets:
            rect = pygame.Rect(*road["rect"])
            pygame.draw.rect(screen, self.road, rect)

            if road.get("axis") == "h":
                y = rect.centery
                for x in range(rect.left + 10, rect.right, 48):
                    pygame.draw.line(
                        screen,
                        self.road_line,
                        (x, y),
                        (min(x + 22, rect.right), y),
                        2,
                    )
            else:
                x = rect.centerx
                for y in range(rect.top + 10, rect.bottom, 48):
                    pygame.draw.line(
                        screen,
                        self.road_line,
                        (x, y),
                        (x, min(y + 22, rect.bottom)),
                        2,
                    )

        pygame.draw.rect(screen, self.park, self.plaza, border_radius=8)
        pygame.draw.rect(screen, (85, 125, 85), self.plaza, 2, border_radius=8)

        pygame.draw.rect(screen, self.building, self.congress)
        pygame.draw.rect(screen, (95, 80, 65), self.congress, 3)

        for name, rect in self.sectors.items():
            pygame.draw.rect(screen, (115, 105, 95), rect, 1)
            label = font.render(name, True, (95, 80, 70))
            screen.blit(label, (rect.left + 3, rect.top + 3))

        title = font.render("CONGRESO", True, (65, 50, 40))
        screen.blit(title, title.get_rect(center=self.congress.center))

        for label in self.labels:
            surf = font.render(label["text"], True, (75, 75, 75))
            screen.blit(surf, tuple(label["pos"]))
