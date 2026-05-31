#!/bin/bash
# ACES Environment Setup for SugarCluster
# Run this on the login node: bash setup_aces.sh
set -euo pipefail

# Paths — adjust if needed
PROJECT_DIR="/scratch/group/p.cis260910.000/cpsc4520-project"
SUGARSCAPE_DIR="${PROJECT_DIR}/sugarscape"
CLUSTER_DIR="${PROJECT_DIR}/SugarCluster"

echo "=== Setting up SugarCluster on ACES ==="

# 1. Create project directory structure
mkdir -p "${PROJECT_DIR}"
mkdir -p "${CLUSTER_DIR}/logs"

# 2. Find Python 3.12
PYTHON=""
for candidate in python3.12 python3 python; do
    if command -v $candidate &>/dev/null; then
        VER=$($candidate --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR=$(echo $VER | cut -d. -f1)
        MINOR=$(echo $VER | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "No Python 3.11+ found. Trying module load..."
    module load GCCcore/13.3.0 Python/3.12.3
    PYTHON="python3"
fi

echo "Using: $($PYTHON --version)"

# 3. Create virtual environment
cd "${CLUSTER_DIR}"
if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv
    echo "Virtual environment created."
fi

# 4. Install dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install tomli

# 5. Quick smoke test
echo "=== Smoke test: running 5-timestep baseline ==="
cd "${PROJECT_DIR}"
cat > /tmp/test_baseline.json << 'TESTJSON'
{
    "agentDecisionModels": ["none"],
    "timesteps": 5,
    "seed": 12345,
    "headlessMode": true,
    "logfileFormat": "json",
    "logfile": "/tmp/test_baseline_output.json"
}
TESTJSON
python sugarscape/sugarscape.py --conf /tmp/test_baseline.json 2>&1 || true

if [ -f "/tmp/test_baseline_output.json" ]; then
    echo "Smoke test PASSED — log file produced at /tmp/test_baseline_output.json"
else
    echo "Smoke test produced no log file — check for errors above"
fi

echo "=== Setup complete ==="
echo "Projects directory: ${PROJECT_DIR}"
echo "To run: cd ${CLUSTER_DIR} && sbatch submit.slurm"
