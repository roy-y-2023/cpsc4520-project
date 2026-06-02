.PHONY: configs commands aggregate timing analyze plots all clean

UV = uv run python

configs:
	python3 generate_configs.py

# Generate TAMULauncher commands file (one line per simulation).
# Set PROJECT_DIR to the absolute path on the cluster before calling this.
# Example:
#   PROJECT_DIR=/scratch/group/p.cis260910.000/cpsc4520-project make commands
commands:
	python3 generate_commands.py --project-dir "$(PROJECT_DIR)"

aggregate:
	$(UV) aggregate.py

timing:
	$(UV) parse_slurm.py
	$(UV) timing_analysis.py

analyze:
	$(UV) analyze.py

plots:
	$(UV) plots.py

all: aggregate timing analyze plots
	@echo "=== Pipeline complete ==="
	@echo "Results: results/"
	@echo "Plots:   plots/"

clean:
	rm -f configs/*.config
	rm -f jobs.csv
	rm -f logs/*.out logs/*.err
	rm -f sim_*.json
	rm -f timing_*.csv
	@echo "Cleaned generated files"

push_code:
	rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude 'results' --exclude 'plots'  --exclude 'timing' --exclude 'data' cpsc4520-project/ login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/

pull_data:
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/sim_*.json data/
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/timing_sim_*.json timing/
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/timing_*.csv timing/
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/slurm_full*.txt ./
