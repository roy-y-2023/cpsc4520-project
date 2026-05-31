#!/usr/bin/env python3
"""Validate that all jobs completed successfully.

Reads the jobs manifest and checks each expected logfile:
- Exists
- Is valid JSON
- Reached timestep 1000

Usage:
    python check_outputs.py --manifest jobs.csv [--logdir .]
"""

import argparse
import csv
import json
import os
import sys


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def check_log(log_path: str, expected_timesteps: int) -> tuple[bool, str]:
    if not os.path.exists(log_path):
        return False, "MISSING"
    try:
        with open(log_path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return False, "CORRUPT_JSON"

    if not isinstance(data, list) or len(data) == 0:
        return False, "EMPTY_LOG"

    last_ts = data[-1].get("timestep", -1)
    if last_ts < expected_timesteps - 1:
        return False, f"INCOMPLETE (last ts={last_ts}, expected >= {expected_timesteps - 1})"

    return True, f"OK ({len(data)} entries, last ts={last_ts})"


def main():
    parser = argparse.ArgumentParser(description="Validate Sugarscape job outputs")
    parser.add_argument("--manifest", default="jobs.csv", help="Path to jobs.csv manifest")
    parser.add_argument("--logdir", default=".", help="Directory containing log files")
    parser.add_argument("--expected", type=int, default=1000, help="Expected timesteps")
    parser.add_argument("--retry", default="retry.csv", help="Output path for failed jobs retry list")
    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"ERROR: '{args.manifest}' not found")
        return 1

    with open(args.manifest, newline="") as f:
        reader = csv.DictReader(f)
        jobs = list(reader)

    print(f"Checking {len(jobs)} jobs...")
    ok = []
    failed = []

    for job in jobs:
        job_id = job["job_id"]
        config_path = job["config_path"]

        if not os.path.exists(config_path):
            failed.append((job_id, config_path, "CONFIG_MISSING"))
            continue

        config = load_config(config_path)
        logfile = config.get("logfile", "")
        if not logfile:
            failed.append((job_id, config_path, "NO_LOGFILE_IN_CONFIG"))
            continue

        log_path = os.path.join(args.logdir, logfile)
        success, status = check_log(log_path, args.expected)
        if success:
            ok.append((job_id, log_path, status))
        else:
            failed.append((job_id, log_path, status))

    print(f"\nResults: {len(ok)} OK, {len(failed)} FAILED")

    if failed:
        print(f"\nFailed jobs ({len(failed)}):")
        with open(args.retry, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["job_id", "config_path", "reason"])
            for job_id, path, reason in failed:
                print(f"  [{job_id}] {path}: {reason}")
                writer.writerow([job_id, path, reason])
        print(f"\nRetry list written to '{args.retry}'")
    else:
        print("All jobs completed successfully!")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
