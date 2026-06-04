#!/usr/bin/env python3
"""Generate Sugarscape simulation configs from a TOML sweep specification."""

import argparse
import csv
import json
import os
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]  # Python < 3.11
from itertools import product


def load_sweep(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        return tomllib.load(f)


def make_baseline_config(sim: dict, framework: str, outdir: str) -> tuple[dict, str]:
    """Return a baseline config dict and its filename."""
    cfg = {
        "agentDecisionModels": [framework],
        "timesteps": sim["timesteps"],
        "seed": sim["seed"],
        "headlessMode": sim["headless_mode"],
        "logfileFormat": sim["logfile_format"],
        "logfile": f"sim_{framework}_baseline.json",
    }
    filename = f"{framework}_baseline.config"
    return cfg, filename


def make_disease_config(
    sim: dict,
    disease: dict,
    framework: str,
    params: tuple[float, int, int, int],
    outdir: str,
) -> tuple[dict, str]:
    """Return a disease-sweep config dict and its filename."""
    trans, tag, imm, pen = params
    name = f"{framework}_t{trans}_tag{tag}_imm{imm}_pen{pen}"
    cfg = {
        "agentDecisionModels": [framework],
        "timesteps": sim["timesteps"],
        "seed": sim["seed"],
        "headlessMode": sim["headless_mode"],
        "logfileFormat": sim["logfile_format"],
        "logfile": f"sim_{name}.json",
        "startingDiseases": disease["startingDiseases"],
        "startingDiseasesPerAgent": disease["startingDiseasesPerAgent"],
        "diseaseTransmissionChance": [trans, trans],
        "diseaseTagStringLength": [tag, tag],
        "agentImmuneSystemLength": imm,
        "diseaseSugarMetabolismPenalty": [pen, pen],
        "diseaseSpiceMetabolismPenalty": [pen, pen],
    }
    filename = f"{name}.config"
    return cfg, filename


def generate(sweep: dict, outdir: str, selected_models: list[str] | None = None, limit: int | None = None) -> list[dict]:
    os.makedirs(outdir, exist_ok=True)

    sim = sweep["simulation"]
    disease = sweep["disease"]
    sweep_params = disease["sweep"]
    frameworks = sweep["sweep"]["models"]["frameworks"]
    baseline_enabled = sweep["baseline"]["enabled"]

    if selected_models:
        frameworks = [f for f in frameworks if f in selected_models]
        if not frameworks:
            raise ValueError(f"No matching models found in: {selected_models}")

    # Cartesian product of all disease sweep parameters
    param_names = [
        "diseaseTransmissionChance",
        "diseaseTagStringLength",
        "agentImmuneSystemLength",
        "diseaseSugarMetabolismPenalty",
    ]
    param_values = [sweep_params[k] for k in param_names]
    param_combos = list(product(*param_values))

    jobs = []
    job_id = 0

    for fw in frameworks:
        # Baseline run
        if baseline_enabled:
            job_id += 1
            cfg, filename = make_baseline_config(sim, fw, outdir)
            path = os.path.join(outdir, filename)
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            jobs.append({
                "job_id": job_id,
                "run_type": "baseline",
                "framework": fw,
                "config_path": path.replace(os.sep, "/"),
                **{k: "" for k in param_names},
            })
            if limit and len(jobs) >= limit:
                return jobs

        # Disease sweep runs
        for params in param_combos:
            job_id += 1
            cfg, filename = make_disease_config(sim, disease, fw, params, outdir)
            path = os.path.join(outdir, filename)
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            jobs.append({
                "job_id": job_id,
                "run_type": "disease",
                "framework": fw,
                "config_path": path.replace(os.sep, "/"),
                **dict(zip(param_names, params)),
            })
            if limit and len(jobs) >= limit:
                return jobs

    return jobs


def write_manifest(jobs: list[dict], manifest_path: str) -> None:
    if not jobs:
        return
    fieldnames = list(jobs[0].keys())
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sugarscape sweep configs")
    parser.add_argument("--sweep", default="sweep.toml", help="Path to sweep TOML file")
    parser.add_argument("--outdir", default="configs", help="Output directory for .config files")
    parser.add_argument("--manifest", default="jobs.csv", help="Output path for job manifest CSV")
    parser.add_argument("--models", nargs="+", help="Limit to specific ethical frameworks")
    parser.add_argument("--limit", type=int, help="Limit total number of jobs generated (for dry-runs)")
    args = parser.parse_args()

    sweep = load_sweep(args.sweep)
    jobs = generate(sweep, args.outdir, selected_models=args.models, limit=args.limit)
    write_manifest(jobs, args.manifest)

    print(f"Generated {len(jobs)} configs in '{args.outdir}'")
    print(f"Manifest written to '{args.manifest}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
