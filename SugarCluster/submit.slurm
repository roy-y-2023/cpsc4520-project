#!/bin/bash
#SBATCH --job-name=sugarscape-sweep
#SBATCH --array=1-656%50
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --ntasks=1
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err

set -euo pipefail

# Project root — override with PROJECT_DIR env var for ACES
# Default: resolved relative to this script's location
PROJECT_DIR="${PROJECT_DIR}"
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
fi

CLUSTER_DIR="${PROJECT_DIR}/SugarCluster"
SUGARSCAPE_DIR="${PROJECT_DIR}/sugarscape"

# Derive config path from the manifest
# jobs.csv columns: job_id,run_type,framework,config_path,...
CONFIG_PATH=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "${CLUSTER_DIR}/jobs.csv" | cut -d',' -f4)

if [ -z "$CONFIG_PATH" ] || [ ! -f "${CLUSTER_DIR}/${CONFIG_PATH}" ]; then
    echo "ERROR: Config not found for array task ${SLURM_ARRAY_TASK_ID} -> ${CONFIG_PATH}" >&2
    exit 1
fi

cd "${CLUSTER_DIR}"
echo "[Task ${SLURM_ARRAY_TASK_ID}] Running ${CONFIG_PATH}"
python "${SUGARSCAPE_DIR}/sugarscape.py" --conf "${CONFIG_PATH}"
