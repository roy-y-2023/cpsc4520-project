"""Compute grouped statistics and framework comparisons from run_summary.csv."""

import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
RUN_SUMMARY = PROJECT / "results" / "run_summary.csv"
OUT_STATS = PROJECT / "results" / "summary_stats.csv"
OUT_FRAMEWORK = PROJECT / "results" / "framework_comparison.csv"
OUT_PENALTY0 = PROJECT / "results" / "framework_penalty0.csv"
OUT_SURVIVAL = PROJECT / "results" / "survival_by_penalty.csv"


def compute_framework_agg(disease_df: pd.DataFrame, label: str = "") -> pd.DataFrame:
    """Aggregate per-run disease metrics by ethical framework."""
    framework_agg = {
        "survived": "mean",
        "peak_sick_percentage": "mean",
        "avg_sick_percentage": "mean",
        "final_population": "mean",
        "final_gini": "mean",
        "final_happiness": "mean",
        "total_deaths": "mean",
        "delta_final_gini": "mean",
        "delta_final_happiness": "mean",
        "delta_final_meanWealth": "mean",
        "duration_seconds": "mean",
    }
    fw = disease_df.groupby("framework").agg(framework_agg).reset_index()
    fw.rename(columns={"survived": "survival_rate"}, inplace=True)
    return fw


def main() -> None:
    """Read run_summary.csv and write the four analysis CSVs."""
    df = pd.read_csv(RUN_SUMMARY)
    df["survived"] = df["survived"].astype(bool)
    disease = df[df["run_type"] == "disease"].copy()

    # --- 1. summary_stats: group by all knobs + framework ---
    group_cols = ["framework", "transmission", "tagLength", "immunity", "penalty"]
    agg = {
        "survived": "mean",
        "peak_sick_percentage": "mean",
        "avg_sick_percentage": "mean",
        "final_population": "mean",
        "final_gini": "mean",
        "final_happiness": "mean",
        "total_deaths": "mean",
        "duration_seconds": "mean",
        "delta_final_gini": "mean",
        "delta_final_happiness": "mean",
        "job_id": "count",
    }
    stats = disease.groupby(group_cols).agg(agg).reset_index()
    stats.rename(columns={"job_id": "count"}, inplace=True)
    stats.to_csv(OUT_STATS, index=False)
    print(f"Wrote {len(stats)} rows to {OUT_STATS.name}")

    # --- 2. framework_comparison: all penalties ---
    fw = compute_framework_agg(disease)
    baseline = df[df["run_type"] == "baseline"].copy()
    bl_agg = baseline.groupby("framework").agg(
        baseline_population=("final_population", "mean"),
        baseline_gini=("final_gini", "mean"),
        baseline_happiness=("final_happiness", "mean"),
        baseline_wealth=("final_meanWealth", "mean"),
    ).reset_index()
    fw = fw.merge(bl_agg, on="framework", how="left")
    fw.to_csv(OUT_FRAMEWORK, index=False)
    print(f"Wrote {len(fw)} rows to {OUT_FRAMEWORK.name}")

    # --- 3. framework_penalty0: penalty=0 subset ---
    p0 = disease[disease["penalty"] == 0].copy()
    fw0 = compute_framework_agg(p0)
    fw0 = fw0.merge(bl_agg, on="framework", how="left")
    fw0.to_csv(OUT_PENALTY0, index=False)
    print(f"Wrote {len(fw0)} rows to {OUT_PENALTY0.name} (penalty=0 only)")

    # --- 4. survival_by_penalty ---
    survival = disease.groupby(["framework", "penalty"])["survived"].mean().reset_index()
    survival.rename(columns={"survived": "survival_rate"}, inplace=True)
    survival["penalty"] = survival["penalty"].astype(float)
    survival.to_csv(OUT_SURVIVAL, index=False)
    print(f"Wrote {len(survival)} rows to {OUT_SURVIVAL.name}")

    # Quick stats
    print("\nKey findings:")
    print(f"  Overall survival:   {disease['survived'].mean():.1%}")
    for p_val in sorted(disease["penalty"].unique()):
        p_sub = disease[disease["penalty"] == p_val]
        print(f"  Penalty={p_val} survival: {p_sub['survived'].mean():.1%}")
    print(f"  Penalty=0 avg final_gini: {p0['final_gini'].mean():.3f}")
    print(f"  Penalty=0 avg delta_gini: {p0['delta_final_gini'].mean():.3f}")


if __name__ == "__main__":
    sys.exit(main())
