# SugarCluster — Final Project Progress Summary

**Course:** CPSC 4520 — Distributed Systems
**Project:** SugarCluster — Scaling the Sugarscape Agent-Based Simulation for Disease Spread Experiments
**Date:** May 30, 2026

---

## 1. Project Overview

SugarCluster is middleware designed to run the Sugarscape agent-based societal simulation at scale on the ACES supercomputer at Texas A&M. The goal is to study how different disease parameters and ethical decision frameworks affect the spread of disease across a population. Two core research questions drive the project:

- **Q1:** How do different disease parameters maximize or minimize the spread of disease?
- **Q2:** How do socio-economic factors (ethical decision models) interact with pandemics?

The experimental design sweeps across 8 ethical frameworks and 81 disease parameter combinations (3 values each for transmission chance, tag string length, immune system length, and metabolism penalty), plus 8 baseline configurations, for a total of **656 simulation jobs**.

---

## 2. What Is Working

### 2.1 Parameter Sweep Configuration Generation

A fully functional configuration generation pipeline has been implemented. The system reads a TOML sweep specification (`sweep.toml`) and produces **656 JSON config files** organized by ethical framework and disease parameter combination. Each config specifies simulation parameters including timesteps (1000), headless mode, seed values, and logging format.

- **Sweep dimensions:** 8 frameworks x (1 baseline + 81 disease combos) = 656 jobs
- **Disease parameters swept:** `diseaseTransmissionChance` (0.3, 0.6, 1.0), `diseaseTagStringLength` (5, 13, 21), `agentImmuneSystemLength` (10, 35, 60), `diseaseSugarMetabolismPenalty` (0, 2, 5)
- **Output:** 656 `.config` files in `SugarCluster/configs/` and a `jobs.csv` manifest mapping array task IDs to config paths

### 2.2 HPC Submission Infrastructure

The SLURM batch submission pipeline is complete. The `submit.slurm` script dispatches jobs as a SLURM array job (`--array=1-656%50`) with a 1-hour walltime and 4 GB memory per task. Each task reads its config path from `jobs.csv` and runs the Sugarscape simulation headless. The `setup_aces.sh` script handles one-time environment setup on ACES, including Python 3.12 detection, virtual environment creation, dependency installation, and a smoke test.

### 2.3 Output Validation

A post-run validation tool (`check_outputs.py`) has been implemented. It reads the job manifest, locates each expected logfile, and checks for existence, valid JSON, non-empty content, and completion to the expected timestep count. Failed jobs are written to `retry.csv` for easy resubmission.

### 2.4 Local Dry-Run Verification

A local dry-run confirmed that the Sugarscape simulation engine correctly loads minimal configurations and produces valid JSON logs containing the required metrics (sickAgentsPercentage, population, deaths, Gini coefficient, happiness, wealth). The `SugarCluster` package correctly injects the read-only `sugarscape/` submodule into `sys.path` at import time.

---

## 3. What Is Not Yet Working

### 3.1 Orchestration Entry Point

The `main.py` file is currently a stub that prints a greeting. No orchestration logic has been implemented — the middleware does not yet coordinate simulation runs, aggregate results, or provide a unified interface for running experiments.

### 3.2 Data Analysis Pipeline

No code exists for parsing or analyzing the simulation output logs. The planned `aggregate.py` (to parse 656 JSON logs and extract per-timestep metrics) and `analyze.py` (to compute summary statistics such as time-to-peak infection, steady-state sick percentage, and survival rate) have not been implemented.

### 3.3 Visualization

No plotting or visualization scripts have been created. The project requires comparison plots (heatmaps, line charts, bar charts, facet grids) to answer the two research questions and present findings.

### 3.4 Documentation and Packaging

The `README.md` file is empty. No slide deck, Makefile, or final submission package (`final.zip`) has been created.

---

## 4. What Remains by Project Deadline (June 1)

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Transfer code to ACES, run environment setup, submit pilot job (2 tasks) | Not started |
| **Phase 2** | Submit all 656 jobs to SLURM, monitor queue, validate outputs, re-run failures | Not started |
| **Phase 3** | rsync logs back locally, implement `aggregate.py` and `analyze.py` | Not started |
| **Phase 4** | Generate comparison plots, answer research questions | Not started |
| **Phase 5** | Build slide deck, write README, create Makefile, package `final.zip` | Not started |

The immediate next step is **Phase 1** — transferring code to the ACES cluster and running a pilot job to verify the pipeline end-to-end. Phases 1 and 2 are planned for this evening, with Phases 3-5 filling tomorrow and Sunday morning.

---

## 5. Conclusion

The project has completed its local preparation phase. The config generation pipeline, SLURM submission script, output validation tool, and ACES setup script are all functional and verified. The remaining work consists of running the distributed simulation on ACES (Phases 1-2), implementing the data analysis and visualization pipeline (Phases 3-4), and preparing the final presentation materials (Phase 5).
