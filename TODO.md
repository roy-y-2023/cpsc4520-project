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

**Job counts:**
- Disease sweep: 3×3×3×3 × 8 = **648 jobs**
- Baseline (no disease): 8 jobs (minimal config: only `agentDecisionModels` + standard sim keys)
- **Total: 656 jobs**

**Output format:** JSON logs (`logfileFormat: "json"`)  
**Timesteps per job:** 1,000  
**Seed:** 12345

---

## Phase 0 — Local Prep & Config Generation (May 30, Afternoon)

- [x] **0.1 Write `SugarCluster/sweep.toml`**
  Flat TOML describing parameter grid, models, and baseline toggle. No `base_config` — generated configs are minimal so Sugarscape fills defaults.

- [x] **0.2 Implement `SugarCluster/generate_configs.py`**
  Reads `sweep.toml`. Outputs:
  - 656 `.config` JSON files to `SugarCluster/configs/`
  - `SugarCluster/jobs.csv` manifest mapping `ARRAY_TASK_ID` → config path + metadata (`run_type`, `framework`, sweep params)
  CLI: `--sweep`, `--outdir`, `--manifest`, optional `--models` and `--limit` for dry-runs.

- [x] **0.3 Implement `SugarCluster/submit.slurm`**
  SLURM job array template:
  ```bash
  #SBATCH --array=1-656%50
  #SBATCH --time=01:00:00
  #SBATCH --mem=4G
  CONFIG=$(sed -n "${SLURM_ARRAY_TASK_ID}p" jobs.csv | cut -d',' -f2)
  python sugarscape/sugarscape.py --conf $CONFIG
  ```

- [x] **0.4 Local dry-run**
  Generated 656 configs. Ran 5-timestep baseline test locally — Sugarscape loaded minimal config correctly and produced valid JSON log with all required metrics (`sickAgentsPercentage`, `giniCoefficient`, etc.).

---

## Phase 1 — ACES Setup & Pilot (May 30, Evening)

- [ ] **1.1 Transfer code to ACES**
  ```bash
  # From repo root on local machine
  rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
    SugarCluster/ sugarscape/ login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/
  ```

- [ ] **1.2 Run environment setup on ACES**
  ```bash
  ssh login.aces.hprc.tamu.edu
  cd ~/cpsc4520-project/SugarCluster
  bash setup_aces.sh
  ```

- [ ] **1.3 Submit pilot job (2 jobs: 1 baseline + 1 disease)**
  ```bash
  # On ACES, in SugarCluster/
  sbatch --array=1-2 submit.slurm
  ```
  Check results with:
  ```bash
  squeue -u $USER
  python check_outputs.py --manifest jobs.csv --logdir .
  ```

---

## Phase 2 — Full Distributed Run (May 30, Late Evening)

- [ ] **2.1 Submit full 656-job array**
  `sbatch SugarCluster/submit.slurm`

- [ ] **2.2 Monitor queue**
  Watch with `squeue -u $USER` and `sacct`.

- [ ] **2.3 Validate outputs**
  ```bash
  python check_outputs.py --manifest jobs.csv --logdir .
  ```
  Re-run any failed jobs with:
  ```bash
  awk -F',' 'NR>1{print $2}' retry.csv | xargs -I {} sed -n "${SLURM_ARRAY_TASK_ID}p" {}
  ```

- [ ] **2.4 Re-submit failures (if any)**
  If >0 jobs fail, submit a secondary array only for missing indices.

---

## Phase 3 — Data Retrieval & Aggregation (May 31, Morning)

- [ ] **3.1 `rsync` logs back to local machine**
  Target: `SugarCluster/data/` directory.

- [ ] **3.2 Implement `SugarCluster/aggregate.py`**
  Parse all 656 JSON logs. Extract per-timestep metrics:
  - `sickAgentsPercentage` (primary disease-spread metric)
  - `population`, `meanDeathsPercentage`, `meanAgeAtDeath`
  - `giniCoefficient`, `meanHappiness`, `meanWealth`
  - Group by `(run_type, framework, transmission, tagLength, immunity, penalty)`

- [ ] **3.3 Implement `SugarCluster/analyze.py`**
  Compute summary statistics per parameter combo:
  - Time-to-peak infection
  - Steady-state sick percentage
  - Survival rate at t=1000
  - Gini & happiness under pandemic vs. baseline

---

## Phase 4 — Visualization (May 31, Afternoon)

- [ ] **4.1 Generate comparison plots**
  Custom matplotlib scripts to produce:
  - Heatmaps: infection peak vs. (transmission × immunity) per framework
  - Line charts: `sickAgentsPercentage` over time for best/worst frameworks
  - Bar charts: Gini coefficient & survival rate across frameworks (disease vs. baseline)
  - Facet grids: effect of each knob on spread

- [ ] **4.2 Answer the two research questions**
  - *Q1: Which parameters maximize/minimize spread?*
  - *Q2: How do socio-economics interact with pandemics?*

---

## Phase 5 — Presentation & Packaging (May 31, Evening / June 1 AM)

- [ ] **5.1 Build 8-minute slide deck**
  Sections:
  1. Project overview & research questions (1 min)  2. Architecture diagram: config gen → ACES SLURM → data pull → analysis (3 min)
    - Audience have general understanding of distributed computing, but not ACES specifically
  3. Results showcase (plots) (2 min)
  4. Challenges & lessons learned (1 min)
    - Decide which distributed runtime to use
    - Had issue with file path, ended up have to hardcode absolute path in files.
  5. Future work (1 min)
    - Make it support more parameters.
    - Make it portable to other users and clusters.

- [ ] **5.2 Write `SugarCluster/README.md`**
  Install steps, how to run `generate_configs.py`, how to submit to ACES, how to regenerate plots.

- [ ] **5.3 Write / update root `Makefile`**
  Targets: `make configs`, `make submit`, `make fetch`, `make analyze`, `make plots`, `make slides`.

- [ ] **5.4 Package `final.zip`**
  Contents: all `SugarCluster/` source, sample configs, raw JSON logs (subset or all if <2GB), all plots, slide PDF, README.

---

## Hour-by-Hour Timeline

| Time (PDT) | Task |
| :--- | :--- |
| **May 30 14:00** | 0.1–0.4: Write `sweep.toml`, `generate_configs.py`, local dry-run |
| **May 30 18:00** | 1.1–1.3: ACES transfer & pilot |
| **May 30 21:00** | 2.1–2.2: Submit 656-job array |
| **May 31 08:00** | 2.3–3.1: Validate & pull data |
| **May 31 12:00** | 3.2–4.2: Aggregate, analyze, generate plots |
| **May 31 18:00** | 5.1–5.3: Slides, README, Makefile |
| **June 01 10:00** | 5.4: Final packaging & submission |

---

## Risks

1. **ACES queue depth:** 656 jobs may queue for hours if the cluster is busy. The `%50` throttle mitigates this.
2. **Sugarscape submodule on ACES:** Ensure directory is transferred (not a broken git submodule link). `rsync` the files directly.
3. **ACES Python environment:** If `uv` is not installed, use `module load python/3.12` + `python -m venv`.
4. **Minimal configs:** Sugarscape must handle omitted keys gracefully (it does, per its default-config logic).
