from __future__ import annotations
import random
from typing import Dict, List
import simpy
try:
    from .config import ModelConfig
    from .model import CallCenter
except ImportError:  # allow running as a script without package context
    from config import ModelConfig
    from model import CallCenter

SCENARIOS = ["baseline", "ring_cancel", "schedule", "centralize"]

def run_once(cfg: ModelConfig, scenario: str, seed: int | None = None) -> Dict[str, Dict[str, float]]:
    env = simpy.Environment()
    base_seed = seed if seed is not None else cfg.seed + random.randint(0, 10_000)
    random.seed(base_seed)
    model = CallCenter(env, cfg, scenario)
    env.run(until=cfg.T_END)
    return model.results()

def aggregate(dicts: List[Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    counts: Dict[str, float] = {}
    for d in dicts:
        for k, sub in d.items():
            if k not in out:
                out[k] = {}
                counts[k] = 0.0
            counts[k] += 1
            for m, v in sub.items():
                if isinstance(v, list):
                    out[k].setdefault(m, [])
                    out[k][m].extend(v)
                else:
                    out[k].setdefault(m, 0.0)
                    out[k][m] += v
    for k, sub in out.items():
        n = counts.get(k, 0.0)
        for m, v in list(sub.items()):
            if isinstance(v, list):
                continue
            sub[m] = v / n if n else v
    return out

def _launch_streamlit_from_cli() -> None:
    """Fallback entry that routes anyone running this module to the Streamlit UI."""
    try:
        from .streamlit_app import main as streamlit_main  # type: ignore
    except ImportError:
        from streamlit_app import main as streamlit_main

    print("`run.py` is no longer an executable entry point. Launching `streamlit_app.py` instead...\n")
    streamlit_main()


if __name__ == "__main__":
    _launch_streamlit_from_cli()
