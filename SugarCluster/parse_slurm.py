"""
Parse sacct output from ACES into a structured slurm_timing.csv.

Reads slurm_full.txt (raw `sacct` output), extracts elapsed time, start/end times, 
and compute node for every completed sugarscape-sweep task, and writes results/slurm_timing.csv.
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
INPUT = PROJECT / "slurm_full.txt"
OUTPUT = PROJECT / "results" / "slurm_timing.csv"


def parse_elapsed(elapsed_str: str) -> float:
    """Convert a SLURM elapsed-time string (HH:MM:SS or MM:SS) to seconds."""
    parts = elapsed_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    return 0.0


def main() -> None:
    """Parse slurm_full.txt and write slurm_timing.csv with per-task metrics."""
    rows = []
    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            if "COMPLETED" not in line:
                continue

            left_raw, right_raw = line.split("COMPLETED", 1)
            left_parts = left_raw.split()
            right_parts = right_raw.split()

            if len(left_parts) < 2:
                continue

            job_id_raw = left_parts[0]
            job_name = left_parts[1]

            if job_name != "sugarscape-sweep":
                continue

            if "_" not in job_id_raw or job_id_raw.count("+") > 0:
                continue

            task_id = int(job_id_raw.split("_")[-1])

            elapsed_str = right_parts[0]
            start_str = right_parts[1]
            end_str = right_parts[2]
            node = right_parts[-1].strip()

            rows.append({
                "task_id": task_id,
                "elapsed_seconds": parse_elapsed(elapsed_str),
                "start_time": start_str,
                "end_time": end_str,
                "node": node,
            })

    df = pd.DataFrame(rows)
    df = df.sort_values("task_id").reset_index(drop=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} SLURM tasks to {OUTPUT}")
    print(f"Tasks: {df.task_id.min()} - {df.task_id.max()}")
    print(f"Elapsed range: {df.elapsed_seconds.min():.0f}s - {df.elapsed_seconds.max():.0f}s")
    print(f"Nodes used: {df.node.nunique()}")
    print(f"First start: {df.start_time.min()}")
    print(f"Last end: {df.end_time.max()}")
    print(f"Total wall:n{df.elapsed_seconds.sum():.0f} core-seconds")


if __name__ == "__main__":
    sys.exit(main())
