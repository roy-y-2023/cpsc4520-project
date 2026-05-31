#!/bin/bash
#SBATCH --job-name=sugarscape-sweep
#SBATCH --array=1-66%50
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --ntasks=1
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err

set -euo pipefail

# --- Configuration (override via environment variables) ---
# PROJECT_DIR: root containing SugarCluster/ and sugarscape/
# SIMS_PER_JOB: how many simulations each array task runs (default 10)
#
# Usage:
#   PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project \
#       SIMS_PER_JOB=10 \
#       sbatch --array=1-66%50 -A 155415875505 submit.slurm
# ----------------------------------------------------------

PROJECT_DIR="${PROJECT_DIR}"
SIMS_PER_JOB="${SIMS_PER_JOB:-10}"

# Auto-detect relative to script if PROJECT_DIR not set
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
fi

# Compute the range of job IDs for this array task
START_ID=$(( (SLURM_ARRAY_TASK_ID - 1) * SIMS_PER_JOB + 1 ))
END_ID=$(( START_ID + SIMS_PER_JOB - 1 ))

echo "[Task ${SLURM_ARRAY_TASK_ID}] Running sims ${START_ID}..${END_ID} (${SIMS_PER_JOB} per task)"

python "${PROJECT_DIR}/SugarCluster/run_batch.py" \
    --project-dir "${PROJECT_DIR}" \
    --start-id "${START_ID}" \
    --end-id "${END_ID}"
