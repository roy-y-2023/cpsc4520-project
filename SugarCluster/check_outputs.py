#!/usr/bin/env python3
"""Validate that all jobs completed successfully."""

import argparse
import csv
import json
import os
import sys


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def find_extinction_ts(data: list) -> int | None:
    """Return the first timestep where population == 0, or None if never extinct."""
    for entry in data:
        if entry.get("population", 1) == 0:
            return entry["timestep"]
    return None


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
    if last_ts >= expected_timesteps - 1:
        return True, f"OK ({len(data)} entries, last ts={last_ts})"

    # Did not reach target — check for extinction
    extinction_ts = find_extinction_ts(data)
    if extinction_ts is not None:
        pop_last = data[-1].get("population", 0)
        if pop_last == 0:
            return True, f"EXTINCTION at ts={extinction_ts} ({len(data)} entries)"
        else:
            return False, f"INCOMPLETE (last ts={last_ts}, pop={pop_last})"

    return False, f"INCOMPLETE (last ts={last_ts})"


def main():
    parser = argparse.ArgumentParser(description="Validate Sugarscape job outputs")
    parser.add_argument("--manifest", default="jobs.csv", help="Path to jobs.csv manifest")
    parser.add_argument("--logdir", default=".", help="Directory containing log files")
    parser.add_argument("--expected", type=int, default=1000, help="Expected timesteps")
    parser.add_argument("--retry", default="retry.csv", help="Output path for failed jobs retry list")
    parser.add_argument("--summary", default="results_summary.csv", help="Output path for full results summary")
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
    results = []

    for job in jobs:
        job_id = job["job_id"]
        config_path = job["config_path"]
        run_type = job["run_type"]
        framework = job["framework"]

        result = {
            "job_id": job_id,
            "run_type": run_type,
            "framework": framework,
            "config_path": config_path,
        }

        if not os.path.exists(config_path):
            result["status"] = "CONFIG_MISSING"
            failed.append((job_id, config_path, "CONFIG_MISSING"))
            results.append(result)
            continue

        config = load_config(config_path)
        logfile = config.get("logfile", "")
        if not logfile:
            result["status"] = "NO_LOGFILE_IN_CONFIG"
            failed.append((job_id, config_path, "NO_LOGFILE_IN_CONFIG"))
            results.append(result)
            continue

        log_path = os.path.join(args.logdir, logfile)
        success, status = check_log(log_path, args.expected)
        result["status"] = status
        for param in ["diseaseTransmissionChance", "diseaseTagStringLength",
                       "agentImmuneSystemLength", "diseaseSugarMetabolismPenalty"]:
            result[param] = job.get(param, "")

        if success:
            ok.append((job_id, log_path, status))
        else:
            failed.append((job_id, log_path, status))
        results.append(result)

    # Count categories
    ok_count = len(ok)
    extinction_count = sum(1 for r in results if r["status"].startswith("EXTINCTION"))
    failed_count = sum(1 for r in results if r["status"].startswith("INCOMPLETE") or r["status"] in ("MISSING", "CORRUPT_JSON", "EMPTY_LOG", "CONFIG_MISSING", "NO_LOGFILE_IN_CONFIG"))
    # OK includes both "OK" and "EXTINCTION"
    valid_ok = sum(1 for r in results if r["status"].startswith("OK"))
    valid_total = valid_ok + extinction_count

    print(f"\nResults: {valid_ok} COMPLETE  |  {extinction_count} EXTINCTION (valid)  |  {failed_count} FAILED  |  {len(results)} total")

    if failed_count > 0:
        print(f"\nFailed jobs ({failed_count}):")
        with open(args.retry, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["job_id", "config_path", "reason"])
            for job_id, path, reason in failed:
                print(f"  [{job_id}] {path}: {reason}")
                writer.writerow([job_id, path, reason])
        print(f"\nRetry list written to '{args.retry}'")
    else:
        print("All jobs completed successfully!")

    # Write full results summary
    with open(args.summary, "w", newline="") as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    print(f"Full results summary written to '{args.summary}'")

    return 1 if failed_count else 0


if __name__ == "__main__":
    sys.exit(main())
