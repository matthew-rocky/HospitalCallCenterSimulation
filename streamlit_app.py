from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import altair as alt
import matplotlib

# UPDATED: force non-GUI backend to avoid Streamlit thread warning
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from config import ModelConfig
from run import SCENARIOS, aggregate, run_once


def _simulate_impl(scenario: str, replications: int, seed: int) -> Dict[str, Dict[str, float]]:
    """Run the call-center DES several times and return the averaged KPIs."""
    cfg = ModelConfig(seed=seed)
    results = [run_once(cfg, scenario, seed=seed + idx) for idx in range(replications)]
    return aggregate(results)


def _has_streamlit_runtime() -> bool:
    try:
        from streamlit import runtime

        return runtime.exists()
    except Exception:
        return False


def simulate(scenario: str, replications: int, seed: int) -> Dict[str, Dict[str, float]]:
    """Dispatch to cached simulation only when Streamlit runtime is active."""
    if not hasattr(simulate, "_cached_fn"):
        simulate._cached_fn = None  # type: ignore[attr-defined]

    if _has_streamlit_runtime():
        if simulate._cached_fn is None:  # type: ignore[attr-defined]
            simulate._cached_fn = st.cache_data(show_spinner=False)(_simulate_impl)  # type: ignore[attr-defined]
        return simulate._cached_fn(scenario, replications, seed)  # type: ignore[attr-defined]
    return _simulate_impl(scenario, replications, seed)


def _launch_streamlit_server() -> None:
    """Programmatically start the Streamlit runtime so running this file locally opens the web UI."""
    from streamlit.web import bootstrap

    script_path = Path(__file__).resolve()
    headless = os.getenv("STREAMLIT_HEADLESS", "").lower() in {"1", "true", "yes"}
    port = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    flag_options = {
        "server.headless": headless,
        "server.port": port,
        "global.developmentMode": False,
    }
    bootstrap.run(str(script_path), False, [], flag_options)


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def layout_service_section(name: str, metrics: Dict[str, float]) -> None:
    st.subheader(f"{name.title()} Performance")
    sla_all = metrics.get("sla_all_calls", metrics.get("sla_within_10s", 0.0))
    sla_answered = metrics.get("sla_within_10s", 0.0)
    cols = st.columns(3)
    cols[0].metric("Arrivals", f"{metrics['arrivals']:.1f}")
    cols[1].metric("Answered", f"{metrics['answered']:.1f}")
    cols[2].metric("Abandonment", format_percent(metrics["abandon_rate"]))

    cols = st.columns(3)
    cols[0].metric("Avg Queue Wait (>0)", f"{metrics['avg_queue_wait_nonzero_s']:.1f}s")
    cols[1].metric("Avg Handle Time", f"{metrics['avg_handle_time_s']:.1f}s")
    cols[2].metric("SLA <=10s (all inbound)", format_percent(sla_all))
    st.caption(f"SLA on answered-only basis: {format_percent(sla_answered)}")


def _extract_utilization(agg: Dict[str, Dict[str, float]], service_key: str) -> float | None:
    util = agg.get(f"utilization_{service_key}", {}).get("util")
    if util is not None:
        return util
    return agg.get("utilization_merged", {}).get("util")


def build_export_dataframe(all_results: Dict[str, Dict[str, Dict[str, float]]]) -> pd.DataFrame:
    """Flatten scenario outputs into a CSV-friendly table with core KPIs."""
    rows = []
    for scenario_name, agg in all_results.items():
        for service_key in ("exams", "consults"):
            if service_key not in agg:
                continue
            metrics = agg[service_key]
            row = {
                "Scenario": scenario_name.replace("_", " ").title(),
                "Service": service_key.title(),
                "Arrivals": metrics.get("arrivals", 0.0),
                "Answered": metrics.get("answered", 0.0),
                "Avg Queue Wait (s)": metrics.get("avg_queue_wait_nonzero_s", 0.0),
                "Avg Handle (s)": metrics.get("avg_handle_time_s", 0.0),
                "Abandonment %": metrics.get("abandon_rate", 0.0) * 100,
                "SLA <=10s (all calls) %": metrics.get("sla_all_calls", metrics.get("sla_within_10s", 0.0)) * 100,
                "SLA <=10s (answered) %": metrics.get("sla_within_10s", 0.0) * 100,
            }
            util = _extract_utilization(agg, service_key)
            if util is not None:
                row["Utilization %"] = util * 100
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    if not _has_streamlit_runtime():
        print("Starting Streamlit server at http://localhost:8501 ...")
        _launch_streamlit_server()
        return

    st.set_page_config(page_title="Hospital Call Center DES", layout="wide")
    st.title("Simulation and Validation of a Children’s Hospital Call Center Appointment Scheduling System (Group 1)")
    st.write(
        "Interactively explore scenario designs for the hospital call center. "
        "Results are averages across multiple Monte Carlo replications."
    )

    with st.sidebar:
        st.header("Simulation Controls")
        scenario = st.selectbox("Scenario", SCENARIOS, index=0, format_func=str.capitalize)
        replications = st.slider("Replications", min_value=5, max_value=200, value=25, step=5)
        seed = st.number_input("Base random seed", min_value=0, value=42, help="Used to initialize each replication.")
        st.caption("Changes re-run the simulation automatically.")

        st.markdown("**Group Members**")
        members = [
            "Matthew Rocky",
            "Dima AlQaruoti",
            "Salwa Kouttane",
        ]
        lines = []
        for entry in members:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                name, sid = entry
                label = f"{name} ({sid})"
                if len(label) > 36:
                    label = name
            else:
                label = str(entry)
            lines.append(f"- {label}")
        st.markdown("\n".join(lines))


    with st.spinner("Running simulation..."):
        agg = simulate(scenario, replications, seed)

    service_keys = [key for key in ("exams", "consults") if key in agg]
    for key in service_keys:
        layout_service_section(key, agg[key])

    if service_keys:
        service_df = pd.DataFrame(
            {
                "Service": [name.title() for name in service_keys],
                "Arrivals": [agg[name]["arrivals"] for name in service_keys],
                "Answered": [agg[name]["answered"] for name in service_keys],
                "Avg Queue Wait (s)": [agg[name]["avg_queue_wait_nonzero_s"] for name in service_keys],
                "Avg Handle (s)": [agg[name]["avg_handle_time_s"] for name in service_keys],
                "Abandonment %": [agg[name]["abandon_rate"] * 100 for name in service_keys],
                "SLA <=10s (all calls) %": [
                    agg[name].get("sla_all_calls", agg[name].get("sla_within_10s", 0.0)) * 100
                    for name in service_keys
                ],
                "SLA <=10s (answered) %": [agg[name].get("sla_within_10s", 0.0) * 100 for name in service_keys],
            }
        ).set_index("Service")

        # UPDATED: unified KPI charts to Altair style
        # UPDATED: 2x2 layout for top KPI charts
        bar_palette = ["#5B8FF9", "#61DDAA", "#EF476F", "#06D6A0"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Arrival vs Answered Volume")
            arrivals_long = (
                service_df.reset_index()
                .melt(id_vars="Service", value_vars=["Arrivals", "Answered"], var_name="Metric", value_name="Value")
            )
            arrivals_chart = (
                alt.Chart(arrivals_long)
                .mark_bar()
                .encode(
                    x=alt.X("Service:N", title="Service"),
                    xOffset="Metric:N",
                    y=alt.Y("Value:Q", title="Volume"),
                    color=alt.Color("Metric:N", scale=alt.Scale(range=bar_palette[:2]), legend=alt.Legend(title="Metric")),
                    tooltip=["Service", "Metric", alt.Tooltip("Value:Q", format=".1f")],
                )
                .properties(height=250)
            )
            st.altair_chart(arrivals_chart, width="stretch")

        with col2:
            st.markdown("### Queue + Handle Time")
            time_long = (
                service_df.reset_index()
                .melt(id_vars="Service", value_vars=["Avg Queue Wait (s)", "Avg Handle (s)"],
                      var_name="Metric", value_name="Value")
            )
            time_chart = (
                alt.Chart(time_long)
                .mark_bar()
                .encode(
                    x=alt.X("Service:N", title="Service"),
                    xOffset="Metric:N",
                    y=alt.Y("Value:Q", title="Seconds"),
                    color=alt.Color("Metric:N", scale=alt.Scale(range=bar_palette[:2]), legend=alt.Legend(title="Metric")),
                    tooltip=["Service", "Metric", alt.Tooltip("Value:Q", format=".1f")],
                )
                .properties(height=250)
            )
            st.altair_chart(time_chart, width="stretch")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("### Reliability Metrics")
            reliability_long = (
                service_df.reset_index()
                .melt(id_vars="Service",
                      value_vars=["Abandonment %", "SLA <=10s (all calls) %", "SLA <=10s (answered) %"],
                      var_name="Metric", value_name="Value")
            )
            reliability_chart = (
                alt.Chart(reliability_long)
                .mark_bar()
                .encode(
                    x=alt.X("Service:N", title="Service"),
                    xOffset="Metric:N",
                    y=alt.Y("Value:Q", title="Percent"),
                    color=alt.Color("Metric:N", scale=alt.Scale(range=bar_palette[:3]),
                                    legend=alt.Legend(title="Metric")),
                    tooltip=["Service", "Metric", alt.Tooltip("Value:Q", format=".1f")],
                )
                .properties(height=250)
            )
            st.altair_chart(reliability_chart, width="stretch")

        with col4:
            st.markdown("### Agent Pool Utilization")
            util_keys = [key for key in agg if key.startswith("utilization")]
            if util_keys:
                util_df = pd.DataFrame(
                    {
                        "Pool": [key.replace("utilization_", "").title() for key in util_keys],
                        "Utilization": [agg[key]["util"] * 100 for key in util_keys],
                    }
                ).set_index("Pool")
                util_chart = (
                    alt.Chart(util_df.reset_index())
                    .mark_bar()
                    .encode(
                        x=alt.X("Pool:N", title="Service"),
                        y=alt.Y("Utilization:Q", title="Utilization (%)"),
                        color=alt.Color("Pool:N", scale=alt.Scale(range=bar_palette[:2]),
                                        legend=alt.Legend(title="Service")),
                        tooltip=["Pool", alt.Tooltip("Utilization:Q", format=".1f")],
                    )
                    .properties(height=250)
                )
                st.altair_chart(util_chart, width="stretch")

        st.markdown("#### Detailed Table")
        st.dataframe(service_df.style.format(
            {
                "Arrivals": "{:.1f}",
                "Answered": "{:.1f}",
                "Avg Queue Wait (s)": "{:.1f}",
                "Avg Handle (s)": "{:.1f}",
                "Abandonment %": "{:.1f}",
                "SLA <=10s (all calls) %": "{:.1f}",
                "SLA <=10s (answered) %": "{:.1f}",
            }
        ))

        st.markdown("#### Export")
        csv_state_key = "csv_all_scenarios"
        if st.button("Generate CSV for all scenarios", type="primary"):
            with st.spinner("Running all scenarios and preparing CSV..."):
                all_results = {name: simulate(name, replications, seed) for name in SCENARIOS}
                export_df = build_export_dataframe(all_results)
                st.session_state[csv_state_key] = export_df.to_csv(index=False).encode("utf-8")

        if csv_state_key in st.session_state:
            st.download_button(
                "Download all scenarios (CSV)",
                data=st.session_state[csv_state_key],
                file_name="call_center_all_scenarios.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # UPDATED: Dark-theme styling for Matplotlib plots
    def _themed_fig_ax():
        bg = st.get_option("theme.backgroundColor")
        txt = st.get_option("theme.textColor")
        if not bg or not txt:
            plt.style.use("default")
            fig, ax = plt.subplots()
        else:
            fig, ax = plt.subplots()
            fig.patch.set_facecolor(bg)
            ax.set_facecolor(bg)
            ax.tick_params(colors=txt)
            for spine in ax.spines.values():
                spine.set_color(txt)
            ax.xaxis.label.set_color(txt)
            ax.yaxis.label.set_color(txt)
            ax.title.set_color(txt)
        return fig, ax

    # UPDATED: Detailed Distributions section
    if service_keys:
        st.markdown("---")
        st.markdown("## Detailed Distributions")

        with st.expander("Queue Waiting Time Distribution", expanded=True):
            st.markdown("### Queue Waiting Time Distribution")
            cols = st.columns(len(service_keys))
            for col, key in zip(cols, service_keys):
                waits = agg[key].get("queue_wait_samples", [])
                fig, ax = _themed_fig_ax()
                if waits:
                    ax.hist(waits, bins=20, color="#5b8ff9", edgecolor="white")
                    ax.set_ylabel("Frequency")
                else:
                    ax.text(0.5, 0.5, "No non-zero waits recorded", ha="center", va="center")
                ax.set_xlabel("Waiting time (seconds)")
                ax.set_title(f"{key.title()} queue waits")
                col.pyplot(fig)

        with st.expander("Queue Length Over the Day", expanded=True):
            st.markdown("### Queue Length Over the Day")
            cols = st.columns(len(service_keys))
            for col, key in zip(cols, service_keys):
                trace = agg[key].get("queue_length_trace", [])
                fig, ax = _themed_fig_ax()
                if trace:
                    trace_sorted = sorted(trace, key=lambda x: x[0])
                    times = [t / 60.0 for t, _ in trace_sorted]  # convert seconds to minutes
                    lengths = [l for _, l in trace_sorted]
                    ax.plot(times, lengths, color="#52c41a", linewidth=2)
                    ax.set_ylabel("Queue length")
                else:
                    ax.text(0.5, 0.5, "No queueing observed", ha="center", va="center")
                ax.set_xlabel("Time (minutes)")
                ax.set_title(f"{key.title()} queue length")
                col.pyplot(fig)

        with st.expander("Handle Time Distribution", expanded=True):
            st.markdown("### Handle Time Distribution")
            cols = st.columns(len(service_keys))
            for col, key in zip(cols, service_keys):
                handles = agg[key].get("handle_time_samples", [])
                fig, ax = _themed_fig_ax()
                if handles:
                    ax.hist(handles, bins=20, color="#fa8c16", edgecolor="white")
                    ax.set_ylabel("Frequency")
                else:
                    ax.text(0.5, 0.5, "No handle times recorded", ha="center", va="center")
                ax.set_xlabel("Handle time (seconds)")
                ax.set_title(f"{key.title()} handle times")
                col.pyplot(fig)


if __name__ == "__main__":
    main()
