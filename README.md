# Simulation and Validation of a Children’s Hospital Call Center  
### SYS 5110 — Modelling & Simulation (Fall 2025)  
### University of Ottawa 

A discrete-event simulation of a children’s hospital call center, modeling NHPP arrivals, ringing behavior, queue abandonment, and multi-service staffing. Built using SimPy with full scenario analysis and validation.
---

# Table of Contents
- [1. Project Overview](#project-overview)
- [2. Objectives](#objectives)
- [3. System Architecture](#system-architecture)
- [4. Model Behavior Description](#model-behavior-description)
- [5. How to Run the Project](#how-to-run-the-project)
- [6. Technologies Used](#Technologies-used)
- [7. Results and Insights](#Results-and-Insights)
- [8. My Contribution](#my-Contribution)
- [9. Key Performance Indicators (KPIs)](#key-performance-indicators-kpis)
- [10. Project Status](#project-status)
- [11. Limitations & Assumptions](#limitations--assumptions)
- [12. Sample Outputs](#Sample-Outputs)
- [13. Reference](#reference)

---

------------------------------------------------------------
PROJECT OVERVIEW
------------------------------------------------------------
This project presents a complete Discrete-Event Simulation (DES) of a children’s hospital call center responsible for handling appointment scheduling for two major services:

• Exams (diagnostic imaging, test bookings)

• Consultations (medical assessments)


The simulation models the full lifecycle of a call, including arrivals, ringing cycles, queueing, abandonment, service handling, and staffing interactions.
Its purpose is to evaluate operational performance under multiple system configurations and identify improvements supported by quantitative evidence.

------------------------------------------------------------
OBJECTIVES
------------------------------------------------------------
• Develop an accurate and modular discrete-event simulation based on a real children’s hospital call center.


• Represent key operational behaviors, including:

  - Time-varying (NHPP) arrival rates
  - Ringing stage with repeated attempts
  - Ringing abandonment
  - Queueing with patience-based abandonment
  - Lognormal service-time distributions
  - Agent inefficiency (~40% of shift unavailable)
  - Distinct behaviors for Exam vs. Consultation calls


• Evaluate multiple system-improvement scenarios:

  - Scenario #1: Remove ringing stage (“ring_cancel”)
  - Scenario #2: Add staffing (“schedule”)
  - Scenario #3: Merge all services (“centralize”)


• Validate performance using:

  - Abandonment rate
  - SLA (calls answered ≤10 seconds)
  - Queueing KPIs
  - Handle-time metrics
  - Agent utilization

• Provide an interactive visualization and results interface via Streamlit.

------------------------------------------------------------
SYSTEM ARCHITECTURE
------------------------------------------------------------
The project is fully modularized to support maintainability, clear logic separation, and scenario experimentation.

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

Time-Varying Arrivals (NHPP)
Calls arrive according to a Nonhomogeneous Poisson Process (NHPP).  
Hourly arrival rates create realistic daily patterns:
- Morning peak
- Midday decline
- Afternoon rise

------------------------------------------------------------

Ringing Stage & Abandonment
When a call arrives:
1. Caller enters a 15‑second ringing cycle.
2. If an agent becomes available, the call is answered.
3. If not, the call continues ringing in cycles.
4. If total ringing exceeds ring‑patience (mean ≈ 60s), the caller abandons.

This models realistic “ring → ring → hang up” behavior.

------------------------------------------------------------

Queueing Stage & Abandonment
If a caller survives the ringing stage:
1. They join a FIFO queue.
2. Waiting time accumulates until an agent is available.
3. If waiting exceeds queue‑patience (mean ≈ 120s), the caller abandons.
4. Queue‑waiting KPIs include only non‑zero waits.

------------------------------------------------------------

Call-Type Handling
Each service (Exam and Consultation) includes multiple call types:
- First contact
- Appointment booking
- Doubts / clarification
- Transfers

Each call type has:
- A unique probability of occurrence
- A lognormal service‑time distribution

------------------------------------------------------------

Agent Inefficiency (~40%)
Agents are not available for calls 100% of the time.  
Shift-time losses (~40%) come from:
- Breaks
- Meetings
- Administrative duties
- Interruptions

This is modeled as temporary capacity reductions.

------------------------------------------------------------

Scenario Definitions (from WSC 2018)

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

Install Dependencies
Install required Python packages:

    pip install simpy streamlit pandas numpy

Requirements

    Python 3.10+
    SimPy
    NumPy
    Pandas
    Streamlit
    Matplotlib / Plotly (optional)

Install everything via:

    pip install -r requirements.txt


Launch the Streamlit Dashboard

    streamlit run streamlit_app.py

Run a Simulation Programmatically

    from config import ModelConfig
    from run import run_once

    cfg = ModelConfig(seed=42)
    result = run_once(cfg, "baseline")
    print(result)

Multiple Replications + Statistics

    from validation import run_experiment, summarize_statistics

    cfg = ModelConfig()
    reps = run_experiment(cfg, "schedule", 50)
    stats = summarize_statistics(reps)
    print(stats)

------------------------------------------------------------
Technologies Used
------------------------------------------------------------

Python, SimPy, Streamlit, NumPy, Pandas, Matplotlib

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
• SLA performance (≤10 seconds)
• Average queue-wait time (non-zero)
• Average handle time
• Arrivals and answered calls
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
Output Samples
------------------------------------------------------------

### Baseline:
<p align="center">
  <img src="https://github.com/matthew-rocky/HospitalCallCenterSimulation/blob/main/sample_output/01%20-%20Baseline.jpg" width="700">
</p>

Baseline system performance showing high congestion, long queue waits, and elevated abandonment due to limited staffing and high demand.


### Ring Cancel:
<p align="center">
  <img src="https://github.com/matthew-rocky/HospitalCallCenterSimulation/blob/main/sample_output/02%20-%20Ring_Cancel.jpg" width="700">
</p>


Ringing stage removed: callers enter the queue immediately, reducing ringing abandonment but lowering SLA by increasing initial queue load.



### Schedule:
<p align="center">
  <img src="https://github.com/matthew-rocky/HospitalCallCenterSimulation/blob/main/sample_output/03%20-%20Schedule.jpg" width="700">
</p>


Staffing reinforcement with +2 Exam agents and +1 Consult agent significantly reduces waiting times and abandonment while improving SLA performance.



### Centralize:
<p align="center">
  <img src="https://github.com/matthew-rocky/HospitalCallCenterSimulation/blob/main/sample_output/04%20-%20Centralize.jpg" width="700">
</p>


Full centralization merges Exam and Consult services into a shared agent pool, leveraging pooled variability to improve throughput and overall system stability.

------------------------------------------------------------
REFERENCE
------------------------------------------------------------
Pisaniello, Angelo, et al. “DISCRETE EVENT SIMULATION OF APPOINTMENTS HANDLING AT A CHILDREN’S HOSPITAL CALL CENTER: LESSONS LEARNED FROM V&V PROCESS.” 2018 Winter Simulation Conference (WSC), IEEE, 2018, pp. 3861–72, https://doi.org/10.1109/WSC.2018.8632466.
