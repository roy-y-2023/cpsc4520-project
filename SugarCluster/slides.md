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
- **1,000 timesteps** each, **30 sims per SLURM task**, **51 parallel tasks**

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ sweep.toml   │────▶│ generate_configs  │────▶│ 1,520 .config files     │
│ (4 knobs)    │     │ .py              │     │ + jobs.csv manifest     │
└──────────────┘     └──────────────────┘     └───────────┬────────────┘
                                                          │
                                                          ▼
┌──────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ plots/*.png  │◀────│ aggregate.py     │◀────│ ACES HPC Cluster        │
│ 8 figures    │     │ + analyze.py     │     │ 11 nodes · 51 tasks     │
└──────────────┘     │ + plots.py       │     │ 5.3 min wall time       │
                     └──────────────────┘     └────────────────────────┘
```

### Data Flow

1. **`sweep.toml`** → TOML declares 4 parameter knobs (3 with 3 values, 1 with 7 values) + 8 ethical frameworks
2. **`generate_configs.py`** → emits 1,520 minimal JSON configs + `jobs.csv` manifest
3. **`submit.slurm`** → SLURM job array, 51 tasks × 30 sims each (hybrid batching)
4. **`run_batch.py`** → per-sim timing, per-batch CSV logs
5. **`aggregate.py`** → parses 1,520 JSON results + timing → `run_summary.csv`
6. **`plots.py`** → 8 figures for presentation

---

## Distributed Execution on ACES

```
┌─────────────────────────────────────────────────────────────┐
│  Job Array: 1730737                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────┐      │
│  │ Task 1  │ │ Task 2  │ │ Task 3  │ ... │ Task 51 │      │
│  │ 30 sims │ │ 30 sims │ │ 30 sims │     │ 30 sims │      │
│  │ ac022   │ │ ac040   │ │ ac069   │     │ ac017   │      │
│  └─────────┘ └─────────┘ └─────────┘     └─────────┘      │
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

---

## Results: Distributed Systems

![cumulative](plots/cumulative_completion.png)

**Real (blue)** tracks actual SLURM task completions from `sacct`.
**Theoretical (red)** assumes perfect parallelism — each batch completes when its 10 sims finish.

The gap shows ACES scheduling ("all tasks start nearly simultaneously, minimal queuing delay").

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

## Challenges: Why SLURM?

| Option | Trade-off |
| :--- | :--- |
| **SLURM job arrays** ✓ | Built-in on ACES, just write a script |
| Drona / TAMULauncher | ACES-specific workflow engine, good for DAGs but less portable |
| MPI (`mpirun`) | Overkill for independent sims — no communication needed |
| CCTools / Makeflow | Excellent for reproducible workflows, but requires custom install on ACES |

**Chose SLURM for simplicity** — our sims are embarrassingly parallel (no data dependencies).

---

## Challenges: Engineering Lessons

| Problem | Fix |
| :--- | :--- |
| **QOS job limit** (1,520 jobs > max array size) | Hybrid batching: 51 tasks × 30 sims each |
| **Windows/Linux paths** (`os.path.join` → `\`) | Forced forward-slash paths in `jobs.csv` |
| **CRLF line endings** | `sed -i 's/\r$//'` on ACES |
| **`$SLURM_SUBMIT_DIR`** resolves to tmpdir | Used absolute paths: `PROJECT_DIR` env var |
| **Disease params must be lists** `[0.3, 0.3]` not scalars | Sugarscape validation requires range format |
| **Penalty calibration** [0, 2, 5] → everyone died | Expanded sweep to [0, 0.1, 0.25, 0.5, 1, 2, 3] to study intermediate penalties |

---

## Challenges: Middleware Design

**Goal:** Reusable, not hard-coded to this experiment.

```
sweep.toml          →    generate_configs.py    →    1,520 configs
(declarative params)     (generic cartesian       (minimal JSON,
                         product engine)           Sugarscape fills defaults)
```

- **No hard-coded parameter values** in Python — everything lives in `sweep.toml`
- **Adding a new knob** = 1 line in TOML + 1 line in config template
- **Running on a different cluster** = swap `submit.slurm` for PBS/Moab/LSF

---

## Future Work

1. **Port to Makeflow / CCTools** — formal DAG workflow with provenance tracking
2. **More parameters** — environmental knobs (resource peaks, pollution), agent genetics
3. **Multiple seeds** — 30+ seeds per config for statistical significance
4. **Interactive dashboard** — real-time monitoring while jobs run on ACES
5. **Containerized deployment** — Singularity/Docker for zero-install cluster portability

---

## Thank You

**SugarCluster** — TOML → configs → SLURM → data → plots

1,520 simulations. 11 nodes. 5.3 minutes.

**Questions?**

---

*Repository: github.com/your/cpsc4520-project · ACES job: 1730737*
