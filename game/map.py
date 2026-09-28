import pygame


class CongressMap:
    """Schematic playable map based on the street network around Plaza Congreso."""

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

    def draw(self, screen, font):
        screen.fill(self.bg)

        for road in self.streets:
            rect = pygame.Rect(*road["rect"])
            pygame.draw.rect(screen, self.road, rect)
            if road.get("axis") == "h":
                y = rect.centery
                for x in range(rect.left + 10, rect.right, 48):
                    pygame.draw.line(screen, self.road_line, (x, y), (min(x + 22, rect.right), y), 2)
            else:
                x = rect.centerx
                for y in range(rect.top + 10, rect.bottom, 48):
                    pygame.draw.line(screen, self.road_line, (x, y), (x, min(y + 22, rect.bottom)), 2)

        pygame.draw.rect(screen, self.park, self.plaza, border_radius=8)
        pygame.draw.rect(screen, (85, 125, 85), self.plaza, 2, border_radius=8)

        pygame.draw.rect(screen, self.building, self.congress)
        pygame.draw.rect(screen, (95, 80, 65), self.congress, 3)

        title = font.render("CONGRESO", True, (65, 50, 40))
        screen.blit(title, title.get_rect(center=self.congress.center))

        for label in self.labels:
            surf = font.render(label["text"], True, (75, 75, 75))
            screen.blit(surf, tuple(label["pos"]))
