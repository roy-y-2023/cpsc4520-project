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
	@echo "Cleaned generated files (data/ and timing/ preserved)"
