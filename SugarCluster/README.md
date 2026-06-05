# SugarCluster

Middleware to run Sugarscape agent-based simulation parameter sweeps at scale on the Texas A&M ACES HPC cluster.

## Overview

SugarCluster automates the entire distributed lifecycle, from configuration sweep generation to parallel execution, post-run verification, and data analysis. It supports a dual-backend execution model, allowing you to choose between standard SLURM job arrays and high-performance TAMULauncher execution.

## Requirements

- **Python 3.12+**
- **Dependencies:** `pandas`, `matplotlib`, `seaborn`, `tomli` (installed automatically via `make setup-server` or `uv sync` locally)

## Quick Start (ACES Cluster Workflow)

All steps of the simulation and analysis pipeline are designed to run directly on the ACES server.

> [!IMPORTANT]
> **Cluster Configuration:**
> You must replace the account number `ACCOUNT=155415875505` and the project directory path `PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project` in the commands below with your own HPRC project account number and absolute cluster path.

> [!WARNING]
> **File/Inode Quotas:**
> A full 2,168-simulation sweep creates a massive footprint of 8,000+ files (configs, output JSON logs, worker outputs, and timing logs). Be mindful of your ACES group disk/inode quotas. Use `make clean` to purge intermediate configurations and outputs after your final analysis runs are finished.

### 1. Setup on ACES
Extract the project archive (or clone the repository) directly to your scratch space on the ACES cluster (e.g., under `/scratch/group/p.cis260910.000/cpsc4520-project/`).

Navigate to the `SugarCluster` folder and bootstrap the environment:
```bash
cd SugarCluster
make setup-server
```
*Note: This automatically creates a Python virtual environment and installs all dependencies (`tomli`, `pandas`, `matplotlib`, `seaborn`).*

### 2. Run the Parameter Sweep
Activate the virtual environment, then choose one of the two execution backends to generate configurations/commands and submit the job in a single command:

#### Option A: TAMULauncher Backend (Recommended)
This dispatch runs all 2,168 simulations concurrently across a master-worker pool (requests 20 nodes with 240 worker slots):
```bash
make submit-tamu ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

#### Option B: SLURM Job Array Backend
This fallback runs simulations in hybrid batches of 28 simulations per job array task (80 tasks total):
```bash
make submit-slurm ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```

### 3. Parse Metadata & Run Analytics Pipeline
Once the jobs complete successfully, generate the analysis and presentation figures directly on the cluster:

```bash
# Verify all output logs were written successfully
make check-outputs

# Export job metadata from SLURM sacct for Job Array backend (replace with your active Job ID)
sacct -j <JOB_ID> > slurm_full.txt

# Run the post-processing pipeline
make all
```
*Note: All results will be generated in `results/` and figures in `plots/` on the server. You can download the completed `plots/` folder to view the figures locally.*


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

Note: if you're settings resulted in more sims and/or longer run, you need to adjust the time ceiling in `submit_tamulauncher.slurm` and `submit.slurm` accordingly.

### 2. Generate Configs & Commands

With the Makefile, configuration and command generation are automatically handled as dependencies when submitting jobs. However, they can be run manually on the server (or locally):
```bash
# Generate the 2,168 minimal config JSON files and jobs.csv manifest:
make configs

# Generate commands.txt for TAMULauncher (specifying the PROJECT_DIR on the cluster):
make commands PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```
This generates:
- `configs/*.config` - 2,168 minimal JSON configs containing only overridden parameters.
- `jobs.csv` - A central database mapping job IDs to parameter combinations.
- `commands.txt` - 2,168 simulation command lines (using Unix LF line endings to avoid cluster parsing issues).

### 3. Run on ACES

With the project folder extracted on the ACES cluster, everything can be executed directly on the server.

#### Option A: TAMULauncher Backend (Recommended)
TAMULauncher runs all 2,168 tasks concurrently as single-core workers using a master-worker schema.

Using the Makefile target simplifies configuration generation, command generation, log cleanup, and job submission into one step:
```bash
make submit-tamu ACCOUNT=155415875505 PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project
```
*Note: This requests 20 nodes with 12 tasks per node (240 slots) to process the sweep.*

#### Option B: SLURM Job Array Backend
SLURM Job Array runs a hybrid batch scheme. Since ACES limits the maximum array size to 80 active tasks, we bundle multiple simulations per SLURM task (dynamically adjusted), resulting in 80 total tasks (78 active).

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
1. `parse_slurm.py` - Parses `sacct` text logs into `results/slurm_timing.csv`.
2. `aggregate.py` - Merges all 2,168 JSON logs and per-run durations into `results/run_summary.csv`.
3. `timing_analysis.py` - Analyzes throughput, parallelism, and cumulative completion data.
4. `analyze.py` - Compiles stats by parameter and ethics framework.
5. `plots.py` - Generates 8 diagnostic and presentation plots in `plots/`.
