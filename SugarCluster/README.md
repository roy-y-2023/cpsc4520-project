# SugarCluster

Middleware to run Sugarscape agent-based simulation parameter sweeps at scale on the Texas A&M ACES HPC cluster.

## Overview

SugarCluster automates everything from config generation to data analysis:

```
sweep.toml  →  generate_configs.py  →  656 .config files
                                         │
              ┌──────────────────────────┘
              ▼
         submit.slurm  →  ACES (66 tasks × 10 sims, 20 nodes)
              │
              ▼
         rsync data back  →  data/*.json + timing/*.csv
              │
              ▼
         aggregate.py  →  analyze.py  →  plots.py  →  plots/*.png
```

## Requirements

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/)
- **Dependencies:** pandas, matplotlib, seaborn, tomli (see `pyproject.toml`)

## Quick Start

```bash
# Clone and enter the project
cd SugarCluster
uv sync

# 1. Generate configs from sweep spec
uv run python generate_configs.py

# 2. Transfer to ACES and submit (manual — see below)
# 3. Pull results back (rsync / scp)

# 4. Parse SLURM timing (requires sacct output in slurm_full.txt)
uv run python parse_slurm.py

# 5. Aggregate all results
uv run python aggregate.py
uv run python timing_analysis.py
uv run python analyze.py

# 6. Generate plots
uv run python plots.py
```

## Project Structure

```
SugarCluster/
├── sweep.toml              # Parameter sweep specification (TOML)
├── generate_configs.py     # Cartesian product config generator
├── submit.slurm            # SLURM job array (hybrid: 10 sims/task)
├── run_batch.py            # Per-batch runner with timing
├── setup_aces.sh           # ACES environment bootstrap
├── check_outputs.py        # Post-run validation
│
├── parse_slurm.py          # Parse sacct output → slurm_timing.csv
├── aggregate.py            # JSON logs + timing → run_summary.csv
├── timing_analysis.py      # Compute throughput/parallelism metrics
├── analyze.py              # Grouped statistics, penalty stratification
├── plots.py                # 7 presentation figures
│
├── slurm_full.txt          # Raw sacct output from ACES
├── jobs.csv                # Job manifest (job_id → config → params)
│
├── configs/                # 656 generated .config JSON files
├── data/                   # 656 simulation JSON log outputs
├── timing/                 # 66 per-batch timing CSVs
├── results/                # All analysis outputs (CSVs)
├── plots/                  # 7 presentation figures (PNG)
│
├── slides.md               # 12-slide presentation deck
├── speaking_notes.md       # Presenter script with timing
└── pyproject.toml          # Python project + dependencies
```

## Workflow

### 1. Configure the Sweep

Edit `sweep.toml` to define parameter knobs and their values:

```toml
[parameters]
diseaseTransmissionChance = [0.3, 0.6, 1.0]
diseaseTagStringLength = [5, 13, 21]
agentImmuneSystemLength = [10, 35, 60]
diseaseSugarMetabolismPenalty = [0, 2, 3]

models = ["none", "altruist", "bentham", "egoist",
          "negativeBentham", "asimov", "temperance", "temperancePECS"]
```

### 2. Generate Configs

```bash
uv run python generate_configs.py
```

Outputs:
- `configs/*.config` — minimal JSON configs (only specified keys differ from defaults)
- `jobs.csv` — manifest mapping `job_id` to config path and parameters

### 3. Run on ACES

```bash
# On ACES in the project directory:
bash setup_aces.sh
PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster \
  sbatch -A 155415875505 submit.slurm
```

`submit.slurm` uses hybrid batching: `SIMS_PER_JOB=10` → 66 tasks for 656 configs (avoids QOS array size limit).

### 4. Pull Results

```bash
rsync -avz login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/data/ \
  SugarCluster/data/
rsync -avz login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/timing/ \
  SugarCluster/timing/
```

Get SLURM timing metadata:
```bash
# On ACES:
sacct | grep <job_array_id> > slurm_full.txt
# Transfer slurm_full.txt to SugarCluster/
```

### 5. Analyze

```bash
uv run python parse_slurm.py        # sacct → slurm_timing.csv
uv run python aggregate.py          # JSON + timing → run_summary.csv
uv run python timing_analysis.py    # Throughput, parallelism, cumulative curves
uv run python analyze.py            # Grouped stats + penalty stratification
```

### 6. Generate Plots

```bash
uv run python plots.py
```

Output: `plots/` directory with 7 PNG figures for the presentation.

## Key Results (Example Run)

| Metric | Value |
| :--- | :--- |
| Total simulations | 656 |
| SLURM tasks | 66 (10 sims/task hybrid) |
| ACES nodes used | 20 |
| Wall time | 2 min 23 sec |
| Parallelism factor | **25.7×** (3681s serial → 143s wall) |
| Throughput | 16,515 sims/wall-hour |
| Batch overhead | 1.3% |
| Penalty=0 survival | 100% |
| Penalty=2/3 survival | 11% |

## Adding a New Parameter

1. Add the parameter to `sweep.toml` under `[parameters]`:
   ```toml
   myNewParam = [10, 20, 30]
   ```
2. Add it to the disease config template in `generate_configs.py`:
   ```python
   cfg[config_level]["myNewParam"] = [combo["myNewParam"], combo["myNewParam"]]
   ```
3. For an environmental parameter (not disease-specific), add a new sweep group.

The middleware is designed to make this a 2-line change.

## License

This project is part of CPSC 4520 Distributed Systems.
