.PHONY: configs commands aggregate timing analyze plots all clean \
        submit-slurm submit-tamu

# Default to uv run python if uv is installed, otherwise fallback to python3
ifeq (, $(shell command -v uv 2>/dev/null))
  UV ?= python3
else
  UV ?= uv run python
endif

# ACCOUNT: SLURM account number, required for submit-slurm and submit-tamu
# PROJECT_DIR: The absolute path of where the repo is cloned/extracted to
# Example:
#   make submit-slurm ACCOUNT=155415875505 PROJECT_DIR=/scratch/.../cpsc4520-project
#   make submit-tamu  ACCOUNT=155415875505 PROJECT_DIR=/scratch/.../cpsc4520-project
ACCOUNT ?= 155415875505
PROJECT_DIR ?= /scratch/group/p.cis260910.000/cpsc4520-project

configs:
	python3 generate_configs.py

commands: configs
	python3 generate_commands.py --project-dir "$(PROJECT_DIR)"

check-outputs:
	python3 check_outputs.py

aggregate:
	$(UV) aggregate.py

timing:
	$(UV) timing_analysis.py

analyze:
	$(UV) analyze.py

plots:
	$(UV) plots.py

all: configs aggregate timing analyze plots
	@echo "=== Pipeline complete ==="
	@echo "Results: results/"
	@echo "Plots:   plots/"

setup-server:
	bash setup_aces.sh
	python3 --version

submit-slurm: configs
ifndef ACCOUNT
	$(error ACCOUNT is required. Usage: make submit-slurm ACCOUNT=<account> [PROJECT_DIR=...])
endif
	@date -u +"%Y-%m-%dT%H:%M:%SZ" > submit_time_slurm.txt
	@echo "Submission time recorded: $$(cat submit_time_slurm.txt)"
	PROJECT_DIR="$(PROJECT_DIR)" sbatch -A $(ACCOUNT) submit.slurm

submit-tamu: commands
ifndef ACCOUNT
	$(error ACCOUNT is required. Usage: make submit-tamu ACCOUNT=<account> [PROJECT_DIR=...])
endif
	tamulauncher --remove-logs $(PROJECT_DIR)/SugarCluster/commands.txt
	@date -u +"%Y-%m-%dT%H:%M:%SZ" > submit_time_tamu.txt
	@echo "Submission time recorded: $$(cat submit_time_tamu.txt)"
	PROJECT_DIR="$(PROJECT_DIR)" sbatch -A $(ACCOUNT) submit_tamulauncher.slurm

clean:
	rm -f configs/*.config
	rm -f jobs.csv commands.txt
	rm -f logs/*.out logs/*.err
	rm -f timing/*.json timing/*.csv
	rm -f sim_*.json timing_*.json submit_time_*.txt slurm_*full.txt
	rm -f results_summary.csv retry.csv
	@echo "Cleaned generated files"

push-code:
	rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude 'results' --exclude 'plots'  --exclude 'timing' --exclude 'data' --exclude 'configs' --exclude 'jobs.csv' cpsc4520-project/ login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/

pull-data:
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:$(PROJECT_DIR)/SugarCluster/sim_*.json data/ & \
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:$(PROJECT_DIR)/SugarCluster/timing_sim_*.json timing/ & \
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:$(PROJECT_DIR)/SugarCluster/submit_time_*.txt ./ & \
	rsync -avz --ignore-missing-args login.aces.hprc.tamu.edu:$(PROJECT_DIR)/SugarCluster/slurm_*full.txt ./ & \
	wait
