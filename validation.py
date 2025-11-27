from __future__ import annotations

import copy
import math
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from config import ModelConfig
from run import run_once, aggregate

MetricBlock = Dict[str, Dict[str, float]]
ExperimentResults = List[MetricBlock]
Statistic = Dict[str, float]
DEFAULT_METRICS = [
    "abandon_rate",
    "sla_all_calls",  # paper definition: denominator = inbound calls
    "sla_within_10s",
    "avg_queue_wait_nonzero_s",
    "avg_handle_time_s",
]


def run_experiment(cfg: ModelConfig, scenario: str, replications: int, seed: Optional[int] = None) -> ExperimentResults:
    """Run multiple independent replications for a given scenario."""
    base_seed = cfg.seed if seed is None else seed
    results: ExperimentResults = []
    for r in range(replications):
        rep_seed = base_seed + r
        results.append(run_once(cfg, scenario, seed=rep_seed))
    return results


def _describe(samples: Sequence[float]) -> Statistic:
    n = len(samples)
    mean = sum(samples) / n if n else 0.0
    if n <= 1:
        return {"n": float(n), "mean": mean, "std": 0.0, "ci_low": mean, "ci_high": mean}
    variance = sum((x - mean) ** 2 for x in samples) / (n - 1)
    std = math.sqrt(variance)
    half_width = 1.96 * std / math.sqrt(n)
    return {
        "n": float(n),
        "mean": mean,
        "std": std,
        "ci_low": mean - half_width,
        "ci_high": mean + half_width,
    }


def summarize_statistics(
    results: ExperimentResults,
    services: Optional[Iterable[str]] = None,
    metrics: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Statistic]]:
    """Operational-validation summary per the paper: compute means/std/95% CIs for each service/metric."""
    if not results:
        return {}
    services = list(services) if services is not None else list(results[0].keys())
    metrics = list(metrics) if metrics is not None else DEFAULT_METRICS
    summary: Dict[str, Dict[str, Statistic]] = {}
    for service in services:
        service_stats: Dict[str, Statistic] = {}
        for metric in metrics:
            samples = [
                rep[service][metric]
                for rep in results
                if service in rep and metric in rep[service]
            ]
            if samples:
                service_stats[metric] = _describe(samples)
        if service_stats:
            summary[service] = service_stats
    return summary


def paired_difference(
    baseline: ExperimentResults,
    challenger: ExperimentResults,
    services: Optional[Iterable[str]] = None,
    metrics: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, Statistic]]:
    """Paper-style paired scenario comparison with CI analysis (challenger − baseline)."""
    n = min(len(baseline), len(challenger))
    if n == 0:
        return {}
    services = list(services) if services is not None else list(baseline[0].keys())
    metrics = list(metrics) if metrics is not None else DEFAULT_METRICS
    summary: Dict[str, Dict[str, Statistic]] = {}
    for service in services:
        svc_stats: Dict[str, Statistic] = {}
        for metric in metrics:
            diffs: List[float] = []
            for idx in range(n):
                base_block = baseline[idx].get(service, {})
                chall_block = challenger[idx].get(service, {})
                if metric in base_block and metric in chall_block:
                    diffs.append(chall_block[metric] - base_block[metric])
            if diffs:
                svc_stats[metric] = _describe(diffs)
        if svc_stats:
            summary[service] = svc_stats
    return summary


Modifier = Callable[[ModelConfig], None]
Variation = Tuple[str, Modifier]


def sensitivity_sweep(
    base_cfg: ModelConfig,
    scenario: str,
    variations: Sequence[Variation],
    replications: int,
    seed: Optional[int] = None,
    metrics: Optional[Iterable[str]] = None,
) -> List[Dict[str, object]]:
    """Run a simple sensitivity analysis over a set of config variations."""
    results: List[Dict[str, object]] = []
    for label, modifier in variations:
        cfg_variant = copy.deepcopy(base_cfg)
        modifier(cfg_variant)
        reps = run_experiment(cfg_variant, scenario, replications, seed=seed)
        stats = summarize_statistics(reps, metrics=metrics)
        results.append(
            {
                "label": label,
                "cfg": cfg_variant,
                "stats": stats,
                "raw": reps,
            }
        )
    return results


def calibrate_baseline(cfg: ModelConfig, n_reps: int = 50) -> Dict[str, Dict[str, float]]:
    """
    Run the baseline scenario for n_reps replications and return average KPIs
    aligned with the paper's definitions (SLA over all inbound calls).
    Targets: exams SLA_all_calls≈0.24, consults SLA_all_calls≈0.17,
    abandonment in the 20–35% band, with queue/handle times unchanged.
    """
    reps = run_experiment(cfg, "baseline", n_reps, seed=cfg.seed)
    agg = aggregate(reps)
    summary: Dict[str, Dict[str, float]] = {}
    print(f"Baseline calibration (mean over {n_reps} replications)")
    for svc in ("exams", "consults"):
        if svc not in agg:
            continue
        svc_metrics = agg[svc]
        summary[svc] = {
            "arrivals": svc_metrics["arrivals"],
            "abandon_rate": svc_metrics["abandon_rate"],
            "sla_all_calls": svc_metrics.get("sla_all_calls", svc_metrics.get("sla_within_10s", 0.0)),
            "sla_within_10s": svc_metrics.get("sla_within_10s", 0.0),
            "avg_queue_wait_nonzero_s": svc_metrics["avg_queue_wait_nonzero_s"],
            "avg_handle_time_s": svc_metrics["avg_handle_time_s"],
        }
        print(
            f"{svc.title()}: arrivals={summary[svc]['arrivals']:.1f}, "
            f"abandon={summary[svc]['abandon_rate']*100:.1f}%, "
            f"SLA_all={summary[svc]['sla_all_calls']*100:.1f}%, "
            f"SLA_answered={summary[svc]['sla_within_10s']*100:.1f}%, "
            f"q_wait>0={summary[svc]['avg_queue_wait_nonzero_s']:.1f}s, "
            f"handle={summary[svc]['avg_handle_time_s']:.1f}s"
        )
    # Expected tuned baseline KPIs should hover near the WSC 2018 paper:
    # Exams SLA_all_calls≈24%, abandon≈20–30%; Consults SLA_all_calls≈17%, abandon≈25–35%.
    return summary


def arrival_multiplier(service: str, multiplier: float) -> Modifier:
    """Scale the hourly arrival table for the selected service."""
    def _modifier(cfg: ModelConfig) -> None:
        table = cfg.exams_hourly if service == "exams" else cfg.consults_hourly
        for hour in list(table.keys()):
            table[hour] *= multiplier
    return _modifier


def staffing_shift(service: str, delta_agents: int) -> Modifier:
    """Adjust the staffing level for a service."""
    def _modifier(cfg: ModelConfig) -> None:
        svc = cfg.exams if service == "exams" else cfg.consults
        svc.n_agents = max(0, svc.n_agents + delta_agents)
    return _modifier


def patience_multiplier(service: str, stage: str, multiplier: float) -> Modifier:
    """Scale patience parameters (ring or queue) for a service."""
    if stage not in {"ring", "queue"}:
        raise ValueError("stage must be 'ring' or 'queue'")

    def _modifier(cfg: ModelConfig) -> None:
        svc = cfg.exams if service == "exams" else cfg.consults
        field = "ring_patience_mean" if stage == "ring" else "queue_patience_mean"
        current = getattr(svc, field)
        setattr(svc, field, max(0.0, current * multiplier))
    return _modifier
