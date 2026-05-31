# CPSC 4520 Final Project Progress

SugarCluster, running the Sugarscape simulation at scale on ACES to study disease spread.

We're using the Sugarscape agent-based simulation and running it on the ACES supercomputer. The idea is to see how different disease parameters and ethical frameworks change how disease spreads through a population. We're testing 8 ethical frameworks with 81 disease parameter combos each, plus 8 baseline runs without disease, so 656 jobs total.

## What's done

We got a few things working already. First, there's a config generator (`generate_configs.py`) that reads a TOML file (`sweep.toml`) and spits out 656 JSON configs. Each one maps to a SLURM array task through a `jobs.csv` file. The configs cover 4 disease parameters: transmission chance, tag string length, immune system length, and metabolism penalty, with 3 values each.

We also have the SLURM submission script (`submit.slurm`). It runs an array job with 656 tasks, 50 at a time, with a 1-hour walltime and 4GB memory each. It reads the config path from `jobs.csv` and runs Sugarscape headless.

There's an ACES setup script (`setup_aces.sh`) that finds Python 3.12, sets up a venv, installs the dependencies, and runs a quick smoke test to make sure Sugarscape actually works on the cluster.

We built an output checker too (`check_outputs.py`). It goes through all 656 logs and checks if they exist, are valid JSON, aren't empty, and ran to 1000 timesteps. If something failed, it writes those jobs to `retry.csv` so we can resubmit them.

We tested it locally with a 5-timestep run and Sugarscape loaded the config fine and produced valid JSON output.

## What's not done

- `main.py` is still just a placeholder, no real logic in it yet
- We don't have any data analysis code, need to write `aggregate.py` to parse the logs and `analyze.py` for stats
- No plotting or visualization stuff yet
- README is empty, no slides or final submission package

## What's left

Phase 1 is next, we need to get the code onto ACES, set up the environment, and run a pilot job to make sure everything works end-to-end. After that we'll submit all 656 jobs and let them run overnight. Then we pull the logs back, write the analysis and plotting code, and put together the slides and final package.
