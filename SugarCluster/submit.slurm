#!/bin/bash
#SBATCH --job-name=sugarscape-sweep
#SBATCH --array=1-80
#SBATCH --time=02:00:00
#SBATCH --mem=1G
#SBATCH --ntasks=1
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err

set -euo pipefail

# Ensure Python 3.12+ is available on compute nodes
if command -v module &> /dev/null; then
    module load GCCcore/13.3.0 Python/3.12.3
fi

PROJECT_DIR="${PROJECT_DIR:-}"
MAX_ARRAY_SLOTS="${MAX_ARRAY_SLOTS:-80}"

# Strip /SugarCluster from PROJECT_DIR if the user accidentally included it
if [ -n "$PROJECT_DIR" ] && [[ "$PROJECT_DIR" == */SugarCluster* ]]; then
    PROJECT_DIR="${PROJECT_DIR%/SugarCluster*}"
fi

# Auto-detect relative to script if PROJECT_DIR not set
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
fi

# Dynamically compute SIMS_PER_JOB to fully utilise MAX_ARRAY_SLOTS slots
JOBS_CSV="${PROJECT_DIR}/SugarCluster/jobs.csv"
TOTAL_SIMS=$(( $(wc -l < "${JOBS_CSV}") - 1 ))   # subtract header row
if [ -z "${SIMS_PER_JOB:-}" ]; then
    # ceil(TOTAL_SIMS / MAX_ARRAY_SLOTS)
    SIMS_PER_JOB=$(( (TOTAL_SIMS + MAX_ARRAY_SLOTS - 1) / MAX_ARRAY_SLOTS ))
fi
NUM_TASKS=$(( (TOTAL_SIMS + SIMS_PER_JOB - 1) / SIMS_PER_JOB ))

echo "[Config] total_sims=${TOTAL_SIMS}  sims_per_job=${SIMS_PER_JOB}  num_tasks=${NUM_TASKS}  max_slots=${MAX_ARRAY_SLOTS}"

# Exit cleanly if this task index is beyond the required task count
if [ "${SLURM_ARRAY_TASK_ID}" -gt "${NUM_TASKS}" ]; then
    echo "[Task ${SLURM_ARRAY_TASK_ID}] No work — beyond NUM_TASKS=${NUM_TASKS}. Exiting."
    exit 0
fi

# Compute the range of sim IDs for this array task
START_ID=$(( (SLURM_ARRAY_TASK_ID - 1) * SIMS_PER_JOB + 1 ))
END_ID=$(( START_ID + SIMS_PER_JOB - 1 ))
if [ "${END_ID}" -gt "${TOTAL_SIMS}" ]; then
    END_ID=${TOTAL_SIMS}
fi

# Activate venv if it exists, otherwise use module-loaded python3
if [ -f "${PROJECT_DIR}/SugarCluster/.venv/bin/activate" ]; then
    source "${PROJECT_DIR}/SugarCluster/.venv/bin/activate"
fi
PYTHON="$(command -v python3 || command -v python)"

echo "[Task ${SLURM_ARRAY_TASK_ID}] Running sims ${START_ID}..${END_ID} (${SIMS_PER_JOB} per task)"

"${PYTHON}" "${PROJECT_DIR}/SugarCluster/run_batch.py" \
    --project-dir "${PROJECT_DIR}" \
    --start-id "${START_ID}" \
    --end-id "${END_ID}"
