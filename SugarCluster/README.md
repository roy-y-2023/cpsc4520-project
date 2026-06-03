# SugarCluster

Middleware to run Sugarscape agent-based simulation parameter sweeps at scale on the Texas A&M ACES HPC cluster.

## Overview

SugarCluster automates the entire distributed lifecycle, from configuration sweep generation to parallel execution, post-run verification, and data analysis. It supports a **dual-backend execution model**, allowing you to choose between standard SLURM job arrays and high-performance TAMULauncher execution.

```
                            ┌──────────────┐
                            │  sweep.toml  │
                            └──────┬───────┘
                                   ▼
                          ┌──────────────────┐
                          │ generate_configs │
                          └──────┬────┬──────┘
                                 │    │
            ┌────────────────────┘    └────────────────────┐
            ▼                                              ▼
    2,888 .config files                              configs/ & jobs.csv
            │                                              │
            │ (SLURM Job Array)                            │ (TAMULauncher Backend)
            ▼                                              ▼
      submit.slurm                                generate_commands.py
     (51 batch tasks)                                      │
            │                                              ▼
            │                                         commands.txt
            │                                              │
            │                                              ▼
            │                                     submit_tamulauncher.slurm
            │                                     (160 worker concurrency)
            └────────────────────┬─────────────────────────┘
                                 ▼
                         ACES HPC Cluster
                                 │
                                 ▼
                     rsync data & timing JSONs
                                 │
                                 ▼
      aggregate.py  →  timing_analysis.py  →  analyze.py  →  plots.py
                                 │
                                 ▼
                           plots/*.png
```

## Requirements

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/)
- **Dependencies:** `pandas`, `matplotlib`, `seaborn`, `tomli` (see `pyproject.toml`)

## Quick Start

```bash
# Clone and enter the project
cd SugarCluster
uv sync

# 1. Generate configs from sweep specification
uv run python generate_configs.py

# 2. Choose and execute an execution backend on ACES:

# --- Option A: TAMULauncher (Recommended) ---
# Generate commands.txt first (specifying the cluster project directory)
PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster \
  uv run python generate_commands.py
# Submit the TAMULauncher script
sbatch -A 155415875505 submit_tamulauncher.slurm

# --- Option B: SLURM Job Array ---
# Submit the hybrid job array script
PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster \
  sbatch -A 155415875505 submit.slurm

# 3. Pull results back to your local machine
make pull_data

# 4. Parse SLURM timing data (requires sacct output)
uv run python parse_slurm.py

# 5. Run the analytics & plotting pipeline
make all
```

## Project Structure

```
SugarCluster/
├── sweep.toml                 # Parameter sweep specification (TOML-driven)
├── generate_configs.py        # Cartesian product config generator
├── generate_commands.py       # TAMULauncher commands generator (commands.txt)
├── submit.slurm               # SLURM job array script (hybrid: 30 sims/task)
├── submit_tamulauncher.slurm  # TAMULauncher submission script (160 concurrent slots)
├── run_batch.py               # Per-batch runner (SLURM job array task worker)
├── run_sim.py                 # Single-simulation runner (TAMULauncher worker)
├── setup_aces.sh              # ACES environment bootstrap script
├── check_outputs.py           # Post-run validation and integrity checker
│
├── parse_slurm.py             # Parse sacct output → slurm_timing.csv
├── aggregate.py               # 2,888 JSON logs + timing → run_summary.csv
├── timing_analysis.py         # Compute throughput/parallelism metrics & curves
├── analyze.py                 # Grouped statistics, penalty stratification
├── plots.py                   # 8 presentation figures
│
├── slurm_full.txt             # Raw sacct output from ACES SLURM array
├── slurm_tamulauncher_full.txt# Raw sacct output from TAMULauncher job
├── jobs.csv                   # Job manifest (job_id → config → params)
│
├── configs/                   # 2,888 generated .config JSON files
├── commands.txt               # 2,888 TAMULauncher command lines
├── data/                      # 2,888 simulation JSON log outputs
├── timing/                    # Per-batch CSVs (SLURM) & per-sim JSONs (TAMULauncher)
├── results/                   # All analysis outputs (CSVs)
└── plots/                     # 8 presentation figures (PNG)
```

## Detailed Workflow

### 1. Configure the Sweep

Edit `sweep.toml` to define the parameters and ethical frameworks to sweep:

```toml
[parameters]
diseaseTransmissionChance = [0.3, 0.6, 1.0]
diseaseTagStringLength = [5, 13, 21]
agentImmuneSystemLength = [10, 35, 60]
diseaseSugarMetabolismPenalty = [0, 0.1, 0.25, 0.5, 1, 2, 3]

models = [
  "none", "altruist", "bentham", "egoist",
  "negativeBentham", "asimov", "temperance", "temperancePECS"
]
```

### 2. Generate Configs & Commands

Run the generation script locally or on the login node:
```bash
uv run python generate_configs.py
```
This generates:
- `configs/*.config` — 2,888 minimal JSON configs containing only overridden parameters.
- `jobs.csv` — A central database mapping job IDs to parameter combinations.

If using TAMULauncher, generate the command list:
```bash
PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster \
  uv run python generate_commands.py
```
This creates `commands.txt` (using explicit Unix LF endings to prevent parser crashes on Linux).

### 3. Run on ACES

Upload the code and configs using `make push_code` or `rsync`. On ACES:

#### Option A: TAMULauncher Backend
TAMULauncher runs all 2,888 tasks concurrently as single-core workers using a master-worker schema.
```bash
# Bootstrap the virtual environment
bash setup_aces.sh

# Submit the TAMULauncher job
sbatch -A 155415875505 submit_tamulauncher.slurm
```
*Note: This requests 20 nodes with 8 tasks per node (160 slots) to process the sweep.*

#### Option B: SLURM Job Array Backend
SLURM Job Array runs a hybrid batch scheme. Since ACES limits the maximum array size to 50 active tasks, we bundle **40 simulations per SLURM task**, resulting in 73 total tasks.
```bash
# Bootstrap the virtual environment
bash setup_aces.sh

# Submit the SLURM job array
PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster \
  sbatch -A 155415875505 submit.slurm
```

### 4. Pull Results & Metadata

After execution completes, download the logs:
```bash
make pull_data
```

To fetch job array metadata from `sacct`:
```bash
# Run on ACES login node (e.g. for Job Array id 1730737):
sacct -j 1730737 > slurm_full.txt

# For TAMULauncher job id 1730944:
sacct -j 1730944 > slurm_tamulauncher_full.txt
```
Copy these text files back to the project root directory.

### 5. Run Post-Processing Pipeline

Run `make all` to run all parsing and statistics steps:
1. `parse_slurm.py` — Parses `sacct` text logs into `results/slurm_timing.csv`.
2. `aggregate.py` — Merges all 1,520 JSON logs and per-run durations into `results/run_summary.csv`.
3. `timing_analysis.py` — Analyzes throughput, parallelism, and cumulative completion data.
4. `analyze.py` — Compiles stats by parameter and ethics framework.
5. `plots.py` — Generates 8 diagnostic and presentation plots.

## Head-to-Head Comparison Results

All 2,888 simulations ran successfully on ACES using both backends:

| Metric | SLURM Job Array Backend | TAMULauncher Backend |
| :--- | :--- | :--- |
| **Total Simulations** | 2,888 | 2,888 |
| **Wall Clock Execution** | 6 min 22 sec (383s) | **3 min 33 sec (213s)** |
| **Parallelism Factor** | 22.5× | **43.7×** |
| **Effective Throughput** | 27,163 sims/hour | **48,801 sims/hour** |
| **Startup / Exec Overhead**| ~4.5% (interpreter startup) | **~0.0%** (direct run) |
| **Queue Concurrency Cap** | 50 jobs (requires hybrid batches) | None (single job container) |
| **Cluster Portability** | Universal SLURM compatibility | TAMU ACES specific |
| **Queue Wait Time** | **Near-instant** | **Near-instant** (distributed load) |

### Key Scientific Findings
- **Disease Metabolism Penalty Dominates:** If metabolism penalty is `0.0`, survival rate is 100% to $t=1000$ across all 8 frameworks. Any non-zero penalty (`0.1` to `3.0`) leads to **89% instant extinction** at $t=1$.
- **Ethics vs Physics:** Since initial disease parameters are highly severe, ethical decision models show identical heatmaps and survival profiles. The physics of disease transmission and metabolic cost completely overwhelm ethical framework behaviors.
- **Economic Inequality:** Wealth inequality slightly decreases under a pandemic (mean delta Gini $\approx -0.01$). This is due to flat metabolic penalties acting as a wealth compression force across the population.

## Adding a New Parameter

1. **Add to `sweep.toml`** under `[parameters]`:
   ```toml
   myNewParam = [10, 20, 30]
   ```
2. **Add to the config generator** in `generate_configs.py`:
   ```python
   cfg[config_level]["myNewParam"] = combo["myNewParam"]
   ```
   *Note: For ranges, use `[combo["myNewParam"], combo["myNewParam"]]` to fit Sugarscape's expected format.*

## License

This project is part of CPSC 4520 Distributed Systems.
