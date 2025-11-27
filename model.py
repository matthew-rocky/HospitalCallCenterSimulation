from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple
import simpy

try:
    from .config import ModelConfig, ServiceConfig
    from .arrivals import TimeVaryingRate
    from .resources import AgentPool
    from .metrics import KPIs
    from .scenarios import ScenarioConfig
except ImportError:  # allow running as standalone scripts
    from config import ModelConfig, ServiceConfig
    from arrivals import TimeVaryingRate
    from resources import AgentPool
    from metrics import KPIs
    from scenarios import ScenarioConfig

class CallCenter:
    def __init__(self, env: simpy.Environment, cfg: ModelConfig, scenario: str):
        self.env = env
        self.cfg = cfg
        self.sc = ScenarioConfig(cfg, scenario)

        self.pool_exams, self.pool_consults, self.pool_merged = self.sc.build_pools(env)
        self.arr_exams = TimeVaryingRate(cfg.exams_hourly)
        self.arr_consults = TimeVaryingRate(cfg.consults_hourly)

        self.kpi_exams = KPIs()
        self.kpi_consults = KPIs()

        # ADDED: queue length traces for plotting (share when using merged pool)
        if self.pool_merged is not None:
            shared_trace: List[Tuple[float, int]] = []
            self.queue_length_trace_exams = shared_trace
            self.queue_length_trace_consults = shared_trace
        else:
            self.queue_length_trace_exams: List[Tuple[float, int]] = []
            self.queue_length_trace_consults: List[Tuple[float, int]] = []

        env.process(self._arrival_process("exams"))
        env.process(self._arrival_process("consults"))

    # --------- helpers ---------
    def _sample_handle(self, svc: ServiceConfig, call_type: Optional[str]) -> float:
        mu, sigma = svc.lognormal_params(call_type)
        return random.lognormvariate(mu, sigma)

    def _exp(self, mean: float) -> float:
        """Exponential with a small floor so callers never abandon instantly."""
        if mean <= 0:
            return float("inf")
        return max(1.0, random.expovariate(1.0 / mean))

    def _sample_patience(self, mean: float, minimum: float, cap: Optional[float]) -> float:
        """
        Exponential patience with truncation to avoid unrealistically tiny/huge waits.
        The paper notes many abandon around 60–120 seconds; this keeps mass in that band.
        """
        base = self._exp(mean)
        base = max(minimum, base)
        if cap is not None:
            base = min(cap, base)
        return base

    def _select_pool(self, kind: str) -> AgentPool:
        if self.pool_merged is not None:
            return self.pool_merged
        return self.pool_exams if kind == "exams" else self.pool_consults

    def _record_queue_length(self, kind: str) -> None:
        """Snapshot queue length for the given service to power time-series plotting."""
        pool = self._select_pool(kind)
        trace = self.queue_length_trace_exams if kind == "exams" else self.queue_length_trace_consults
        trace.append((self.env.now, len(pool.capacity.queue)))

    # --------- processes ---------
    def _choose_call_type(self, svc_cfg: ServiceConfig) -> Optional[str]:
        if not svc_cfg.call_types:
            return None
        r = random.random()
        cumulative = 0.0
        names = list(svc_cfg.call_types.keys())
        total = sum(max(0.0, cfg.probability) for cfg in svc_cfg.call_types.values())
        if total <= 0:
            return names[0]
        for name, cfg in svc_cfg.call_types.items():
            cumulative += max(0.0, cfg.probability) / total
            if r <= cumulative:
                return name
        return names[-1]  # numerical safety

    def _arrival_process(self, kind: str):
        env = self.env
        cfg = self.cfg
        kpi = self.kpi_exams if kind == "exams" else self.kpi_consults
        rate = self.arr_exams if kind == "exams" else self.arr_consults
        svc_cfg = (self._select_pool(kind).cfg)
        horizon = min(cfg.T_END, svc_cfg.shift_end)

        while True:
            nxt = rate.next_arrival(env, horizon)
            if nxt is None:
                return
            yield env.timeout(max(0, nxt - env.now))
            kpi.arrivals += 1
            call_type = self._choose_call_type(svc_cfg)
            env.process(self._handle_call(kind, svc_cfg, kpi, call_type))

    def _handle_call(self, kind: str, svc_cfg: ServiceConfig, kpi: KPIs, call_type: Optional[str]):
        env = self.env
        pool = self._select_pool(kind)

        # Stage 1: RING (unless ring_cancel scenario)
        ring_req = None
        if not self.sc.ring_cancel:
            ring_req, answered_in_ring, abandoned = yield from self._ring_stage(pool, svc_cfg)
            if abandoned:
                kpi.abandoned_ring += 1
                return
            if answered_in_ring and ring_req is not None:
                # Immediate answer during ring; queue wait is zero by definition
                kpi.sla_hits += 1
                pool.begin_service()
                handle = self._sample_handle(svc_cfg, call_type)
                yield env.timeout(handle)
                pool.end_service()
                pool.capacity.release(ring_req)
                kpi.answered += 1
                kpi.total_handle_time += handle
                kpi.handle_time_samples.append(handle)
                kpi.record_answered_type(call_type)
                return

        # Stage 2: QUEUE to seize agent
        t_queue_start = env.now
        patience_q = self._sample_patience(
            svc_cfg.queue_patience_mean,
            svc_cfg.queue_patience_min,
            svc_cfg.queue_patience_cap,
        )
        req = pool.capacity.request()
        # ADDED: record queue length after joining the queue
        self._record_queue_length(kind)
        res = yield req | env.timeout(patience_q)
        if req not in res:
            req.cancel()  # remove abandoned request so it does not block capacity
            kpi.abandoned_queue += 1
            # ADDED: record queue length after abandonment
            self._record_queue_length(kind)
            return

        wait_q = env.now - t_queue_start
        if wait_q > 0:
            kpi.queue_wait_sum_nonzero += wait_q
            kpi.queue_wait_count_nonzero += 1
            # ADDED: collect non-zero waits for histogram
            kpi.queue_wait_samples.append(wait_q)
        if wait_q <= svc_cfg.sla_threshold:
            kpi.sla_hits += 1

        # ADDED: record queue length after service begins (queue decremented)
        self._record_queue_length(kind)

        # Service
        pool.begin_service()
        handle = self._sample_handle(svc_cfg, call_type)
        yield env.timeout(handle)
        pool.end_service()
        pool.capacity.release(req)

        kpi.answered += 1
        kpi.total_handle_time += handle
        # ADDED: collect handle-time samples for histogram
        kpi.handle_time_samples.append(handle)
        kpi.record_answered_type(call_type)

    def _ring_stage(self, pool: AgentPool, svc_cfg: ServiceConfig):
        env = self.env
        patience = self._sample_patience(
            svc_cfg.ring_patience_mean,
            svc_cfg.ring_patience_min,
            svc_cfg.ring_patience_cap,
        )
        # Try to seize an agent during the ring window; otherwise decide whether to continue in queue
        req = pool.capacity.request()
        res = yield req | env.timeout(patience)
        if req in res:
            return req, True, False  # answered during ring
        req.cancel()
        # Portion of callers drop after ringing; the rest proceed to the queue stage
        abandon = random.random() >= svc_cfg.ring_to_queue_prob
        return None, False, abandon

    # --------- results ---------
    def results(self) -> Dict[str, Dict[str, float]]:
        out = {
            "exams": self.kpi_exams.summarize(),
            "consults": self.kpi_consults.summarize(),
        }
        # ADDED: expose queue length traces for visualization
        out["exams"]["queue_length_trace"] = list(self.queue_length_trace_exams)
        out["consults"]["queue_length_trace"] = list(self.queue_length_trace_consults)
        if self.pool_merged is not None:
            out["utilization_merged"] = {"util": self.pool_merged.utilization}
        else:
            out["utilization_exams"] = {"util": self.pool_exams.utilization}
            out["utilization_consults"] = {"util": self.pool_consults.utilization}
        return out
