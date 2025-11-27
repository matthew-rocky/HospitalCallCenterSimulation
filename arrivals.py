from __future__ import annotations
import random
from typing import Dict
import simpy

class TimeVaryingRate:
    """Nonhomogeneous Poisson Process (NHPP) via thinning."""
    def __init__(self, hourly: Dict[int, float]):
        self.hourly = hourly
        self.max_rate = max(hourly.values()) / 3600.0 if hourly else 0.0

    def rate_at(self, t_seconds: int) -> float:
        hour = 8 + int(t_seconds // 3600)
        lam_h = self.hourly.get(hour, 0.0)
        return lam_h / 3600.0

    def next_arrival(self, env: simpy.Environment, t_end: int):
        t = env.now
        while t < t_end:
            wait = random.expovariate(self.max_rate) if self.max_rate > 0 else t_end
            t += wait
            if t >= t_end:
                return None
            if self.max_rate == 0:
                continue
            if random.random() < self.rate_at(int(t)) / self.max_rate:
                return t
        return None
