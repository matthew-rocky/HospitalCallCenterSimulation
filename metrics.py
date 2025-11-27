from __future__ import annotations
import dataclasses as dc
from typing import Dict, List, Optional

@dc.dataclass
class KPIs:
    arrivals: int = 0
    answered: int = 0
    abandoned_ring: int = 0
    abandoned_queue: int = 0
    total_handle_time: float = 0.0
    queue_wait_sum_nonzero: float = 0.0
    queue_wait_count_nonzero: int = 0
    sla_hits: int = 0
    # ADDED: store raw samples for new visualizations
    queue_wait_samples: List[float] = dc.field(default_factory=list)
    handle_time_samples: List[float] = dc.field(default_factory=list)
    call_types_answered: Dict[str, int] = dc.field(default_factory=dict)

    def record_answered_type(self, call_type: Optional[str]):
        if not call_type:
            return
        self.call_types_answered[call_type] = self.call_types_answered.get(call_type, 0) + 1

    def summarize(self) -> Dict[str, float]:
        aband_total = self.abandoned_ring + self.abandoned_queue
        avg_q_nonzero = (self.queue_wait_sum_nonzero / self.queue_wait_count_nonzero
                          if self.queue_wait_count_nonzero else 0.0)  # excludes zero-wait calls per paper KPI
        avg_handle = (self.total_handle_time / self.answered) if self.answered else 0.0  # averages over answered calls only
        sla = (self.sla_hits / self.answered) if self.answered else 0.0  # SLA <=10s target comes from the paper
        sla_all_calls = (self.sla_hits / self.arrivals) if self.arrivals else 0.0  # paper denominator = all inbound calls
        aband_rate = (aband_total / self.arrivals) if self.arrivals else 0.0
        out = {
            "arrivals": self.arrivals,
            "answered": self.answered,
            "abandon_rate": aband_rate,
            "avg_queue_wait_nonzero_s": avg_q_nonzero,
            "avg_handle_time_s": avg_handle,
            "sla_within_10s": sla,
            "sla_all_calls": sla_all_calls,
        }
        for ctype, count in self.call_types_answered.items():
            out[f"answered_{ctype}"] = count
        # ADDED: expose raw samples for plotting
        out["queue_wait_samples"] = list(self.queue_wait_samples)
        out["handle_time_samples"] = list(self.handle_time_samples)
        return out
