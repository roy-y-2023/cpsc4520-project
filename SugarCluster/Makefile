.PHONY: configs aggregate timing analyze plots all clean

UV = uv run python

configs:
	$(UV) generate_configs.py

aggregate:
	$(UV) aggregate.py

timing:
	$(UV) parse_slurm.py
	$(UV) timing_analysis.py

analyze:
	$(UV) analyze.py

plots:
	$(UV) plots.py

all: configs aggregate timing analyze plots
	@echo "=== Pipeline complete ==="
	@echo "Results: results/"
	@echo "Plots:   plots/"

clean:
	rm -rf results/*
	rm -rf plots/*
	rm -f configs/*.config
	rm -f jobs.csv
	rm logs/*.out logs/*.err
	rm *.json
	rm timing_*.csv
	@echo "Cleaned generated files"

push_code:
	rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git'   cpsc4520-project/   login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/

pull_data:
	rsync -avz login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/*.json   SugarCluster/data/
	rsync -avz login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/timing_*.csv   SugarCluster/timing/
	rsync -avz login.aces.hprc.tamu.edu:/scratch/group/p.cis260910.000/cpsc4520-project/SugarCluster/slurm_full.txt   SugarCluster/
