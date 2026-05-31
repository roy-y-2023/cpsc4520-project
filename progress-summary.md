# SugarCluster — Progress Summary

**Course:** CPSC 4520 — Distributed Systems
**Date:** May 30, 2026

---

## Overview

For this project we're building middleware to run the Sugarscape agent-based simulation at scale on the ACES supercomputer. The goal is to study how disease parameters and ethical frameworks affect disease spread. We're sweeping across 8 ethical frameworks and 81 disease parameter combos, plus 8 baselines — 656 simulation jobs total.

## What We Have Working

**Config generator** (`generate_configs.py`): Reads `sweep.toml`, generates 656 JSON configs and a `jobs.csv` manifest. Each config maps to a SLURM array task. Supports 4 disease parameters (transmission chance, tag string length, immune system length, metabolism penalty) with 3 values each.

**SLURM submission** (`submit.slurm`): Array job that runs `--array=1-656%50`, 1 hour walltime, 4GB memory per task. Reads the config path from `jobs.csv` and runs Sugarscape headless.

**ACES setup script** (`setup_aces.sh`): Handles Python 3.12 detection, venv creation, `tomli` install, and runs a smoke test to make sure everything works.

**Output checker** (`check_outputs.py`): Goes through all 656 logs, checks they exist, are valid JSON, aren't empty, and ran to the full 1000 timesteps. Writes failed jobs to `retry.csv`.

**Local dry-run**: Tested a 5-timestep run locally. Sugarscape loads the config fine and produces valid JSON output.

## What's Not Done Yet

- `main.py` is just a placeholder — no orchestration logic
- No data analysis code — need `aggregate.py` to parse logs and `analyze.py` for statistics
- No plotting or visualization scripts
- No README, slides, or final submission package

## Remaining Work

| Phase | What | Status |
|-------|------|--------|
| 1 | Transfer to ACES, run setup, pilot job | Not started |
| 2 | Submit all 656 jobs, monitor, validate | Not started |
| 3 | Pull logs back, write aggregate/analyze scripts | Not started |
| 4 | Generate plots, answer research questions | Not started |
| 5 | Slides, README, Makefile, `final.zip` | Not started |

Next up is getting the code onto ACES and running a pilot job to make sure the whole pipeline works end-to-end. Plan to submit all 656 jobs tonight and let them run overnight.
