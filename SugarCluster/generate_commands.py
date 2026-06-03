#!/usr/bin/env python3
"""Generate a TAMULauncher commands file from jobs.csv.

Each line in the output file calls run_sim.py with a single --job-id,
which TAMULauncher will dispatch concurrently across available cores/nodes.

Usage:
    python generate_commands.py
    python generate_commands.py --project-dir /scratch/... --outfile commands.txt
    python generate_commands.py --job-ids 1 5 10  # generate for specific IDs only
"""

import argparse
import csv
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate TAMULauncher commands file from jobs.csv"
    )
    parser.add_argument(
        "--project-dir",
        default="",
        help=(
            "Absolute path to the project root (containing SugarCluster/ and sugarscape/). "
            "Defaults to the directory two levels above this script."
        ),
    )
    parser.add_argument(
        "--manifest",
        default="jobs.csv",
        help="Path to jobs.csv (default: jobs.csv relative to this script)",
    )
    parser.add_argument(
        "--outfile",
        default="commands.txt",
        help="Output commands file path (default: commands.txt)",
    )
    parser.add_argument(
        "--job-ids",
        nargs="+",
        type=int,
        metavar="ID",
        help="Only emit commands for these specific job IDs (default: all jobs)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Resolve project_dir: default = parent of SugarCluster/
    project_dir = args.project_dir or os.path.dirname(script_dir)

    # Resolve manifest path relative to script_dir if not absolute
    manifest_path = (
        args.manifest
        if os.path.isabs(args.manifest)
        else os.path.join(script_dir, args.manifest)
    )

    if not os.path.exists(manifest_path):
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, newline="") as f:
        reader = csv.DictReader(f)
        jobs = list(reader)

    if not jobs:
        print("ERROR: jobs.csv is empty", file=sys.stderr)
        return 1

    # Filter to requested job IDs if specified
    selected_ids = set(args.job_ids) if args.job_ids else None

    run_sim = os.path.join(script_dir, "run_sim.py")

    lines = []
    for row in jobs:
        job_id = int(row["job_id"])
        if selected_ids and job_id not in selected_ids:
            continue
        # Use forward slashes for Linux cluster compatibility
        project_dir_fwd = project_dir.replace("\\", "/")
        run_sim_fwd = run_sim.replace("\\", "/")
        # Use python3 from PATH (venv activated by submit_tamulauncher.slurm)
        cmd = (
            f"python3 {run_sim_fwd}"
            f" --project-dir {project_dir_fwd}"
            f" --job-id {job_id}"
            f" --backend tamu"
        )
        lines.append(cmd)

    outfile = (
        args.outfile
        if os.path.isabs(args.outfile)
        else os.path.join(script_dir, args.outfile)
    )
    with open(outfile, "w", newline="\n") as f:  # LF line endings for Linux
        f.write("\n".join(lines) + "\n")

    print(f"Generated {len(lines)} commands → {outfile}")
    print("Submit with: make submit-tamu ACCOUNT=<account>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
