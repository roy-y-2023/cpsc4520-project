#!/bin/bash
#SBATCH --job-name=sugarscape-sweep
#SBATCH --array=1-51%50
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --ntasks=1
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err

set -euo pipefail

# Ensure Python 3.12+ is available on compute nodes
if command -v module &> /dev/null; then
    module load GCCcore/13.3.0 Python/3.12.3
fi


# --- Configuration (override via environment variables) ---
# PROJECT_DIR: root containing SugarCluster/ and sugarscape/
# SIMS_PER_JOB: how many simulations each array task runs (default 10)
#
# Usage:
#   PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project \
#       SIMS_PER_JOB=10 \
#       sbatch --array=1-66%50 -A 155415875505 submit.slurm
# ----------------------------------------------------------

PROJECT_DIR="${PROJECT_DIR:-}"
SIMS_PER_JOB="${SIMS_PER_JOB:-30}"

# Strip /SugarCluster from PROJECT_DIR if the user accidentally included it
if [ -n "$PROJECT_DIR" ] && [[ "$PROJECT_DIR" == */SugarCluster* ]]; then
    PROJECT_DIR="${PROJECT_DIR%/SugarCluster*}"
fi

# Auto-detect relative to script if PROJECT_DIR not set
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
fi

# Compute the range of job IDs for this array task
START_ID=$(( (SLURM_ARRAY_TASK_ID - 1) * SIMS_PER_JOB + 1 ))
END_ID=$(( START_ID + SIMS_PER_JOB - 1 ))

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
