# AGENTS.md

## Project Overview

Middleware to run the Sugarscape agent-based simulation at scale for disease spread experiments. The `sugarscape/` directory is a **read-only git submodule** — never modify files inside it. All new code lives in the repo root.

## Questions to Explore
- How does different parameters maximize/minimize the spread of disease?
- How does socio-economics factors play with "pandemics"?

## Setup

- Python 3.11+, managed with **uv**
- Initialize: `uv init` then `uv add` any dependencies
- The sugarscape submodule is imported as a local package — add it to `pyproject.toml` paths

## Sugarscape Reference (read-only)

Entry point: `sugarscape/sugarscape.py` — the `Sugarscape` class. Key files:
- `agent.py` — Agent model, disease contraction (`catchDisease`), immune system (hamming distance)
- `condition.py` — Disease/Depression classes, penalties, transmission
- `ethics.py` — Decision model subclasses: Bentham, Asimov, Temperance (+ PECS variant)
- `environment.py` — Grid, resource peaks, pollution
- `config.json` — Full parameter reference (two-level JSON: `dataCollectionOptions` + `sugarscapeOptions`)

### Running Sugarscape Locally (reference only)

```bash
cd sugarscape
python sugarscape.py --conf config.json       # GUI mode
# Set "headlessMode": true in config for batch runs
```

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

### Data Collection Flow

1. `make seeds` — generates random seed configs in `data/`
2. `make data` — runs all seed configs (controlled by `numSeeds`, `numParallelSimJobs`)
3. `make plots` — generates PDF plots from collected data
4. `make test` — runs all `examples/*.json` at 200 timesteps (not pytest)

### Testing

No pytest or test framework. Tests are integration-only: `cd sugarscape && make test` runs every example config headless for 200 timesteps. Add new test configs as JSON in `sugarscape/examples/`.

### Logging

- `logfile` — path for simulation output (JSON or CSV, set by `logfileFormat`)
- `agentLogfile` — per-agent detailed logs
- `experimentalGroup` — track specific agent subsets (e.g., `"disease"`, `"sick"`, `"female"`, decision model names)
