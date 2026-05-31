# SugarCluster TODO — Step 5 Onward
**Deadline:** June 1, 2026

## Experimental Design

| Parameter | Values |
| :--- | :--- |
| `diseaseTransmissionChance` | 0.3, 0.6, 1.0 |
| `diseaseTagStringLength` | 5, 13, 21 |
| `agentImmuneSystemLength` | 10, 35, 60 |
| `diseaseSugarMetabolismPenalty` (= `diseaseSpiceMetabolismPenalty`) | 0, 2, 5 |
| **Ethical frameworks** | `none`, `altruist`, `bentham`, `egoist`, `negativeBentham`, `asimov`, `temperance`, `temperancePECS` |

**Total jobs:** 3×3×3×3 × 8 = **648 jobs**
**Timesteps per job:** 1,000
**Output format:** JSON logs (`logfileFormat: "json"`)

---

## Phase 0 — Local Prep & Config Generation (May 30, Afternoon)

- [ ] **0.1 Design config schema**
  Define naming convention: `bentham_t0.3_tag13_imm35_pen2_seed12345.json`
  Map each `ARRAY_TASK_ID` to a config path via a manifest file.

- [ ] **0.2 Implement `SugarCluster/generate_configs.py`**
  Adapts `sugarscape/data/run.py` logic.
  - Input: base `config.json`, parameter grid, seed
  - Output: 648 `.config` files to `SugarCluster/configs/` + master manifest `SugarCluster/jobs.csv`

- [ ] **0.3 Implement `SugarCluster/submit.slurm`**
  SLURM job array template:
  ```bash
  #SBATCH --array=1-648%50
  #SBATCH --time=01:00:00
  #SBATCH --mem=4G
  CONFIG=$(sed -n "${SLURM_ARRAY_TASK_ID}p" jobs.csv | cut -d',' -f2)
  python sugarscape/sugarscape.py --conf $CONFIG
  ```

- [ ] **0.4 Local dry-run**
  Run `generate_configs.py`. Verify 648 files created and one sample config loads correctly.

---

## Phase 1 — ACES Setup & Pilot (May 30, Evening)

- [ ] **1.1 Transfer code to ACES**
  ```bash
  rsync -avz --exclude '.venv' --exclude '__pycache__' \
    SugarCluster/ sugarscape/ <user>@login.aces.hprc.tamu.edu:/scratch/user/<user>/SugarCluster/
  ```

- [ ] **1.2 Environment setup on ACES**
  Load Python 3.12 module, create venv, install dependencies.

- [ ] **1.3 Pilot job**
  Submit 1-job test (`--array=1-1`) to confirm:
  - Sugarscape submodule loads correctly
  - JSON log written to scratch
  - Job completes within walltime

---

## Phase 2 — Full Distributed Run (May 30, Late Evening)

- [ ] **2.1 Submit full 648-job array**
  `sbatch SugarCluster/submit.slurm`

- [ ] **2.2 Monitor queue**
  Watch with `squeue -u $USER` and `sacct`.

- [ ] **2.3 Validate outputs**
  Run `SugarCluster/check_outputs.py` on ACES to verify every JSON log exists and reached timestep 1000.

- [ ] **2.4 Re-submit failures (if any)**
  Submit secondary array only for missing indices.

---

## Phase 3 — Data Retrieval & Aggregation (May 31, Morning)

- [ ] **3.1 `rsync` logs back to local machine**
  Target: `SugarCluster/data/` directory.

- [ ] **3.2 Implement `SugarCluster/aggregate.py`**
  Parse all 648 JSON logs. Extract per-timestep metrics:
  - `sickAgentsPercentage` (primary disease-spread metric)
  - `population`, `meanDeathsPercentage`, `meanAgeAtDeath`
  - `giniCoefficient`, `meanHappiness`, `meanWealth`
  - Group by `(framework, transmission, tagLength, immunity, penalty)`

- [ ] **3.3 Implement `SugarCluster/analyze.py`**
  Compute summary statistics per parameter combo:
  - Time-to-peak infection
  - Steady-state sick percentage
  - Survival rate at t=1000
  - Gini & happiness under pandemic

---

## Phase 4 — Visualization (May 31, Afternoon)

- [ ] **4.1 Generate comparison plots**
  - Heatmaps: infection peak vs. (transmission × immunity) per framework
  - Line charts: `sickAgentsPercentage` over time for best/worst frameworks
  - Bar charts: Gini coefficient & survival rate across frameworks
  - Facet grids: effect of each knob on spread

- [ ] **4.2 Answer the two research questions**
  - *Q1: Which parameters maximize/minimize spread?*
  - *Q2: How do socio-economics interact with pandemics?*

---

## Phase 5 — Presentation & Packaging (May 31, Evening / June 1 AM)

- [ ] **5.1 Build 8-minute slide deck**
  Sections:
  1. Project overview & research questions (1 min)
  2. Architecture diagram: config gen → ACES SLURM → data pull → analysis (1 min)
  3. Results showcase (plots) (4 min)
  4. Challenges & lessons learned (1 min)
  5. Future work (1 min)

- [ ] **5.2 Write `SugarCluster/README.md`**
  Install steps, how to run generators, how to submit to ACES, how to regenerate plots.

- [ ] **5.3 Write / update root `Makefile`**
  Targets: `make configs`, `make submit`, `make fetch`, `make analyze`, `make plots`, `make slides`.

- [ ] **5.4 Package `final.zip`**
  All `SugarCluster/` source, sample configs, raw JSON logs (subset or all if <2GB), all plots, slide PDF, README.

---

## Hour-by-Hour Timeline

| Time (PDT) | Task |
| :--- | :--- |
| **May 30 14:00** | 0.1–0.4: Local config generation & dry-run |
| **May 30 18:00** | 1.1–1.3: ACES transfer & pilot |
| **May 30 21:00** | 2.1–2.2: Submit 648-job array |
| **May 31 08:00** | 2.3–3.1: Validate & pull data |
| **May 31 12:00** | 3.2–4.2: Aggregate, analyze, plot |
| **May 31 18:00** | 5.1–5.3: Slides, README, Makefile |
| **June 01 10:00** | 5.4: Final packaging & submission |

---

## Risks

1. **ACES queue depth:** 648 jobs may queue for hours if the cluster is busy. The `%50` throttle mitigates this.
2. **Sugarscape submodule on ACES:** Ensure directory is transferred (not a broken git submodule link).
3. **ACES Python environment:** If `uv` is not installed, use `module load python/3.12` + `python -m venv`.
