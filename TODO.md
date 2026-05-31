# SugarCluster TODO — Step 5 Onward
**Deadline:** June 1, 2026

## Experimental Design

| Parameter | Values |
| :--- | :--- |
| `diseaseTransmissionChance` | 0.3, 0.6, 1.0 |
| `diseaseTagStringLength` | 5, 13, 21 |
| `agentImmuneSystemLength` | 10, 35, 60 |
| `diseaseSugarMetabolismPenalty` (= `diseaseSpiceMetabolismPenalty`) | 0, 2, 3 |
| **Ethical frameworks** | `none`, `altruist`, `bentham`, `egoist`, `negativeBentham`, `asimov`, `temperance`, `temperancePECS` |

**Job counts:**
- Disease sweep: 3×3×3×3 × 8 = **648 jobs**
- Baseline (no disease): 8 jobs (minimal config)
- **Total: 656 jobs**

**Output format:** JSON logs  
**Timesteps per job:** 1,000  
**Seed:** 12345

---

## Phase 0 — Local Prep & Config Generation (May 30, Afternoon)

- [x] **0.1 Write `SugarCluster/sweep.toml`**
  TOML-driven parameter sweep config. No hard-coded values — fully reusable.
- [x] **0.2 Implement `SugarCluster/generate_configs.py`**
  Generates 656 `.config` files + `jobs.csv` manifest.
  CLI: `--sweep`, `--outdir`, `--manifest`, `--models`, `--limit`.
- [x] **0.3 Implement `SugarCluster/submit.slurm`**
  SLURM job array with configurable `PROJECT_DIR` and `SIMS_PER_JOB`.
- [x] **0.4 Local dry-run**
  Ran 5-timestep test — config loaded correctly, JSON log produced.

---

## Phase 1 — ACES Setup & Pilot (May 30, Evening)

- [x] **1.1 Transfer code to ACES**
- [x] **1.2 Run environment setup on ACES**
- [x] **1.3 Submit pilot job**
  Verified baseline and disease runs work interactively on ACES.

---

## Phase 2 — Full Distributed Run (May 30, Late Evening → May 31)

- [x] **2.1 Submit hybrid 66-task array** (SIMS_PER_JOB=10, 10 sims per SLURM task)
- [x] **2.2 Monitor queue** — All 656 jobs completed on ACES
- [x] **2.3 Validate outputs** — `check_outputs.py` confirms all logs exist; extinction events correctly classified as valid termination
- [x] **2.4 Timing data collected** — Per-simulation durations saved in `timing_*.csv` files

---

## Phase 3 — Data Retrieval & Aggregation (May 31, Morning)

- [x] **3.1 Pull data from ACES**
  JSON logs and timing CSVs transferred to local machine.

- [x] **3.2 Implement `SugarCluster/aggregate.py`**
  Parses all 656 JSON logs + timing CSVs + `jobs.csv` → `results/run_summary.csv`
  - Per-run summary: `final_timestep`, `survived`, `time_to_extinction`, `peak_sick_percentage`, `avg_sick_percentage`, death counts
  - Derived metrics: `wealth_gini_change`, `happiness_decline`
  - Baseline comparison via `delta_*` columns (e.g., `delta_final_gini`, `delta_final_happiness`)
  - Timing merged from per-batch CSVs

- [x] **3.3 Implement `SugarCluster/analyze.py`**
  Loads `run_summary.csv` → `results/summary_stats.csv` (648 grouped rows) + `results/framework_comparison.csv` (8 rows)
  - Groups by `(framework, transmission, tagLength, immunity, penalty)` for granular analysis
  - Aggregates across all disease params per framework for high-level comparison

---

## Phase 4 — Visualization (May 31, Afternoon)

- [x] **4.1 Generate comparison plots** (7 figures, timing-focused)
  1. `cumulative_completion.png` — real (SLURM sacct) vs theoretical cumulative completion
  2. `slurm_task_duration.png` — histogram of 66 SLURM task durations (34–82s)
  3. `node_distribution.png` — ACES node load distribution (20 nodes)
  4. `timing_by_penalty.png` — per-sim duration by penalty (bimodal: 0.1s vs 10s)
  5. `heatmap_penalty0.png` — peak infection heatmaps, **penalty=0 only** (where frameworks differ)
  6. `survival_stacked.png` — survival rate by penalty level per framework
  7. `gini_penalty0.png` — Gini delta for penalty=0 subset

- [x] **4.2 Distributed Systems Timing Stats**
  - **25.7x parallelism** — 3,681 serial-seconds completed in 143s wall time
  - **16,515 sims/wall-hour** throughput
  - **1.3% batch overhead** — only 0.8s of Python startup per 10-sim batch
  - **20 ACES nodes**, 66 SLURM tasks, 1722415 job array

- [x] **4.3 Key Scientific Findings**
  - **Penalty dominates everything** — penalty=0 → 100% survival; penalty=2/3 → 11% survival regardless of framework
  - **All 8 frameworks are near-identical** — disease severity physics overwhelm ethical differences
  - **Delta Gini ≈ 0 for penalty=0** — mean inequality unchanged by pandemic (blue = baseline, orange = pandemic)
  - **Short simulations (<0.5s) are instant extinction** — penalty=2/3 kills all 250 agents at timestep 1

---

## Phase 5 — Presentation & Packaging (May 31, Evening / June 1 AM)

- [ ] **5.1 Build 8-minute slide deck**
  Sections:
  1. Project overview & research questions (1 min)
  2. Architecture and diagram: config gen → ACES SLURM → data pull → analysis (2 min)
    - Audience have general understanding of distributed computing, but not ACES specifically
  3. Results showcase (plots) (2 min)
  4. Challenges & lessons learned (2 min)
     - Distributed runtime selection (SLURM vs Drona Workflow Engine / TAMULauncher vs MPI vs setting up something with CCTools)
     - ACES job array QOS limits → hybrid batching
     - Windows/Linux path separator issues (CRLF). Code runs locally might not run on a external cluster easily.
     - Disease parameter scaling (penalty severity)
  5. Future work (1 min)
    - Make it support more parameters.
    - Make it portable to other users and clusters.

- [ ] **5.2 Write `SugarCluster/README.md`**
  Install steps, `generate_configs.py` usage, ACES submission, plot regeneration.

- [ ] **5.3 Write root `Makefile`**
  Targets: `make configs`, `make submit`, `make fetch`, `make analyze`, `make plots`, `make slides`.

- [ ] **5.4 Package `final.zip`**
  All source, configs, raw JSON logs (subset if >2GB), all plots, slide PDF, README.

---

## Updated Timeline

| Time (PDT) | Task |
| :--- | :--- |
| **May 31 Morning** | 3.2–3.3: Aggregate & analyze data |
| **May 31 Afternoon** | 4.1–4.2: Generate plots & answer research questions |
| **May 31 Evening** | 5.1–5.3: Slides, README, Makefile |
| **June 01 10:00** | 5.4: Final packaging & submission |

---

## Lessons Learned (for presentation)

1. **Path separators across platforms** — `os.path.join` produces `\` on Windows, breaks on Linux
2. **CRLF line endings** — Windows files need `dos2unix` on Linux clusters
3. **Absolute paths in SLURM scripts** — `$SCRIPT_DIR` resolves to staging tmpdir, not project dir
4. **ACES QOS limits** — Job array limits require batching (SIMS_PER_JOB=10)
5. **Sugarscape expects lists for disease ranges** — `diseaseTransmissionChance: [0.3, 0.3]` not `0.3`
6. **Penalty severity** — `[0, 2, 5]` caused instant extinction; reduced to `[0, 2, 3]` for observable dynamics
