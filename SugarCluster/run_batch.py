#!/usr/bin/env python3
"""
Run a batch of Sugarscape simulations sequentially within one SLURM task.

Each simulation is delegated to run_sim.py (which handles timing, memory
measurement, and writing timing_sim_<job_id>_slurm.json).
"""

import argparse
import csv
import os
import subprocess
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a batch of Sugarscape simulations sequentially"
    )
    parser.add_argument(
        "--project-dir", required=True,
        help="Root directory containing SugarCluster/ and sugarscape/"
    )
    parser.add_argument(
        "--start-id", type=int, required=True,
        help="First job ID (1-indexed from jobs.csv)"
    )
    parser.add_argument(
        "--end-id", type=int, required=True,
        help="Last job ID (inclusive)"
    )
    args = parser.parse_args()

    cluster_dir = os.path.join(args.project_dir, "SugarCluster")
    manifest = os.path.join(cluster_dir, "jobs.csv")
    run_sim_py = os.path.join(cluster_dir, "run_sim.py")

    if not os.path.exists(manifest):
        print(f"ERROR: Manifest not found: {manifest}", file=sys.stderr)
        return 1
    if not os.path.exists(run_sim_py):
        print(f"ERROR: run_sim.py not found: {run_sim_py}", file=sys.stderr)
        return 1

    with open(manifest, newline="") as f:
        reader = csv.DictReader(f)
        jobs = list(reader)

    total_jobs = len(jobs)
    start_id = max(1, min(args.start_id, total_jobs))
    end_id = min(args.end_id, total_jobs)

    if start_id > total_jobs or start_id > end_id:
        print(f"No jobs in range {start_id}–{end_id} (total={total_jobs})")
        return 0

    errors = []
    batch_start = time.perf_counter()

    for job_id in range(start_id, end_id + 1):
        row = jobs[job_id - 1]
        label = f"[{job_id}/{total_jobs}] {row['run_type']} {row['framework']}"
        print(f"{label} dispatching to run_sim.py")
        sys.stdout.flush()

        result = subprocess.run([
            sys.executable, run_sim_py,
            "--project-dir", args.project_dir,
            "--job-id", str(job_id),
            "--backend", "slurm",
        ],)

        if result.returncode != 0:
            status = f"EXIT_{result.returncode}"
            print(f"{label} FAILED ({status})", file=sys.stderr)
            errors.append({"job_id": job_id, "config_path": row.get("config_path", ""), "reason": status})
        else:
            print(f"{label} OK")

    if errors:
        print(f"\n*** Batch {start_id}–{end_id} completed with {len(errors)} error(s) ***")
        retry_path = os.path.join(cluster_dir, f"retry_{start_id}_{end_id}.csv")
        with open(retry_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["job_id", "config_path", "reason"])
            writer.writeheader()
            writer.writerows(errors)
        print(f"Retry list: {retry_path}")

    batch_end = time.perf_counter()
    batch_duration = batch_end - batch_start
    run_count = end_id - start_id + 1
    avg = batch_duration / run_count if run_count > 0 else 0
    print(
        f"\n*** Batch {start_id}–{end_id} complete. "
        f"Total: {batch_duration:.1f}s  |  Per sim: {avg:.1f}s avg  |  "
        f"{len(errors)} error(s) ***"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
