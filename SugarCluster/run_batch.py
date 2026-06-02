#!/usr/bin/env python3
"""Run a batch of Sugarscape simulations sequentially within one SLURM task.

Usage:
    python run_batch.py --project-dir /path/to/project --start-id 1 --end-id 10
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
    sugarscape_dir = os.path.join(args.project_dir, "sugarscape")
    manifest = os.path.join(cluster_dir, "jobs.csv")
    sugarscape_py = os.path.join(sugarscape_dir, "sugarscape.py")

    if not os.path.exists(manifest):
        print(f"ERROR: Manifest not found: {manifest}", file=sys.stderr)
        return 1
    if not os.path.exists(sugarscape_py):
        print(f"ERROR: sugarscape.py not found: {sugarscape_py}", file=sys.stderr)
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

    cwd = os.getcwd()
    param_names = ["diseaseTransmissionChance", "diseaseTagStringLength",
                   "agentImmuneSystemLength", "diseaseSugarMetabolismPenalty"]
    errors = []
    timing = []
    batch_start = time.perf_counter()

    for job_id in range(start_id, end_id + 1):
        row = jobs[job_id - 1]
        config_rel = row["config_path"]
        config_path = os.path.join(cluster_dir, config_rel)
        label = f"[{job_id}/{total_jobs}] {row['run_type']} {row['framework']}"

        if not os.path.exists(config_path):
            msg = f"{label} SKIPPED — config not found: {config_path}"
            print(msg, file=sys.stderr)
            errors.append({"job_id": job_id, "config_path": config_rel, "reason": "CONFIG_MISSING"})
            continue

        print(f"{label} running {config_rel}")
        sys.stdout.flush()

        sim_start = time.perf_counter()
        p = subprocess.Popen(
            [sys.executable, sugarscape_py, "--conf", str(config_path)],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        peak_rss_kb = 0
        while True:
            ret = p.poll()
            try:
                with open(f"/proc/{p.pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1])
                            if rss > peak_rss_kb:
                                peak_rss_kb = rss
                            break
            except Exception:
                pass
            if ret is not None:
                break
            time.sleep(0.05)

        stdout, stderr = p.communicate()
        sim_end = time.perf_counter()
        duration = sim_end - sim_start
        peak_memory_mb = round(peak_rss_kb / 1024.0, 2)

        class CompletedProcess:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        result = CompletedProcess(p.returncode, stdout, stderr)

        if result.returncode != 0:
            status = f"EXIT_{result.returncode}"
            msg = (
                f"{label} FAILED ({status}) in {duration:.1f}s (Peak Mem: {peak_memory_mb:.2f}MB)\n"
                f"  stdout: {result.stdout.strip()[:200]}\n"
                f"  stderr: {result.stderr.strip()[:200]}"
            )
            print(msg, file=sys.stderr)
            errors.append({"job_id": job_id, "config_path": config_rel, "reason": status})
        else:
            status = "OK"
            print(f"{label} OK ({duration:.1f}s, Peak Mem: {peak_memory_mb:.2f}MB)")

        timing.append({
            "job_id": job_id,
            "run_type": row["run_type"],
            "framework": row["framework"],
            **{p: row.get(p, "") for p in param_names},
            "duration_seconds": round(duration, 1),
            "peak_memory_mb": peak_memory_mb,
            "status": status,
        })

    # Write errors
    if errors:
        print(f"\n*** Batch {start_id}–{end_id} completed with {len(errors)} error(s) ***")
        retry_path = os.path.join(cluster_dir, f"retry_{start_id}_{end_id}.csv")
        with open(retry_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["job_id", "config_path", "reason"])
            writer.writeheader()
            writer.writerows(errors)
        print(f"Retry list: {retry_path}")

    # Write timing
    timing_path = os.path.join(cluster_dir, f"timing_{start_id}_{end_id}.csv")
    if timing:
        fieldnames = list(timing[0].keys())
        with open(timing_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(timing)
        print(f"Timing written: {timing_path}")

    batch_end = time.perf_counter()
    batch_duration = batch_end - batch_start
    run_count = end_id - start_id + 1
    avg = batch_duration / run_count if run_count > 0 else 0
    print(f"\n*** Batch {start_id}–{end_id} complete. "
          f"Total: {batch_duration:.1f}s  |  Per sim: {avg:.1f}s avg  |  "
          f"{len(errors)} error(s) ***")

    return 0


if __name__ == "__main__":
    sys.exit(main())
