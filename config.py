
"""
Model configuration for the Hospital Call Center Discrete-Event Simulation
(consistent with the assumptions from the referenced WSC 2018 paper).

Key Modeling Assumptions
------------------------
• Two distinct services are modeled:
    - Exams: staffed by 3 agents, operating from 08:00 to 21:00.
    - Consultations: staffed by 2 agents, operating from 08:00 to 18:00.

• Agent productivity is reduced by approximately 40% due to non-call activities
  (breaks, meetings, technical issues, personal interruptions). This is represented
  by `inefficiency_share = 0.40`, which proportionally reduces effective staffing.

• Service-time distributions follow lognormal patterns derived from the paper.
  Each call type (first contact, appointment, doubts, transfer, etc.) has its own
  probability of occurrence and its own mean handling time.

• Arrivals follow a time-varying arrival pattern across the day (NHPP), capturing:
    - morning peak,
    - midday/lunch dip,
    - afternoon peak.
  These patterns reproduce the hourly arrival tables reported in the study.

This configuration provides the baseline parameters for Exams and Consults services
used across all simulation scenarios (baseline, ring cancellation, schedule change,
and centralization).
"""


from __future__ import annotations
import dataclasses as dc
import math
from typing import Dict, Tuple, List, Optional

@dc.dataclass
class CallTypeConfig:
    probability: float
    mean_handle: float  # mean service/handle time (seconds)
    handle_scatter: float = 0.4  # coefficient of variation for lognormal

    def lognormal_params(self) -> Tuple[float, float]:
        cv2 = self.handle_scatter ** 2
        sigma2 = math.log(1 + cv2)
        mu = math.log(self.mean_handle) - 0.5 * sigma2
        return mu, math.sqrt(sigma2)

@dc.dataclass
class ExtraAgentWindow:
    start: int  # seconds from t=0
    end: int    # seconds from t=0
    extra_agents: int

@dc.dataclass
class ServiceConfig:
    name: str
    n_agents: int
    shift_start: int  # seconds from t=0 (08:00)
    shift_end: int    # seconds from t=0
    mean_handle: Optional[float] = None
    handle_scatter: float = 0.4  # coefficient of variation for lognormal
    ring_cycle: int = 15  # 15-second re-routing cycle between ring checks
    sla_threshold: int = 10  # seconds (queue-only)
    ring_patience_mean: float = 170  # tuned toward ~90–180s typical abandonment
    queue_patience_mean: float = 1350  # tuned toward longer waits to reduce abandonment
    ring_patience_min: float = 10.0
    queue_patience_min: float = 30.0
    ring_patience_cap: Optional[float] = 300.0
    queue_patience_cap: Optional[float] = 1900.0
    ring_to_queue_prob: float = 0.98  # after ringing out, share who continue waiting in queue
    inefficiency_share: float = 0.50  # fraction of shift lost to breaks
    min_capacity: int = 0  # optional minimum guaranteed capacity (e.g., backup agent)
    call_types: Dict[str, CallTypeConfig] = dc.field(default_factory=dict)
    extra_agents_windows: List[ExtraAgentWindow] = dc.field(default_factory=list)

    def lognormal_params(self, call_type: Optional[str] = None) -> Tuple[float, float]:
        # mean = exp(mu + 0.5*sigma^2), cv^2 = exp(sigma^2) - 1
        if call_type and call_type in self.call_types:
            return self.call_types[call_type].lognormal_params()
        if self.mean_handle is None:
            raise ValueError(f"Service {self.name} missing mean_handle for call_type={call_type}")
        cv2 = self.handle_scatter ** 2
        sigma2 = math.log(1 + cv2)
        mu = math.log(self.mean_handle) - 0.5 * sigma2
        return mu, math.sqrt(sigma2)

@dc.dataclass
class ModelConfig:
    # Simulation horizon: 08:00 to 21:00
    T_START: int = 0
    T_END: int = (21 - 8) * 3600  # seconds
    seed: int = 42

    # Hourly arrivals (expected calls per hour) for 08..20 local hours.
    exams_hourly: Dict[int, float] = dc.field(default_factory=lambda: {
        8: 16, 9: 48, 10: 56, 11: 52, 12: 20, 13: 32, 14: 56, 15: 52, 16: 44, 17: 20, 18: 12, 19: 8, 20: 4
    })
    consults_hourly: Dict[int, float] = dc.field(default_factory=lambda: {
        8: 15, 9: 42, 10: 52, 11: 47, 12: 19, 13: 34, 14: 54, 15: 52, 16: 42, 17: 19, 18: 9, 19: 0, 20: 0
    })

    # Baseline service configs
    exams: ServiceConfig = dc.field(default_factory=lambda: ServiceConfig(
        name="exams",
        n_agents=3,
        shift_start=0,
        shift_end=(21 - 8) * 3600,
        inefficiency_share=0.43,
        mean_handle=180,
        call_types={
            "first_contact": CallTypeConfig(probability=0.2767, mean_handle=150),
            "appointment": CallTypeConfig(probability=0.2674, mean_handle=210),
            "doubts": CallTypeConfig(probability=0.3593, mean_handle=190),
            "transfer": CallTypeConfig(probability=0.0965, mean_handle=220),
        },
    ))
    consults: ServiceConfig = dc.field(default_factory=lambda: ServiceConfig(
        name="consults",
        n_agents=2,
        shift_start=0,
        shift_end=(18 - 8) * 3600,
        min_capacity=1,  # keep at least one active agent; backup support modeled via extra_agents_windows
        ring_patience_mean=160,
        queue_patience_mean=1300,
        ring_to_queue_prob=0.99,
        mean_handle=210,
        call_types={
            "appointment": CallTypeConfig(probability=0.3051, mean_handle=230),
            "transfer": CallTypeConfig(probability=0.1645, mean_handle=170),
            "doubts_rescheduling": CallTypeConfig(probability=0.5304, mean_handle=200),
        },
        extra_agents_windows=[
            ExtraAgentWindow(
                start=(10 - 8) * 3600,  # targeted backup during mid-day peak/absences
                end=(15 - 8) * 3600,
                extra_agents=1,  # approximates a backup agent when one of two is unavailable
            )
        ],
    ))
