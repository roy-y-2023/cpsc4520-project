# SugarCluster: Distributed Sugarscape Disease Simulation on ACES

## CPSC 4520 — Distributed Systems Final Project

---

## Overview

**SugarCluster** — Middleware to run parameter sweeps on the Sugarscape agent-based
simulation engine at scale across Texas A&M's ACES HPC cluster.

### Research Questions

1. **Which disease parameters maximize or minimize the spread of infection?**
2. **How do ethical frameworks influence socio-economic factors (Gini, happiness) during a pandemic?**

### Scale

- **2,168 simulations** — every combination of 4 disease knobs across 8 ethical frameworks (with baselines)
- **1,000 timesteps** each — run twice: once with SLURM job arrays, once with TAMULauncher

---

## Architecture

![architecture](plots/architecture.svg)

### Data Flow

1. **`sweep.toml`** → TOML declares 4 parameter knobs (transmission: 5 values, tag length: 3, immunity: 3, penalty: 6) + 8 ethical frameworks
2. **`generate_configs.py`** → emits 2,168 minimal JSON configs + `jobs.csv` manifest
3. **Two submission strategies** — compared directly (see next slides)
4. **`aggregate.py`** → parses 2,168 JSON results + timing → `run_summary.csv`
5. **`plots.py`** → 7 figures for presentation

---

## Challenges: Too Many Ways to Run a Job

**The problem:** ACES offers 5+ execution strategies. No obvious "right" answer upfront.

| Option | Why it's confusing |
| :--- | :--- |
| **SLURM Job Arrays** | Sounds straightforward — until you hit the QOS array-size limit mid-sweep |
| **TAMULauncher** | ACES-specific, underdocumented — unclear if it's the right tool or just more complexity |
| **Drona Workflow Engine** | GUI-based DAG scheduler — but we wanted terminal/scripting control, not point-and-click |
| **MPI / OpenMP** | Familiar from class — but heavy overhead for embarrassingly parallel, independent sims |
| **CCTools Work Queue** | Portable and general — but why bring in external tools when ACES has its own? |

**Resolution:** We decided to start with the option that seemed most familiar—standard SLURM Job Arrays—and see how far we could push it.

---

## Approach 1: SLURM Job Array

```
┌─────────────────────────────────────────────────────────────┐
│  Job Array: 1741358                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────┐        │
│  │ Task 1  │ │ Task 2  │ │ Task 3  │ ... │ Task 78 │        │
│  │ 28 sims │ │ 28 sims │ │ 28 sims │     │ 12 sims │        │
│  │ ac020   │ │ ac054   │ │ ac092   │     │ ac084   │        │
│  └─────────┘ └─────────┘ └─────────┘     └─────────┘        │
│                    13 ACES nodes                            │
└─────────────────────────────────────────────────────────────┘
```

| Metric | Value |
| :--- | :--- |
| **Total simulations** | 2,168 |
| **SLURM tasks** | 80 |
| **Nodes used** | 13 physical nodes |
| **Total wall time** | **12 min 5 sec** (submit → last task) |
| **Serial equivalent** | 23,186 seconds (386.4 min) |
| **Parallelism factor** | **32.0×** |
| **Avg sim duration** | **10.7s** |
| **Throughput** | **10,761 sims/wall-hour** |

**Challanges:**  ACES QOS limits — can only submit 80 jobs at once.
**Workaround:**  Hybrid batching: a Python script that sequentially runs multiple simulation tasks (e.g. 30) within a single SLURM job.
**Bottleneck:**  Global concurrency cap of 40 running jobs limits true parallelism.

---

## Approach 2: TAMULauncher

```
┌──────────────────────────────────────────────────────┐
│  TAMULauncher (Job: 1741350)                         │
│  commands.txt: 1 line per sim                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  ...  ┌──────┐  │
│  │ sim1 │ │ sim2 │ │ sim3 │ │ sim4 │       │s2168 │  │
│  └──────┘ └──────┘ └──────┘ └──────┘       └──────┘  │
│          20 nodes × 12 tasks = 240 concurrent        │
└──────────────────────────────────────────────────────┘
```

| Metric | Value |
| :--- | :--- |
| **Total simulations** | 2,168 |
| **Concurrency** | 240 (20 nodes × 12/node) |
| **Total wall time** | **2 min 27 sec** (submit → last sim) |
| **Serial equivalent** | 22,480 seconds (374.7 min) |
| **Parallelism factor** | **152.6×** |
| **Avg sim duration** | **10.4s** |
| **Throughput** | **52,983 sims/wall-hour** |

**No job array limit** — TAMULauncher dispatches all 2,168 as individual tasks automatically.

**Challanges:** While I can request more CPU for each node (e.g. 48 cores) to further increase the throughput, the queue wait time will significantly increase to half a day or more due to resource constraints that mean will spend more than queueing than actual execution.

**Measurements:**  Requesting 12 CPUs per node for balance between concurrency and queue time.  

---

## SLURM vs TAMULauncher: Head-to-Head

| Area | SLURM Job Array | TAMULauncher |
| :--- | :--- | :--- |
| **Wall time** | 12 min 5 sec | **2 min 27 sec** |
| **Throughput** | 10,761 sims/hr | **52,983 sims/hr** |
| **Parallelism** | 32.0× | **152.6×** |
| **Job limit workaround** | Hybrid batching (complex) | None needed |
| **Overhead** | Batch startup per task | ~30 seconds |
| **Queue wait** | Near-instant (small jobs) | Near-instant (high priority / reduced density) |
| **Portability** | Any SLURM cluster | ACES-specific |
| **Observability** | `sacct` per task | Per-sim timing JSON |

**Takeaway:** TAMULauncher is **4.9× faster** in wall time. Requesting 240 CPUs via 12 tasks
per node solved the queue time and resource cap issues.

---

## Results: Distributed Systems

![cumulative](plots/cumulative_completion.png)

**TAMULauncher (green)** — 2,168 individual sims, per-sim end timestamps. Finishes at **2:27**.
**SLURM Job Array (blue)** — 80 batch tasks via `sacct`. Staircase reflects 28-sim batches. Finishes at **12:05**.

---

## Results: Timing Breakdown

![duration](plots/sim_duration_hist.png) ![timing](plots/timing_by_penalty.png)

| Penalty | Mean Duration | Outcome |
| :--- | :--- | :--- |
| Baseline (-1.0) | ~10.2s | 100% survival to t=1000 |
| 0.0 | ~10.5s | 100% survival to t=1000 |
| 0.1 – 2.0 | ~10.4s | 100% survival to t=1000 |

- **Unimodal distribution** — simulation durations are tightly concentrated around 10.4s
- **Baseline runs (-1.0)** — runs without any disease initialized finish slightly faster (~10.2s)
- **Starting with 0 diseases prevents early mass extinction**, enabling 100% survival across all configurations
- Execution time is uniform because all simulations survive and run to the 1,000 timestep limit

---

## Results: Scientific Findings

![heatmap](plots/heatmap_penalty0.png)
*Peak infection % by transmission × immunity (penalty=0 only)*

- **Transmission=1.0 + immunity=10** → 68% infection peak across all frameworks
- **Transmission=0.05 + immunity=60** → lowest infection spread (2% peak) in the sweep
- **All 8 ethical frameworks show identical heatmaps** — disease physics dominates ethics

---

## Results: Survival by Penalty

![survival](plots/survival_stacked.png)

- **100% survival across all penalties (0.0 to 2.0)**: Starting with 0 diseases avoids early population collapse
- Ethics do not affect survival outcomes; all ethical frameworks exhibit identical 100% survival rates
- Mild dynamic infection spread from the environment replaces the pre-infected mass extinction dynamic

---

## Results: Inequality (Gini Coefficient)

![gini](plots/gini_penalty.png)

- **Mean delta_gini ≈ −0.008** — wealth inequality slightly decreases under disease sweep across all configurations
- Baseline Gini ~0.3 across all frameworks; disease runs converge to Gini ~0.291
- **Finding:** Economic structure of the disease (metabolism penalty) matters more than ethical behavior, but effects are compressed due to mild infection loads


---

## Challenges: Engineering Lessons

| Problem | Fix |
| :--- | :--- |
| **Misleading Log**| It says process got killed, so I proceed to debug OOM, turns out it's normal TAMULauncher teardown behavior |
| **`$SLURM_SUBMIT_DIR`** resolves to tmpdir | Used absolute paths |
| **Windows/Linux paths** (`os.path.join` → `\`) | Forced forward-slash paths in `jobs.csv` |
| **CRLF line endings** | `commands.txt` written with explicit LF newlines |
| **Final Analysis is Slow**| Use `ThreadPoolExecutor` to parallelize parsing sugarscape outputs |


---

## Future Work

1. **More parameters** — environmental knobs (resource peaks, seasons), trading
2. **Multiple seeds** — 30+ seeds per config for statistical significance; at 52K sims/hr this is now tractable
3. **Interactive dashboard** — real-time monitoring while jobs run on ACES
4. **Automatic Concurrency Tuning** — Autotuning task density dynamically to optimize queue wait vs. execution throughput.
5. **Portability** — abstraction layers to run on other supercomputer/cluster with minimal code changes.

---

## Thank You

**SugarCluster** — TOML → configs → SLURM/TAMULauncher → data → plots

2,168 simulations. Two execution engines. SLURM: 12:05. TAMULauncher: 2:27.

**Questions?**
