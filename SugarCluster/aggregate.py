import json
import math
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
DATA = PROJECT / "data"
TIMING = PROJECT / "timing"
JOBS_CSV = PROJECT / "jobs.csv"
OUTPUT = PROJECT / "results" / "run_summary.csv"


def load_jobs():
    df = pd.read_csv(JOBS_CSV)
    df["config_stem"] = df["config_path"].apply(lambda p: Path(p).stem)
    return df


def load_timing():
    files = sorted(TIMING.glob("timing_*.csv"))
    chunks = [pd.read_csv(f) for f in files]
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()


def summarize_json(path):
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        return {}

    initial = records[0]
    final = records[-1]
    final_ts = final["timestep"]
    survived = final_ts >= 999  # allow off-by-one
    pop_values = [r["population"] for r in records]
    sick_values = [r.get("sickAgentsPercentage", 0) for r in records]
    gini_values = [r.get("giniCoefficient", 0) for r in records]
    happy_values = [r.get("meanHappiness", 0) for r in records]
    wealth_values = [r.get("meanWealth", 0) for r in records]
    disease_deaths = [r.get("agentDiseaseDeaths", 0) for r in records]
    starvation_deaths = [r.get("agentStarvationDeaths", 0) for r in records]
    combat_deaths = [r.get("agentCombatDeaths", 0) for r in records]
    aging_deaths = [r.get("agentAgingDeaths", 0) for r in records]
    agent_deaths = [r.get("agentDeaths", 0) for r in records]

    if sick_values:
        peak_idx = max(range(len(sick_values)), key=lambda i: sick_values[i])
    else:
        peak_idx = 0

    return {
        "final_timestep": final_ts,
        "survived": survived,
        "time_to_extinction": final_ts if not survived else math.nan,
        "peak_sick_percentage": max(sick_values) if sick_values else 0,
        "peak_sick_timestep": sick_values[peak_idx] if sick_values else 0,
        "avg_sick_percentage": sum(sick_values) / len(sick_values) if sick_values else 0,
        "final_population": final["population"] if "population" in final else 0,
        "initial_population": initial["population"] if "population" in initial else 0,
        "final_gini": final.get("giniCoefficient", 0),
        "final_happiness": final.get("meanHappiness", 0),
        "final_meanWealth": final.get("meanWealth", 0),
        "final_death_pct": final.get("meanDeathsPercentage", 0),
        "initial_gini": initial.get("giniCoefficient", 0),
        "initial_happiness": initial.get("meanHappiness", 0),
        "initial_meanWealth": initial.get("meanWealth", 0),
        "wealth_gini_change": final.get("giniCoefficient", 0) - initial.get("giniCoefficient", 0),
        "happiness_decline": initial.get("meanHappiness", 0) - final.get("meanHappiness", 0),
        "total_disease_deaths": sum(disease_deaths),
        "total_starvation_deaths": sum(starvation_deaths),
        "total_combat_deaths": sum(combat_deaths),
        "total_aging_deaths": sum(aging_deaths),
        "total_deaths": sum(agent_deaths),
    }


def add_baseline_deltas(df):
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


def main():
    jobs = load_jobs()
    timing = load_timing()

    stem_to_meta = jobs.set_index("config_stem").to_dict(orient="index")

    rows = []
    for json_path in sorted(DATA.glob("*.json")):
        stem = json_path.stem
        meta = stem_to_meta.get(stem)
        if meta is None:
            continue

        summary = summarize_json(json_path)
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
        rows.append(row)

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
    main()
