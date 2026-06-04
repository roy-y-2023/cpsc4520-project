"""Aggregate per-simulation JSON logs and timing data into run_summary.csv."""

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
DATA = PROJECT / "data"
TIMING = PROJECT / "timing"
JOBS_CSV = PROJECT / "jobs.csv"
OUTPUT = PROJECT / "results" / "run_summary.csv"


def load_jobs() -> pd.DataFrame:
    """Load the jobs manifest and add a config_stem column for matching log files."""
    df = pd.read_csv(JOBS_CSV)
    df["config_stem"] = df["config_path"].apply(lambda p: Path(p).stem)
    return df


def _load_timing_jsons(pattern: str) -> "pd.DataFrame":
    """Load all timing JSONs matching *pattern* in the TIMING directory."""
    records = []
    for p in sorted(TIMING.glob(pattern)):
        try:
            with open(p) as f:
                records.append(json.load(f))
        except Exception:
            pass
    return pd.DataFrame(records) if records else pd.DataFrame()


def load_timing() -> "pd.DataFrame":
    """Load per-sim timing from both backends, preferring tamu over slurm."""
    chunks = []

    # SLURM-array per-sim JSONs
    slurm_df = _load_timing_jsons("timing_sim_*_slurm.json")
    if not slurm_df.empty:
        chunks.append(slurm_df)

    # TAMULauncher per-sim JSONs
    tamu_df = _load_timing_jsons("timing_sim_*_tamu.json")
    if not tamu_df.empty:
        chunks.append(tamu_df)

    if not chunks:
        return pd.DataFrame()

    combined = pd.concat(chunks, ignore_index=True)

    # De-duplicate by job_id: tamu > slurm (last wins after sort)
    if "job_id" in combined.columns and "backend" in combined.columns:
        priority = {"slurm": 1, "tamu": 2}
        combined["_pri"] = combined["backend"].map(lambda b: priority.get(b, 0))
        combined = (
            combined.sort_values("_pri")
            .drop_duplicates(subset=["job_id"], keep="last")
            .drop(columns=["_pri"])
        )
    elif "job_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["job_id"], keep="first")

    return combined.reset_index(drop=True)


def summarize_json(path: Path) -> dict:
    """Extract summary metrics from a single Sugarscape JSON log."""
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        return {}

    initial = records[0]
    final = records[-1]
    final_ts = final["timestep"]
    survived = final_ts >= 999  # allow off-by-one

    # Single pass over records — collects all per-timestep series and accumulators
    pop_values: list[float] = []
    sick_values: list[float] = []
    gini_values: list[float] = []
    happy_values: list[float] = []
    wealth_values: list[float] = []
    peak_sick = 0.0
    peak_idx = 0
    total_disease = total_starvation = total_combat = total_aging = total_deaths = 0
    for i, r in enumerate(records):
        pop_values.append(r.get("population", 0))
        gini_values.append(r.get("giniCoefficient", 0))
        happy_values.append(r.get("meanHappiness", 0))
        wealth_values.append(r.get("meanWealth", 0))
        s = r.get("sickAgentsPercentage", 0)
        sick_values.append(s)
        if s > peak_sick:
            peak_sick = s
            peak_idx = i
        total_disease += r.get("agentDiseaseDeaths", 0)
        total_starvation += r.get("agentStarvationDeaths", 0)
        total_combat += r.get("agentCombatDeaths", 0)
        total_aging += r.get("agentAgingDeaths", 0)
        total_deaths += r.get("agentDeaths", 0)

    n = len(sick_values)
    return {
        "final_timestep": final_ts,
        "survived": survived,
        "time_to_extinction": final_ts if not survived else math.nan,
        "peak_sick_percentage": peak_sick,
        "peak_sick_timestep": records[peak_idx].get("timestep", peak_idx) if n else 0,
        "avg_sick_percentage": sum(sick_values) / n if n else 0,
        "final_population": final.get("population", 0),
        "initial_population": initial.get("population", 0),
        "final_gini": final.get("giniCoefficient", 0),
        "final_happiness": final.get("meanHappiness", 0),
        "final_meanWealth": final.get("meanWealth", 0),
        "final_death_pct": final.get("meanDeathsPercentage", 0),
        "initial_gini": initial.get("giniCoefficient", 0),
        "initial_happiness": initial.get("meanHappiness", 0),
        "initial_meanWealth": initial.get("meanWealth", 0),
        "wealth_gini_change": final.get("giniCoefficient", 0) - initial.get("giniCoefficient", 0),
        "happiness_decline": initial.get("meanHappiness", 0) - final.get("meanHappiness", 0),
        "total_disease_deaths": total_disease,
        "total_starvation_deaths": total_starvation,
        "total_combat_deaths": total_combat,
        "total_aging_deaths": total_aging,
        "total_deaths": total_deaths,
    }


def add_baseline_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Attach baseline reference values and compute delta columns."""
    baselines = df[df["run_type"] == "baseline"].copy()
    baseline_cols = {
        "final_population": "baseline_final_population",
        "final_gini": "baseline_final_gini",
        "final_happiness": "baseline_final_happiness",
        "final_meanWealth": "baseline_final_meanWealth",
    }
    baseline_map = {}
    for _, row in baselines.iterrows():
        baseline_map[row["framework"]] = {new: row[old] for old, new in baseline_cols.items()}

    for new_col in baseline_cols.values():
        df[new_col] = df["framework"].map(lambda f: baseline_map.get(f, {}).get(new_col, math.nan))

    for old, new in baseline_cols.items():
        delta_col = "delta" + new[len("baseline"):]
        df[delta_col] = df[old] - df[new]

    return df


def _process_sim(args):
    """Worker used by the thread pool: returns (meta-dict, summary-dict) or None."""
    json_path, meta = args
    summary = summarize_json(json_path)
    if not summary:
        return None
    row = {
        "job_id": meta["job_id"],
        "run_type": meta["run_type"],
        "framework": meta["framework"],
        "transmission": meta.get("diseaseTransmissionChance"),
        "tagLength": meta.get("diseaseTagStringLength"),
        "immunity": meta.get("agentImmuneSystemLength"),
        "penalty": meta.get("diseaseSugarMetabolismPenalty"),
    }
    row.update(summary)
    return row


def main() -> None:
    """Load jobs + timing, aggregate all sim logs, write run_summary.csv."""
    jobs = load_jobs()
    timing = load_timing()

    stem_to_meta = jobs.set_index("config_stem").to_dict(orient="index")

    work = [
        (json_path, stem_to_meta[json_path.stem.removeprefix("sim_")])
        for json_path in sorted(DATA.glob("sim_*.json"))
        if json_path.stem.removeprefix("sim_") in stem_to_meta
    ]

    rows = []
    with ThreadPoolExecutor() as pool:
        for result in pool.map(_process_sim, work):
            if result is not None:
                rows.append(result)

    df = pd.DataFrame(rows)

    timing_cols = ["job_id", "duration_seconds", "status"]
    if not timing.empty and "peak_memory_mb" in timing.columns:
        timing_cols.append("peak_memory_mb")

    if not timing.empty:
        df = df.merge(timing[timing_cols], on="job_id", how="left")

    df = add_baseline_deltas(df)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT}")


if __name__ == "__main__":
    sys.exit(main())
