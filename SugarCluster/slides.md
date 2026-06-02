# SugarCluster: Distributed Sugarscape Disease Simulation on ACES

## CPSC 4520 — Distributed Systems Final Project

---

## Agenda

| Section | Time |
| :--- | :--- |
| Overview & Research Questions | 1 min |
| Architecture | 2 min |
| Results | 2 min |
| Challenges & Lessons Learned | 2 min |
| Future Work | 1 min |

---

## Overview

**SugarCluster** — Middleware to run parameter sweeps on the Sugarscape agent-based
simulation engine at scale across an HPC cluster (Texas A&M ACES).

### Research Questions

1. **Which disease parameters maximize or minimize the spread of infection?**
2. **How do socio-economic factors (Gini, happiness) interact with pandemics?**

### Scale

- **1,520 simulations** — every combination of 4 disease knobs across 8 ethical frameworks (with baselines)
- **1,000 timesteps** each — run twice: once with SLURM job arrays, once with TAMULauncher

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ sweep.toml   │───▶│ generate_configs │───▶│ 1,520 .config files     │
│ (4 knobs)    │     │ .py              │     │ + jobs.csv manifest    │
└──────────────┘     └──────────────────┘     └───────────┬────────────┘
                                                          │
                                        ┌─────────────────┴─────────────────┐
                                        ▼                                   ▼
                                   submit.slurm                 submit_tamulauncher.slurm
                                    (job array)                      (TAMULauncher)
                                        └─────────────────┬─────────────────┘
                                                          ▼
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ plots/*.png  │◀───│ aggregate.py     │◀───│ ACES HPC Cluster        │
│ 8 figures    │     │ + analyze.py     │     │ 1,520 JSON results     │
└──────────────┘     │ + plots.py       │     └────────────────────────┘
                     └──────────────────┘
```

### Data Flow

1. **`sweep.toml`** → TOML declares 4 parameter knobs (3 with 3 values, 1 with 7 values) + 8 ethical frameworks
2. **`generate_configs.py`** → emits 1,520 minimal JSON configs + `jobs.csv` manifest
3. **Two submission strategies** — compared head-to-head (see next slides)
4. **`aggregate.py`** → parses 1,520 JSON results + timing → `run_summary.csv`
5. **`plots.py`** → 8 figures for presentation

---

## Approach 1: SLURM Job Array

```
┌─────────────────────────────────────────────────────────────┐
│  Job Array: 1730737                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────┐        │
│  │ Task 1  │ │ Task 2  │ │ Task 3  │ ... │ Task 51 │        │
│  │ 30 sims │ │ 30 sims │ │ 30 sims │     │ 30 sims │        │
│  │ ac022   │ │ ac040   │ │ ac069   │     │ ac017   │        │
│  └─────────┘ └─────────┘ └─────────┘     └─────────┘        │
│                    11 ACES nodes                            │
└─────────────────────────────────────────────────────────────┘
```

| Metric | Value |
| :--- | :--- |
| **Total simulations** | 1,520 |
| **SLURM tasks** | 51 (hybrid: 30 sims/task) |
| **Nodes used** | 11 ACES nodes |
| **Total wall time** | **5 min 16 sec** |
| **Serial equivalent** | 6,599 seconds (110 min) |
| **Parallelism factor** | **20.9×** |
| **Batch overhead** | **6.0%** (8.6s Python startup + config loading) |
| **Throughput** | **17,316 sims/wall-hour** |

**Bottleneck:** ACES QOS limits — max array size forced hybrid batching (30 sims/task).
Global concurrency cap of 40 running jobs limits true parallelism.

---

## Approach 2: TAMULauncher

```
┌──────────────────────────────────────────────────────┐
│  TAMULauncher (Job: 1730944)                         │
│  commands.txt: 1 line per sim                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  ...  ┌──────┐  │
│  │ sim1 │ │ sim2 │ │ sim3 │ │ sim4 │       │s1520 │  │
│  └──────┘ └──────┘ └──────┘ └──────┘       └──────┘  │
│          8 nodes × 16 tasks = 128 concurrent         │
└──────────────────────────────────────────────────────┘
```

| Metric | Value |
| :--- | :--- |
| **Total simulations** | 1,520 |
| **Concurrency** | 128 (8 nodes × 16/node) |
| **Total wall time** | **60 seconds** |
| **Serial equivalent** | 4,214 seconds (70 min) |
| **Parallelism factor** | **70×** |
| **Overhead** | ~0% (no batching, no Python startup cost per batch) |
| **Throughput** | **91,144 sims/wall-hour** |

**No job array limit** — TAMULauncher dispatches all 1,520 as individual tasks automatically.

---

## SLURM vs TAMULauncher: Head-to-Head

| | SLURM Job Array | TAMULauncher |
| :--- | :--- | :--- |
| **Wall time** | 5 min 16 sec | **60 sec** |
| **Throughput** | 17,316 sims/hr | **91,144 sims/hr** |
| **Parallelism** | 20.9× | **70×** |
| **Job limit workaround** | Hybrid batching (complex) | None needed |
| **Overhead** | 6% (batch startup) | ~0% |
| **Queue wait** | Near-instant (small jobs) | Near-instant (after reduced machine size) |
| **Portability** | Any SLURM cluster | ACES-specific |
| **Observability** | `sacct` per task | Per-sim timing JSON |

**Takeaway:** TAMULauncher is **5.3× faster** in wall time and handles the array size limit
transparently — but requesting 48 CPUs means a longer queue wait even during night time.

---

## Results: Distributed Systems

![cumulative](plots/cumulative_completion.png)

**TAMULauncher (green)** — 1,520 individual sims, per-sim end timestamps. Finishes at **60 sec**.
**SLURM Job Array (blue)** — 51 batch tasks via `sacct`. Staircase reflects 30-sim batches. Finishes at **316 sec**.
**Theoretical (red dashed)** — perfect parallelism baseline from per-sim durations.

---

## Results: Timing Breakdown

![timing](plots/timing_by_penalty.png)

| Penalty | Mean Duration (Survived / Extinct) | Outcome |
| :--- | :--- | :--- |
| 0.0 | 24.4s / N/A | 100% survival to t=1000 (final pop ~153) |
| 0.1 – 3.0 | ~5.2s / ~0.4s | 89% extinction at t=1; 11% survive to t=1000 (final pop ~10) |

- **Bimodal distribution** — simulation runs either to completion or dies instantly
- **Any non-zero penalty (0.1 to 3.0) causes mass extinction** for 89% of configurations at t=1

---

## Results: Scientific Findings

![heatmap](plots/heatmap_penalty0.png)
*Peak infection % by transmission × immunity (penalty=0 only)*

- **Transmission=1.0 + immunity=10** → 100% infection peak across all frameworks
- **Transmission=0.3 + immunity=60** → 98.4% infection peak (due to high initial disease load)
- **All 8 ethical frameworks show identical heatmaps** — disease physics dominates ethics

---

## Results: Survival by Penalty

![survival](plots/survival_stacked.png)

- **Penalty=0: 100% survival** across all frameworks
- **Penalty=0.1 – 3.0: only 11% survival** (just the high-immunity/short-tag combinations)
- **No framework difference** — ethics don't change outcomes when disease is present

---

## Results: Inequality (Gini Coefficient)

![gini](plots/gini_penalty0.png)

- **Mean delta_gini ≈ -0.01** — wealth inequality slightly decreases under penalty=0
- Baseline Gini ~0.3 across all frameworks
- Disease runs converge to Gini ~0.29
- **Finding:** Economic structure of the disease (metabolism penalty) matters more than ethical behavior

---

## Challenges: Engineering Lessons

| Problem | Fix |
| :--- | :--- |
| **QOS job limit** (1,520 jobs > max array size) | Hybrid batching: 51 tasks × 30 sims → then switched to TAMULauncher |
| **ACES global concurrency cap** (40 jobs) | TAMULauncher bypasses this entirely |
| **TAMULauncher queue wait** | Large resource ask (48 CPU per node) → ~2 hour queue time |
| **`$SLURM_SUBMIT_DIR`** resolves to tmpdir | Used absolute paths: `PROJECT_DIR` env var |
| **Windows/Linux paths** (`os.path.join` → `\`) | Forced forward-slash paths in `jobs.csv` |
| **CRLF line endings** | `commands.txt` written with explicit LF newlines |
| **Disease params must be lists** `[0.3, 0.3]` | Sugarscape validation requires range format |
| **Penalty calibration** [0, 2, 5] → everyone died | Expanded sweep to [0, 0.1, 0.25, 0.5, 1, 2, 3] |


---

## Challenges: Middleware Design

**Goal:** Reusable, not hard-coded to this experiment.

```
sweep.toml          →    generate_configs.py    →    1,520 configs
(declarative params)     (generic cartesian       (minimal JSON,
                         product engine)           Sugarscape fills defaults)

                    →    generate_commands.py   →    commands.txt
                         (TAMULauncher mode)         (1 line per sim)
```

- **No hard-coded parameter values** in Python — everything lives in `sweep.toml`
- **Adding a new knob** = 1 line in TOML + 1 line in config template
- **Swap execution engine** = switch `submit.slurm` ↔ `submit_tamulauncher.slurm`

---

## Future Work

1. **Reduce TAMULauncher queue wait** — request fewer nodes, more tasks/node (e.g. 2 nodes × 64/node)
2. **More parameters** — environmental knobs (resource peaks, pollution), agent genetics
3. **Multiple seeds** — 30+ seeds per config for statistical significance; at 91K sims/hr this is now tractable
4. **Interactive dashboard** — real-time monitoring while jobs run on ACES
5. **Containerized deployment** — Singularity/Docker for zero-install cluster portability

---

## Thank You

**SugarCluster** — TOML → configs → SLURM/TAMULauncher → data → plots

1,520 simulations. Two execution engines. SLURM: 5.3 min. TAMULauncher: 60 sec.

**Questions?**

---

*Repository: github.com/your/cpsc4520-project · SLURM job: 1730737 · TAMULauncher job: 1730944*
