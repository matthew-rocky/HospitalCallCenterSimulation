from __future__ import annotations
import dataclasses as dc
from typing import Tuple, Optional
try:
    from .config import ServiceConfig, ModelConfig
    from .resources import AgentPool
except ImportError:  # allow running as standalone scripts
    from config import ServiceConfig, ModelConfig
    from resources import AgentPool
import simpy

class ScenarioConfig:
    """
    Scenario definitions based on the validation and experimentation design
    described in the hospital call-center V&V study (WSC 2018).

    Supported Scenarios
    -------------------
    • baseline
        Represents the original system configuration.
        Exams and Consults operate independently with their default staffing.
        Ring stage is active.

    • ring_cancel   (Scenario #1)
        Removes the ringing stage entirely. Calls enter the queue immediately.
        No staffing changes are applied.

    • schedule      (Scenario #2)
        Workforce reinforcement scenario:
            - Exams service receives +2 additional agents.
            - Consultations service receives +1 additional agent.
        The ring stage is also removed (inherits ring_cancel).

    • centralize    (Scenario #3)
        Fully centralized service model:
            - Merges Exams and Consults into a single unified agent pool.
            - Inherits all schedule adjustments from Scenario #2.
            - Ring stage remains cancelled.
            - Effective capacity becomes the sum of both services.

    These scenarios allow direct comparison of operational performance
    under structural, behavioral, and staffing modifications, consistent
    with the experiments reported in the V&V paper.
    """

    def __init__(self, model_cfg: ModelConfig, scenario: str):
        self.model_cfg = model_cfg
        self.scenario = scenario
        self.ring_cancel = False
        self.centralize = False

        self.exams_cfg = dc.replace(model_cfg.exams)
        self.consults_cfg = dc.replace(model_cfg.consults)

        if scenario == "ring_cancel":
            self.ring_cancel = True  # Scenario #1 removes the ringing stage
        elif scenario == "schedule":
            self.exams_cfg.n_agents += 2  # Scenario #2 adds two exam agents
            self.consults_cfg.n_agents += 1  # Scenario #2 adds one consult agent
            self.ring_cancel = True  # Scenario #2 still cancels ringing
        elif scenario == "centralize":
            self.exams_cfg.n_agents += 2  # Scenario #3 inherits schedule staffing
            self.consults_cfg.n_agents += 1
            self.ring_cancel = True  # Scenario #3 also cancels ringing
            self.centralize = True  # Scenario #3 merges pools

    def build_pools(self, env: simpy.Environment) -> Tuple[Optional[AgentPool], Optional[AgentPool], Optional[AgentPool]]:
        if self.centralize:
            merged = ServiceConfig(  # Scenario #3 creates a combined pool per the paper
                name="merged",
                n_agents=self.exams_cfg.n_agents + self.consults_cfg.n_agents,
                shift_start=min(self.exams_cfg.shift_start, self.consults_cfg.shift_start),
                shift_end=max(self.exams_cfg.shift_end, self.consults_cfg.shift_end),
                mean_handle=(self.exams_cfg.mean_handle + self.consults_cfg.mean_handle) / 2,
                handle_scatter=max(self.exams_cfg.handle_scatter, self.consults_cfg.handle_scatter),
                ring_cycle=self.exams_cfg.ring_cycle,
                sla_threshold=min(self.exams_cfg.sla_threshold, self.consults_cfg.sla_threshold),
                ring_patience_mean=min(self.exams_cfg.ring_patience_mean, self.consults_cfg.ring_patience_mean),
                queue_patience_mean=min(self.exams_cfg.queue_patience_mean, self.consults_cfg.queue_patience_mean),
                inefficiency_share=max(self.exams_cfg.inefficiency_share, self.consults_cfg.inefficiency_share),
            )
            return None, None, AgentPool(env, merged)
        else:
            return AgentPool(env, self.exams_cfg), AgentPool(env, self.consults_cfg), None
