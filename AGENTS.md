# AGENTS.md

## Project Overview

**SugarCluster** — Middleware to run Sugarscape agent-based simulation parameter sweeps at scale on the [Texas A&M ACES](https://hprc.tamu.edu/aces/) cluster. The `sugarscape/` directory is a **read-only git submodule** — never modify files inside it. All new code lives in `SugarCluster/`.

**Status:** Phase 5 (Presentation & Packaging). All 656 simulations ran successfully on ACES — 66 SLURM tasks across 20 nodes.

## Questions to Explore

- How does different parameters maximize/minimize the spread of disease?
- How do socio-economics factors play with "pandemics"?

**Finding:** Disease metabolism penalty dominates outcomes. Penalty=0 → 100% survival to t=1000. Penalty=2/3 → 89% extinction at t=1. All 8 ethical frameworks produce near-identical results — disease physics overwhelms ethical behavior. Delta Gini ≈ 0 (pandemic does not measurably change wealth inequality).

## Setup

- Python 3.12+, managed with **uv**
- Project code lives in `SugarCluster/` — `uv add` any dependencies
- Dependencies installed: `pandas`, `matplotlib`, `seaborn`, `tomli`
- Run `uv sync` after cloning

## Project Structure

```
SugarCluster/                  # Main implementation (all new code)
├── sweep.toml                 # Parameter sweep specification (TOML-driven)
├── generate_configs.py        # Cartesian product config generator
├── generate_commands.py       # TAMULauncher: one command per sim → commands.txt
├── submit.slurm               # SLURM job array (legacy: hybrid 10 sims/task)
├── submit_tamulauncher.slurm  # TAMULauncher submit (no job array limit)
├── run_batch.py               # Per-batch runner with per-sim timing (SLURM array)
├── run_sim.py                 # Single-sim runner with timing JSON (TAMULauncher)
├── check_outputs.py           # Post-run validation & retry support
├── setup_aces.sh              # ACES environment bootstrap
│
├── parse_slurm.py             # Parse sacct output → slurm_timing.csv
├── aggregate.py               # 656 JSON logs + timing → run_summary.csv
├── timing_analysis.py         # Throughput/parallelism metrics + cumulative curves
├── analyze.py                 # Grouped statistics, penalty=0 stratification
├── plots.py                   # 7 presentation figures
│
├── slides.md                  # 12-slide presentation deck (Markdown)
├── speaking_notes.md          # Presenter script with timing
├── README.md                  # Project documentation
├── Makefile                   # Targets: configs, commands, aggregate, timing, analyze, plots
├── pyproject.toml             # Python project config
├── .python-version            # Python 3.12
│
├── configs/                   # 656 generated .config JSON files
├── commands.txt               # TAMULauncher commands file (one line per sim)
├── data/                      # 656 simulation JSON log outputs
├── timing/                    # Per-batch CSVs (SLURM) and downloaded per-sim JSONs (TAMULauncher)
│   └── timing_sim_*.json      # timing_sim_<job_id>.json — written in root on cluster, pulled here
├── results/                   # All analysis outputs (CSVs)
├── plots/                     # 7 presentation figures (PNG)
│
├── slurm_full.txt             # Raw sacct output from ACES
├── jobs.csv                   # Job manifest (job_id → config → params)
└── uv.lock                    # Locked dependency versions
```

## Script Reference

| Script | Reads | Writes | Purpose |
| :--- | :--- | :--- | :--- |
| `generate_configs.py` | `sweep.toml` | `configs/*.config`, `jobs.csv` | Generate 656 minimal JSON configs |
| `generate_commands.py` | `jobs.csv` | `commands.txt` | TAMULauncher: one command line per sim |
| `submit.slurm` | `jobs.csv` | `data/*.json`, `timing/*.csv` | **Legacy** SLURM job array |
| `submit_tamulauncher.slurm` | `commands.txt` | `data/*.json`, `timing_sim_*.json` | **TAMULauncher** submit (no array limit) |
| `run_batch.py` | config file | JSON log + timing CSV | Per-batch runner (SLURM job array) |
| `run_sim.py` | `jobs.csv`, config | JSON log + `timing_sim_<id>.json` | Single-sim runner (TAMULauncher worker) |
| `check_outputs.py` | `jobs.csv` | log summary | Post-run validation |
| `parse_slurm.py` | `slurm_full.txt` | `slurm_timing.csv` | Parse sacct output |
| `aggregate.py` | `data/*.json`, `timing/`, `jobs.csv` | `run_summary.csv` | Extract per-run metrics + baseline deltas |
| `timing_analysis.py` | `slurm_timing.csv`, `timing/*.csv` | `timing_summary.csv`, cumulative curves | Throughput, parallelism, node distribution |
| `analyze.py` | `run_summary.csv` | `summary_stats.csv`, `framework_*.csv` | Grouped stats, penalty stratification |
| `plots.py` | `run_summary.csv`, `slurm_timing.csv`, cumulative CSVs | `plots/*.png` | 7 presentation figures |

## Sugarscape Reference (read-only submodule)

Entry point: `sugarscape/sugarscape.py` — the `Sugarscape` class. Key files:
- `agent.py` — Agent model, disease contraction (`catchDisease`), immune system (hamming distance)
- `condition.py` — Disease/Depression classes, penalties, transmission
- `ethics.py` — Decision model subclasses: Bentham, Asimov, Temperance (+ PECS variant)
- `environment.py` — Grid, resource peaks, pollution
- `config.json` — Full parameter reference (two-level JSON: `dataCollectionOptions` + `sugarscapeOptions`)

### Config Structure

Configs are two-level JSON: `dataCollectionOptions` (seed count, parallelism, plots) and `sugarscapeOptions` (all simulation params). Passed via `--conf path/to/config.json`.

Key disease params (`sugarscapeOptions`):
- `startingDiseases` — number of random diseases generated at init
- `startingDiseasesPerAgent` — diseases assigned per agent at start
- `diseaseList` — named diseases (only `"zombieVirus"` exists)
- `diseaseTransmissionChance`, `diseaseTagStringLength`, `diseaseIncubationPeriod`
- `disease*Penalty` keys — aggression, fertility, happiness, movement, metabolism, vision
- `agentImmuneSystemLength` — immune tag length (hamming distance matching)
- `agentDiseaseProtectionChance` — probability of resisting infection

Ethical frameworks (`agentDecisionModels`):
`none`, `altruist`, `bentham`, `egoist`, `negativeBentham`, `asimov`, `temperance`, `temperancePECS`
Suffixes: `HalfLookahead`, `NoLookahead`, `Dynamic`

### Testing

No pytest or test framework. Tests are integration-only: `cd sugarscape && make test` runs every example config headless for 200 timesteps. Add new test configs as JSON in `sugarscape/examples/`.

## Lessons Learned

1. **CRLF line endings** — Windows files need `sed -i 's/\r$//'` on Linux clusters
2. **Path separators** — `os.path.join` produces `\` on Windows, breaks on Linux; force forward-slash
3. **SLURM SUBMIT_DIR** — Resolves to staging tmpdir, not project dir; use `PROJECT_DIR` env var instead
4. **ACES QOS limits** — Job array max size requires hybrid batching; TAMULauncher avoids this entirely
5. **Disease param range format** — Sugarscape validates `[min, max]` lists, not scalars
6. **Penalty calibration** — `[0, 2, 5]` caused instant extinction; reduced to `[0, 2, 3]`
7. **TAMULauncher commands.txt** — Must use LF line endings (not CRLF); `generate_commands.py` enforces this via `newline="\n"`

## Deliverables

- `slides.md` — 12-slide Markdown presentation with architecture, timing stats, and plots
- `speaking_notes.md` — Full presenter script with timing per slide
- `README.md` — Project documentation with setup and workflow
- `Makefile` — Automation targets
- `plots/*.png` — 7 presentation figures
- `results/*.csv` — 10 analysis CSVs (run_summary, summary_stats, framework comparisons, timing)
