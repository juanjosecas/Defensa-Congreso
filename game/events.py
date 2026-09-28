import random


class EventSystem:
    def __init__(self, events, min_delay=18.0, max_delay=32.0):
        self.events = list(events)
        self.min_delay = float(min_delay)
        self.max_delay = float(max_delay)
        self.timer = random.uniform(self.min_delay, self.max_delay)

    def update(self, dt):
        if not self.events:
            return None
        self.timer -= dt
        if self.timer > 0:
            return None
        self.timer = random.uniform(self.min_delay, self.max_delay)
        return random.choice(self.events)
