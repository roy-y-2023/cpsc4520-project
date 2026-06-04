# SugarCluster

Run Sugarscape agent-based simulation parameter sweeps at scale on the Texas A&M ACES HPC cluster.

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
    2,168 .config files                              configs/ & jobs.csv
            │                                              │
            │ (SLURM Job Array)                            │ (TAMULauncher Backend)
            ▼                                              ▼
      submit.slurm                                generate_commands.py
     (80 batch tasks)                                      │
            │                                              ▼
            │                                         commands.txt
            │                                              │
            │                                              ▼
            │                                     submit_tamulauncher.slurm
            │                                     (240 worker concurrency)
            └────────────────────┬─────────────────────────┘
                                 ▼
                          ACES HPC Cluster
                                 │
                                 ▼
                    sacct logs + simulation data
                                 │
                                 ▼
      aggregate.py  →  timing_analysis.py  →  analyze.py  →  plots.py
                                 │
                                 ▼
                            plots/*.png
```
## Requirements

- **Python 3.12+**
- **Dependencies:** `pandas`, `matplotlib`, `seaborn`, `tomli` (installed automatically via `make setup-server` or `uv sync` locally)

## Quick Start (ACES Cluster Workflow)

All steps of the simulation and analysis pipeline are designed to run directly on the ACES server.

> [!IMPORTANT]
> **Cluster Configuration:**
> You **MUST** replace the account number `ACCOUNT=155415875505` and the project directory path `PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project` in the commands below with your own HPRC project account number and absolute cluster path.

> [!WARNING]
> **File/Inode Quotas:**
> A full 2,168-simulation sweep creates a massive footprint of **8,000+ files** (configs, output JSON logs, worker outputs, and timing logs). Be mindful of your ACES group disk/inode quotas. Use `make clean` to purge intermediate configurations and outputs after your final analysis runs are finished.

### 1. Setup on ACES
Extract the project archive (or clone the repository) directly to your scratch space on the ACES cluster (e.g., under `/scratch/group/p.cis260910.000/cpsc4520-project/`).

Navigate to the `SugarCluster` folder and bootstrap the environment:
```bash
cd SugarCluster
make setup-server
```
This creates a Python virtual environment and installs all dependencies.

### 2. Run the Parameter Sweep
Activate the virtual environment, then choose one of the two execution backends to generate configurations/commands and submit the job in a single command:

#### Option A: TAMULauncher Backend (Recommended)
This dispatch runs all 2,168 simulations concurrently across a master-worker pool (requests 20 nodes with 240 worker slots):
```bash
source .venv/bin/activate
make submit-tamu ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

#### Option B: SLURM Job Array Backend
This fallback runs simulations in hybrid batches of 28 simulations per job array task (80 tasks total):
```bash
source .venv/bin/activate
make submit-slurm ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

### 3. Parse Metadata & Run Analytics Pipeline
Once the jobs complete successfully, generate the analysis and presentation figures directly on the cluster:

```bash
# Verify all output logs were written successfully
make check-outputs

# Export job metadata from SLURM sacct (replace with your active Job ID)
sacct -j <JOB_ID> > slurm_full.txt               # For Job Array backend

# Run the post-processing pipeline
make all
```
Results go to `results/` and figures to `plots/` on the server. Download the `plots/` folder to view locally.


## Project Structure

```
SugarCluster/
├── sweep.toml                 # Parameter sweep specification (TOML-driven)
├── generate_configs.py        # Cartesian product config generator
├── generate_commands.py       # TAMULauncher commands generator (commands.txt)
├── submit.slurm               # SLURM job array script (hybrid: 28 sims/task)
├── submit_tamulauncher.slurm  # TAMULauncher submission script (240 concurrent slots)
├── run_batch.py               # Per-batch runner (SLURM job array task worker)
├── run_sim.py                 # Single-simulation runner (TAMULauncher worker)
├── setup_aces.sh              # ACES environment bootstrap script
├── check_outputs.py           # Post-run validation and integrity checker
│
├── parse_slurm.py             # Parse sacct output → slurm_timing.csv
├── aggregate.py               # 2,168 JSON logs + timing → run_summary.csv
├── timing_analysis.py         # Compute throughput/parallelism metrics & curves
├── analyze.py                 # Grouped statistics, penalty stratification
├── plots.py                   # 8 presentation figures
│
├── slurm_full.txt             # Raw sacct output from ACES SLURM array
├── slurm_tamulauncher_full.txt# Raw sacct output from TAMULauncher job
├── jobs.csv                   # Job manifest (job_id → config → params)
│
├── configs/                   # 2,168 generated .config JSON files
├── commands.txt               # 2,168 TAMULauncher command lines
├── data/                      # 2,168 simulation JSON log outputs
├── timing/                    # Per-batch CSVs (SLURM) & per-sim JSONs (TAMULauncher)
├── results/                   # All analysis outputs (CSVs)
└── plots/                     # 8 presentation figures (PNG)
```

## Detailed Workflow

### 1. Configure the Sweep

Edit `sweep.toml` to define the parameters and ethical frameworks to sweep:

```toml
[disease.sweep]
diseaseTransmissionChance = [0.05, 0.1, 0.3, 0.6, 1.0]
diseaseTagStringLength = [5, 13, 21]
agentImmuneSystemLength = [10, 35, 60]
diseaseSugarMetabolismPenalty = [0, 0.1, 0.25, 0.5, 1, 2]

[sweep.models]
frameworks = [
  "none",
  "altruist",
  "bentham",
  "egoist",
  "negativeBentham",
  "asimov",
  "temperance",
  "temperancePECS"
]
```

If your settings result in more sims or longer runs, adjust the time ceiling in `submit_tamulauncher.slurm` and `submit.slurm` accordingly.

### 2. Generate Configs & Commands

With the Makefile, configuration and command generation are automatically handled as dependencies when submitting jobs. However, they can be run manually on the server (or locally):
```bash
# Generate the 2,168 minimal config JSON files and jobs.csv manifest:
make configs

# Generate commands.txt for TAMULauncher (specifying the PROJECT_DIR on the cluster):
make commands PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```
This generates:
- `configs/*.config` — 2,168 minimal JSON configs containing only overridden parameters.
- `jobs.csv` — A central database mapping job IDs to parameter combinations.
- `commands.txt` — 2,168 simulation command lines (using Unix LF line endings to avoid cluster parsing issues).

### 3. Run on ACES

With the project folder extracted on the ACES cluster, everything can be executed directly on the server.

#### Option A: TAMULauncher Backend (Recommended)
TAMULauncher runs all 2,168 tasks concurrently as single-core workers using a master-worker schema.

Using the Makefile target simplifies configuration generation, command generation, log cleanup, and job submission into one step:
```bash
make submit-tamu ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```
This requests 20 nodes with 12 tasks per node (240 slots) to process the sweep.

#### Option B: SLURM Job Array Backend
SLURM Job Array runs a hybrid batch scheme. Since ACES limits the maximum array size to 50 active tasks, we bundle **28 simulations per SLURM task**, resulting in 80 total tasks (78 active).

This is also simplified via the Makefile:
```bash
make submit-slurm ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

### 4. Fetch Job Metadata

After execution completes, export the job history metadata from `sacct` directly on the ACES login node. This is required for the timing analysis.

For the Job Array backend (e.g., job ID `1741358`):
```bash
sacct -j 1741358 > slurm_full.txt
```

*(Optional)* If you wish to download the simulation results to analyze them locally:
```bash
make pull-data PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

### 5. Run Post-Processing Pipeline

Activate the virtual environment if it isn't already, and run the pipeline on the server:
```bash
source .venv/bin/activate
make all
```

This runs:
1. `parse_slurm.py` — Parses `sacct` text logs into `results/slurm_timing.csv`.
2. `aggregate.py` — Merges all 2,168 JSON logs and per-run durations into `results/run_summary.csv`.
3. `timing_analysis.py` — Analyzes throughput, parallelism, and cumulative completion data.
4. `analyze.py` — Compiles stats by parameter and ethics framework.
5. `plots.py` — Generates 8 diagnostic and presentation plots in `plots/`.

## Head-to-Head Comparison Results

All 2,168 simulations ran successfully on ACES using both backends:

| Metric | SLURM Job Array Backend | TAMULauncher Backend |
| :--- | :--- | :--- |
| **Total Simulations** | 2,168 | 2,168 |
| **Wall Clock Execution** | 12 min 5 sec (725s) | **2 min 27 sec (147s)** |
| **Parallelism Factor** | 32.0× | **152.6×** |
| **Effective Throughput** | 10,761 sims/hour | **52,983 sims/hour** |
| **Startup / Exec Overhead**| ~4.5% (interpreter startup) | **~0.0%** (direct run) |
| **Queue Concurrency Cap** | 50 jobs (requires hybrid batches) | None (single job container) |
| **Cluster Portability** | Universal SLURM compatibility | TAMU ACES specific |
| **Queue Wait Time** | **Near-instant** | **Near-instant** (distributed load) |

### Key Scientific Findings
- **100% Survival Across All Penalties:** With `startingDiseasesPerAgent` set to `[0, 0]` (no pre-infected agents), all simulations survive to the 1,000 timestep limit (100% survival) across all penalty levels (0.0 to 2.0). Early mass extinction disappears entirely, resulting in unimodal execution durations.
- **Ethics vs Physics:** Since all configurations survive and the disease spreads mildly through the environment, ethical decision models show identical heatmaps and survival profiles. The physics of disease transmission and immunity length completely govern the infection peaks.
- **Economic Inequality:** Wealth inequality slightly decreases under a pandemic (mean delta Gini $\approx -0.008$). This is due to flat metabolic penalties acting as a mild wealth compression force, converging to Gini ~0.291 (from baseline ~0.30).

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
