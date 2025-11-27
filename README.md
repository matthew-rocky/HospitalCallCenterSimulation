# Simulation and Validation of a Children’s Hospital Call Center  
### SYS 5110 — Modelling & Simulation (Fall 2025)  
### University of Ottawa 

---

# Table of Contents
- [1. Project Overview](#project-overview)
- [2. Objectives](#objectives)
- [3. System Architecture](#system-architecture)
- [4. Model Behavior Description](#model-behavior-description)
- [5. How to Run the Project](#how-to-run-the-project)
- [6. Key Performance Indicators (KPIs)](#key-performance-indicators-kpis)
- [7. Project Status](#project-status)
- [8. Limitations & Assumptions](#limitations--assumptions)
- [9. Reference](#reference)

---

------------------------------------------------------------
PROJECT OVERVIEW
------------------------------------------------------------
This project presents a fully developed Discrete-Event Simulation (DES) of a
children’s hospital call center responsible for scheduling appointments for two
types of services:

• Exams (diagnostic imaging, tests)

• Consultations (medical assessment appointments)

The goal of the simulation is to model the incoming call flow, queueing
behavior, ringing behavior, abandonment patterns, agent workloads, staffing
constraints, and different operational scenarios in order to analyze system
performance and identify meaningful improvements.

------------------------------------------------------------
OBJECTIVES
------------------------------------------------------------
• Build an accurate, modular discrete-event simulation of a real-world
  hospital call center.


• Represent all essential behaviors:

  - Time-varying arrival rates
  - Ringing stage with cyclic attempts
  - Ring abandonment
  - Queueing and queue abandonment
  - Service handling times with lognormal distributions
  - Agent inefficiency (~40% of shift)
  - Distinct call-type behavior per service


• Experiment with multiple system-improvement scenarios:

  - Scenario #1: Remove ring stage (“ring_cancel”)
  - Scenario #2: Add staffing (“schedule”)
  - Scenario #3: Merge services (“centralize”)


• Validate system performance using key indicators:

  - Abandonment rate
  - SLA (calls answered within 10 seconds)
  - Queue waiting time
  - Handle time
  - Agent utilization

• Provide an interactive visualization interface through Streamlit.

------------------------------------------------------------
SYSTEM ARCHITECTURE
------------------------------------------------------------
The project is organized into modular Python files for clarity,
reusability, and maintainability.

Directory layout:

    project/
      arrivals.py        - Time-varying arrival generator (NHPP)
      config.py          - Model parameters and global configuration
      model.py           - Core DES logic: ringing, queueing, service flow
      resources.py       - Agent pools, inefficiency modeling
      scenarios.py       - Baseline, ring_cancel, schedule, centralize
      metrics.py         - KPI tracking and statistics
      validation.py      - Experiment replications & V&V utilities
      run.py             - Simulation runner and CLI entry point
      streamlit_app.py   - Streamlit dashboard for visualization


------------------------------------------------------------
## MODEL BEHAVIOR DESCRIPTION
------------------------------------------------------------

4.1 Time-Varying Arrivals (NHPP)
Calls arrive according to a Nonhomogeneous Poisson Process (NHPP).  
Hourly arrival rates create realistic daily patterns:
- Morning peak
- Midday decline
- Afternoon rise

------------------------------------------------------------

4.2 Ringing Stage & Abandonment
When a call arrives:
1. Caller enters a 15‑second ringing cycle.
2. If an agent becomes available, the call is answered.
3. If not, the call continues ringing in cycles.
4. If total ringing exceeds ring‑patience (mean ≈ 60s), the caller abandons.

This models realistic “ring → ring → hang up” behavior.

------------------------------------------------------------

4.3 Queueing Stage & Abandonment
If a caller survives the ringing stage:
1. They join a FIFO queue.
2. Waiting time accumulates until an agent is available.
3. If waiting exceeds queue‑patience (mean ≈ 120s), the caller abandons.
4. Queue‑waiting KPIs include only non‑zero waits.

------------------------------------------------------------

4.4 Call-Type Handling
Each service (Exam and Consultation) includes multiple call types:
- First contact
- Appointment booking
- Doubts / clarification
- Transfers

Each call type has:
- A unique probability of occurrence
- A lognormal service‑time distribution

------------------------------------------------------------

4.5 Agent Inefficiency (~40%)
Agents are not available for calls 100% of the time.  
Shift-time losses (~40%) come from:
- Breaks
- Meetings
- Administrative duties
- Interruptions

This is modeled as temporary capacity reductions.

------------------------------------------------------------

4.6 Scenario Definitions (from WSC 2018)

Scenario 0: baseline
- Independent Exam & Consult services
- Ring stage active
- Original staffing levels

Scenario 1: ring_cancel
- Removes ring stage
- Calls go directly to the queue

Scenario 2: schedule
- Adds +2 Exam agents
- Adds +1 Consult agent
- Inherits ring cancellation

Scenario 3: centralize
- Merges all agents into one pool
- Inherits added staffing
- Inherits ring cancellation


------------------------------------------------------------
HOW TO RUN THE PROJECT
------------------------------------------------------------

5.1 Install Dependencies
Install required Python packages:

    pip install simpy streamlit pandas numpy

5.1.1 Requirements

    Python 3.10+
    SimPy
    NumPy
    Pandas
    Streamlit
    Matplotlib / Plotly (optional)

5.1.2 Install everything via:

    pip install -r requirements.txt


5.2 Launch the Streamlit Dashboard

    streamlit run streamlit_app.py

5.3 Run a Simulation Programmatically

    from config import ModelConfig
    from run import run_once

    cfg = ModelConfig(seed=42)
    result = run_once(cfg, "baseline")
    print(result)

5.4 Multiple Replications + Statistics

    from validation import run_experiment, summarize_statistics

    cfg = ModelConfig()
    reps = run_experiment(cfg, "schedule", 50)
    stats = summarize_statistics(reps)
    print(stats)
------------------------------------------------------------
Results and Insights
------------------------------------------------------------
The model reveals how operational decisions affect:

• Abandonment levels

• Waiting time distributions

• Agent utilization

• Service level achievement

• Queueing behavior

• Patient experience

Across the four scenarios, the Full Centralization configuration consistently produced the best performance due to pooled variability and improved resource sharing.


------------------------------------------------------------
My Contribution
------------------------------------------------------------
I independently developed the full simulation engine, implemented all scenario configurations, built the Streamlit dashboard, and authored the complete final report.

------------------------------------------------------------
KEY PERFORMANCE INDICATORS (KPIs)
------------------------------------------------------------
The model generates:

• Abandonment rate  
• SLA (calls answered within 10 seconds)  
• Average queue waiting time (non-zero only)  
• Average handle time  
• Arrivals & answered calls  
• Agent utilization  

------------------------------------------------------------
PROJECT STATUS
------------------------------------------------------------
✔ Simulation model fully completed

✔ All four scenarios working

✔ Streamlit dashboard finished with charts and tables

✔ Validation module completed with replications and confidence intervals

✔ All KPIs implemented (arrivals, answered, abandonment, SLA, waits, handles, utilization)

✔ Scenario engine fully functional

✔ Time-varying arrivals implemented with NHPP

✔ All visualizations working (queue length, wait times, handle times)

✔ About 1130 total lines of code (820 executable lines)


------------------------------------------------------------
LIMITATIONS & ASSUMPTIONS
------------------------------------------------------------
• Break patterns are stochastic rather than fixed.  
• Patience modeled with exponential distributions.  
• Handle times follow lognormal assumptions.  
• Some real-world behaviors are approximated based on the paper.

------------------------------------------------------------
REFERENCE
------------------------------------------------------------
Pisaniello, Angelo, et al. “DISCRETE EVENT SIMULATION OF APPOINTMENTS HANDLING AT A CHILDREN’S HOSPITAL CALL CENTER: LESSONS LEARNED FROM V&V PROCESS.” 2018 Winter Simulation Conference (WSC), IEEE, 2018, pp. 3861–72, https://doi.org/10.1109/WSC.2018.8632466.
