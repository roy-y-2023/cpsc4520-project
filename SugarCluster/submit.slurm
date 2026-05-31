#!/bin/bash
#SBATCH --job-name=sugarscape-sweep
#SBATCH --array=1-656%50
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err

set -euo pipefail

# Change to the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Find sugarscape relative to this directory (assumes sibling repo checkout)
SUGARSCAPE_DIR="${SUGARSCAPE_DIR:-../sugarscape}"

# Derive config path from the manifest
# jobs.csv columns: job_id,run_type,framework,config_path,...
CONFIG_PATH=$(sed -n "${SLURM_ARRAY_TASK_ID}p" jobs.csv | cut -d',' -f4)

if [ -z "$CONFIG_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Config not found for array task ${SLURM_ARRAY_TASK_ID} -> ${CONFIG_PATH}" >&2
    exit 1
fi

echo "[Task ${SLURM_ARRAY_TASK_ID}] Running ${CONFIG_PATH}"
python "${SUGARSCAPE_DIR}/sugarscape.py" --conf "${CONFIG_PATH}"
