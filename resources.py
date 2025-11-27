
from __future__ import annotations
import random
import simpy
try:
    from .config import ServiceConfig
except ImportError:  # allow running as standalone scripts
    from config import ServiceConfig

class AgentPool:
    def __init__(self, env: simpy.Environment, cfg: ServiceConfig):
        self.env = env
        self.cfg = cfg
        initial_capacity = max(cfg.n_agents, cfg.min_capacity)
        self.capacity = simpy.Resource(env, capacity=initial_capacity)
        self._base_capacity = cfg.n_agents
        self._active_extra = 0
        self._active_breaks = 0
        self.busy_time = 0.0  # accumulated agent-seconds of service work
        self._busy_agents = 0
        self._last_busy_change = env.now
        env.process(self._inject_breaks())  # inefficiency modeled as staggered per-agent breaks
        if self.cfg.extra_agents_windows:
            env.process(self._apply_extra_agents())

    def _sync_capacity(self):
        """Recompute effective capacity after break/extra-agent changes."""
        effective = max(
            self.cfg.min_capacity,
            self._base_capacity + self._active_extra - self._active_breaks,
        )
        self.capacity._capacity = effective  # noqa: SLF001

    def _update_busy_time(self):
        """Track agent-seconds by integrating the busy-agent count over time."""
        now = self.env.now
        elapsed = now - self._last_busy_change
        if elapsed > 0 and self._busy_agents > 0:
            self.busy_time += self._busy_agents * elapsed
        self._last_busy_change = now

    def _inject_breaks(self):
        """Distribute each agent's breaks across the shift (3-5 chunks, ~40% loss)."""
        shift_len = max(0.0, self.cfg.shift_end - self.cfg.shift_start)
        total_break = 0.0

        if shift_len > 0 and self.cfg.inefficiency_share > 0:
            per_agent_break = self.cfg.inefficiency_share * shift_len
            for _agent in range(self.cfg.n_agents):
                n_chunks = random.randint(3, 5)
                if n_chunks <= 0:
                    continue
                chunk = per_agent_break / n_chunks
                segment = shift_len / n_chunks
                for i in range(n_chunks):
                    slack = max(0.0, segment - chunk)
                    start = self.cfg.shift_start + i * segment + random.uniform(0.0, slack)
                    end = min(start + chunk, self.cfg.shift_end)
                    duration = max(0.0, end - start)
                    total_break += duration
                    self.env.process(self._agent_break(start, duration))

        if self.cfg.n_agents > 0 and shift_len > 0:
            print("Effective break share:", total_break / (self.cfg.n_agents * shift_len))
        yield self.env.timeout(0)

    def _agent_break(self, start: float, duration: float):
        """Reduce capacity for one agent during a break window."""
        if duration <= 0:
            return
        yield self.env.timeout(max(0.0, start - self.env.now))
        self._active_breaks += 1
        self._sync_capacity()
        yield self.env.timeout(duration)
        self._active_breaks -= 1
        self._sync_capacity()

    def begin_service(self):
        self._update_busy_time()
        self._busy_agents += 1

    def end_service(self):
        self._update_busy_time()
        self._busy_agents = max(0, self._busy_agents - 1)

    @property
    def utilization(self) -> float:
        self._update_busy_time()  # include any work-in-progress up to "now"
        horizon = min(self.env.now, self.cfg.shift_end)
        elapsed = max(0.0, horizon - self.cfg.shift_start)
        base = self.cfg.n_agents * elapsed
        extra = 0.0
        for window in self.cfg.extra_agents_windows:
            start = max(window.start, self.cfg.shift_start)
            end = min(window.end, horizon)
            if end > start:
                extra += window.extra_agents * (end - start)
        denom = max(1.0, base + extra)
        util = self.busy_time / denom
        return min(1.0, util)

    def _apply_extra_agents(self):
        windows = sorted(self.cfg.extra_agents_windows, key=lambda w: w.start)
        for window in windows:
            if window.extra_agents <= 0:
                continue
            yield self.env.timeout(max(0, window.start - self.env.now))
            self._active_extra += window.extra_agents
            self._sync_capacity()
            yield self.env.timeout(max(0, window.end - self.env.now))
            self._active_extra -= window.extra_agents
            target = max(self.cfg.min_capacity, self._base_capacity + self._active_extra - self._active_breaks)
            while self.capacity.count > target:
                yield self.env.timeout(1)
            self._sync_capacity()
