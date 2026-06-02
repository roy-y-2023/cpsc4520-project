"""Timing analysis — supports both SLURM job-array and TAMULauncher modes.

Outputs (written only when the relevant data exists):
  results/timing_summary_slurm.csv          — SLURM job-array summary stats
  results/timing_summary_tamulauncher.csv   — TAMULauncher summary stats
  results/cumulative_real_slurm.csv         — actual per-task completion curve (SLURM)
  results/cumulative_real_tamulauncher.csv  — actual per-sim completion curve (TAMULauncher)
  results/cumulative_theoretical_slurm.csv  — theoretical perfect-parallelism (SLURM)
  results/cumulative_theoretical_tamulauncher.csv
  results/node_distribution.csv            — SLURM node load (SLURM only)
  results/timing_summary.csv               — backward-compat (SLURM if available, else TL)
  results/cumulative_real.csv              — backward-compat
  results/cumulative_theoretical.csv       — backward-compat
"""

import json
import re
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent
SLURM_CSV = PROJECT / "results" / "slurm_timing.csv"
TIMING_DIR = PROJECT / "timing"
OUT_DIR = PROJECT / "results"


# ── Data loaders ─────────────────────────────────────────────────────────────

def load_slurm_timing():
    """Load SLURM job-array metadata (from parse_slurm.py → slurm_timing.csv)."""
    if not SLURM_CSV.exists():
        return None
    df = pd.read_csv(SLURM_CSV)
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    return df


def load_sim_timing_legacy():
    """Load per-sim timing from timing_*.csv (written by run_batch.py, SLURM mode)."""
    files = sorted(TIMING_DIR.glob("timing_*.csv"))
    if not files:
        return None
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def load_sim_timing_tamulauncher():
    """Load per-sim timing from timing_sim_*.json (written by run_sim.py, TAMULauncher)."""
    records = []
    for p in sorted(TIMING_DIR.glob("timing_sim_*.json")):
        try:
            records.append(json.loads(p.read_text()))
        except Exception:
            pass
    if not records:
        return None
    df = pd.DataFrame(records)
    for col in ("start_time", "end_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def get_tamulauncher_job_elapsed():
    """Parse the elapsed seconds of the COMPLETED TAMULauncher job from slurm_tamulauncher_full.txt."""
    path = PROJECT / "slurm_tamulauncher_full.txt"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "COMPLETED" in line and "sugarscape-tamulaun" in line:
                parts = line.split("COMPLETED", 1)[1].split()
                if parts:
                    elapsed_str = parts[0]
                    t_parts = elapsed_str.split(":")
                    if len(t_parts) == 3:
                        h, m, s = t_parts
                        return int(h) * 3600 + int(m) * 60 + int(s)
                    elif len(t_parts) == 2:
                        m, s = t_parts
                        return int(m) * 60 + int(s)
    return None


def load_any_sim_timing():
    """Union of both per-sim timing sources — used by aggregate.py and plots.py."""
    chunks = []
    legacy = load_sim_timing_legacy()
    tamu = load_sim_timing_tamulauncher()
    if legacy is not None:
        chunks.append(legacy)
    if tamu is not None:
        chunks.append(tamu)
    if not chunks:
        return pd.DataFrame()
    combined = pd.concat(chunks, ignore_index=True)
    if "job_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["job_id"], keep="first")
    return combined


# ── SLURM job-array mode ──────────────────────────────────────────────────────

def get_sims_per_job():
    submit_slurm = PROJECT / "submit.slurm"
    if submit_slurm.exists():
        content = submit_slurm.read_text(encoding="utf-8")
        m = re.search(r'SIMS_PER_JOB="\$\{SIMS_PER_JOB:-(\d+)\}"', content)
        if m:
            return int(m.group(1))
    return 30


def compute_batch_durations(sim_df):
    sims_per_job = get_sims_per_job()
    sim_df = sim_df.copy()
    sim_df["batch_id"] = ((sim_df["job_id"] - 1) // sims_per_job) + 1
    return sim_df.groupby("batch_id").agg(
        sim_count=("job_id", "count"),
        total_sim_seconds=("duration_seconds", "sum"),
        max_sim=("duration_seconds", "max"),
    ).reset_index()


def compute_cumulative_real_slurm(slurm_df):
    """Cumulative sims complete vs wall time, from SLURM task end-times."""
    sims_per_job = get_sims_per_job()
    df = slurm_df.sort_values("end_time").reset_index(drop=True)
    start = slurm_df["start_time"].min()
    df["t_seconds"] = (df["end_time"] - start).dt.total_seconds()
    df["cum_sims"] = (df.index + 1) * sims_per_job
    
    # Prepend t_seconds=0, cum_sims=0 to represent the origin / job startup
    zero_row = pd.DataFrame([{"t_seconds": 0.0, "cum_sims": 0}])
    df_result = pd.concat([zero_row, df[["t_seconds", "cum_sims"]]], ignore_index=True)
    return df_result


def compute_cumulative_theoretical_slurm(sim_df):
    """Theoretical: batch total time sorted ascending (sequential perfect dispatch)."""
    batches = compute_batch_durations(sim_df)
    batches = batches.sort_values("total_sim_seconds")
    batches["cum_sims"] = batches["sim_count"].cumsum()
    return batches[["total_sim_seconds", "cum_sims"]].rename(
        columns={"total_sim_seconds": "t_seconds"}
    )


def analyze_slurm(slurm_df, sim_df):
    first_start = slurm_df["start_time"].min()
    last_end = slurm_df["end_time"].max()
    total_wall = (last_end - first_start).total_seconds()
    total_core = slurm_df["elapsed_seconds"].sum()
    total_sim = sim_df["duration_seconds"].sum()
    num_nodes = slurm_df["node"].nunique()
    num_tasks = len(slurm_df)

    batch = compute_batch_durations(sim_df)
    slurm_rename = slurm_df[["task_id", "elapsed_seconds"]].rename(
        columns={"task_id": "batch_id", "elapsed_seconds": "slurm_elapsed"}
    )
    batch = batch.merge(slurm_rename, on="batch_id", how="left")
    batch["overhead_seconds"] = batch["slurm_elapsed"] - batch["total_sim_seconds"]
    batch["overhead_pct"] = batch["overhead_seconds"] / batch["slurm_elapsed"] * 100

    real_cum = compute_cumulative_real_slurm(slurm_df)
    theo_cum = compute_cumulative_theoretical_slurm(sim_df)

    tasks_per_node = slurm_df.groupby("node").size().reset_index(name="count")
    node_counts = (
        tasks_per_node.groupby("count").size()
        .reset_index(name="num_nodes")
        .rename(columns={"count": "tasks_per_node"})
        .sort_values("tasks_per_node")
    )

    summary = {
        "mode": "slurm_array",
        "total_sims": len(sim_df),
        "total_slurm_tasks": num_tasks,
        "num_nodes": num_nodes,
        "sims_per_task": get_sims_per_job(),
        "total_wall_seconds": total_wall,
        "total_wall_minutes": total_wall / 60,
        "total_core_seconds": total_core,
        "total_sim_seconds": total_sim,
        "avg_slurm_elapsed": slurm_df["elapsed_seconds"].mean(),
        "min_slurm_elapsed": slurm_df["elapsed_seconds"].min(),
        "max_slurm_elapsed": slurm_df["elapsed_seconds"].max(),
        "avg_sim_duration": sim_df["duration_seconds"].mean(),
        "sims_per_wall_hour": len(sim_df) / (total_wall / 3600),
        "avg_batch_overhead_pct": batch["overhead_pct"].mean(),
        "avg_batch_overhead_s": batch["overhead_seconds"].mean(),
        "parallelism_factor": total_sim / total_wall,
        "total_duration_hhmmss": f"{int(total_wall // 60)}:{int(total_wall % 60):02d}",
    }
    return summary, real_cum, theo_cum, node_counts


# ── TAMULauncher mode ─────────────────────────────────────────────────────────

def compute_cumulative_real_tamulauncher(sim_df):
    """Cumulative sims complete vs wall time, from per-sim end_time timestamps."""
    df = sim_df.dropna(subset=["end_time"]).copy()
    df = df.sort_values("end_time").reset_index(drop=True)
    
    elapsed = get_tamulauncher_job_elapsed()
    if elapsed is not None:
        max_end = df["end_time"].max()
        df["t_seconds"] = (df["end_time"] - max_end).dt.total_seconds() + elapsed
        print(f"[timing_analysis] Aligned TAMULauncher timeline using job elapsed duration of {elapsed}s.")
    else:
        start = sim_df["start_time"].dropna().min()
        df["t_seconds"] = (df["end_time"] - start).dt.total_seconds()
        print(f"[timing_analysis] WARNING: slurm_tamulauncher_full.txt not found. Using first simulation start time.")
        
    df["cum_sims"] = range(1, len(df) + 1)
    
    # Prepend t_seconds=0, cum_sims=0 to represent the origin / job startup
    zero_row = pd.DataFrame([{"t_seconds": 0.0, "cum_sims": 0}])
    df_result = pd.concat([zero_row, df[["t_seconds", "cum_sims"]]], ignore_index=True)
    return df_result


def compute_cumulative_theoretical_tamulauncher(sim_df):
    """Theoretical: infinite-parallelism — all sims start at t=0, complete at duration."""
    df = sim_df[["duration_seconds"]].dropna().copy()
    df = df.sort_values("duration_seconds").reset_index(drop=True)
    df["cum_sims"] = range(1, len(df) + 1)
    return df[["duration_seconds", "cum_sims"]].rename(
        columns={"duration_seconds": "t_seconds"}
    )


def analyze_tamulauncher(sim_df):
    has_timestamps = (
        "start_time" in sim_df.columns and sim_df["start_time"].notna().any()
    )
    elapsed = get_tamulauncher_job_elapsed()
    
    if elapsed is not None:
        total_wall = float(elapsed)
    elif has_timestamps:
        first_start = sim_df["start_time"].min()
        last_end = sim_df["end_time"].dropna().max()
        total_wall = (last_end - first_start).total_seconds()
    else:
        # Fallback: use sum of durations / estimated parallelism
        total_wall = sim_df["duration_seconds"].max()

    total_sim = sim_df["duration_seconds"].sum()

    real_cum = (
        compute_cumulative_real_tamulauncher(sim_df)
        if has_timestamps
        else compute_cumulative_theoretical_tamulauncher(sim_df)
    )
    theo_cum = compute_cumulative_theoretical_tamulauncher(sim_df)

    summary = {
        "mode": "tamulauncher",
        "total_sims": len(sim_df),
        "total_slurm_tasks": 1,
        "num_nodes": None,
        "sims_per_task": None,
        "total_wall_seconds": total_wall,
        "total_wall_minutes": total_wall / 60,
        "total_core_seconds": total_sim,  # each sim = 1 core
        "total_sim_seconds": total_sim,
        "avg_slurm_elapsed": None,
        "min_slurm_elapsed": None,
        "max_slurm_elapsed": None,
        "avg_sim_duration": sim_df["duration_seconds"].mean(),
        "sims_per_wall_hour": len(sim_df) / (total_wall / 3600) if total_wall > 0 else None,
        "avg_batch_overhead_pct": None,
        "avg_batch_overhead_s": None,
        "parallelism_factor": total_sim / total_wall if total_wall > 0 else None,
        "total_duration_hhmmss": f"{int(total_wall // 60)}:{int(total_wall % 60):02d}",
    }
    return summary, real_cum, theo_cum


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    slurm_df = load_slurm_timing()
    sim_legacy = load_sim_timing_legacy()
    sim_tamu = load_sim_timing_tamulauncher()

    slurm_done = False
    tamu_done = False
    primary_real = None
    primary_theo = None

    # ── SLURM job-array analysis ──────────────────────────────────
    if slurm_df is not None and sim_legacy is not None:
        print("[timing_analysis] SLURM job-array mode: found slurm_timing.csv + timing_*.csv")
        summary, real_cum, theo_cum, node_counts = analyze_slurm(slurm_df, sim_legacy)

        pd.DataFrame([summary]).to_csv(OUT_DIR / "timing_summary_slurm.csv", index=False)
        real_cum.to_csv(OUT_DIR / "cumulative_real_slurm.csv", index=False)
        theo_cum.to_csv(OUT_DIR / "cumulative_theoretical_slurm.csv", index=False)
        node_counts.to_csv(OUT_DIR / "node_distribution.csv", index=False)

        print("=== SLURM Job-Array Timing Summary ===")
        _print_summary(summary, slurm_df)

        primary_real = real_cum
        primary_theo = theo_cum
        slurm_done = True
    else:
        if slurm_df is None:
            print("[timing_analysis] SLURM mode skipped: results/slurm_timing.csv not found")
        if sim_legacy is None:
            print("[timing_analysis] SLURM mode skipped: no timing/timing_*.csv files")

    # ── TAMULauncher analysis ─────────────────────────────────────
    if sim_tamu is not None:
        print("[timing_analysis] TAMULauncher mode: found timing_sim_*.json")
        summary, real_cum, theo_cum = analyze_tamulauncher(sim_tamu)

        pd.DataFrame([summary]).to_csv(OUT_DIR / "timing_summary_tamulauncher.csv", index=False)
        real_cum.to_csv(OUT_DIR / "cumulative_real_tamulauncher.csv", index=False)
        theo_cum.to_csv(OUT_DIR / "cumulative_theoretical_tamulauncher.csv", index=False)

        print("=== TAMULauncher Timing Summary ===")
        _print_summary(summary)

        if primary_real is None:
            primary_real = real_cum
            primary_theo = theo_cum
        tamu_done = True
    else:
        print("[timing_analysis] TAMULauncher mode skipped: no timing_sim_*.json files")

    # ── Backward-compat files (used by plots.py) ──────────────────
    if primary_real is not None:
        primary_real.to_csv(OUT_DIR / "cumulative_real.csv", index=False)
        primary_theo.to_csv(OUT_DIR / "cumulative_theoretical.csv", index=False)

    # timing_summary.csv: prefer SLURM summary if available
    primary_summary_path = (
        OUT_DIR / "timing_summary_slurm.csv" if slurm_done
        else OUT_DIR / "timing_summary_tamulauncher.csv" if tamu_done
        else None
    )
    if primary_summary_path and primary_summary_path.exists():
        import shutil
        shutil.copy(primary_summary_path, OUT_DIR / "timing_summary.csv")

    if not slurm_done and not tamu_done:
        print("ERROR: No timing data found in either timing_*.csv or timing_sim_*.json. "
              "Run parse_slurm.py first (SLURM mode) or check TAMULauncher output.")


def _print_summary(summary: dict, slurm_df=None):
    tw = summary["total_wall_seconds"]
    ts = summary["total_sim_seconds"]
    print(f"  Total sims:         {summary['total_sims']}")
    print(f"  SLURM tasks:        {summary['total_slurm_tasks']}")
    nodes = summary.get("num_nodes")
    print(f"  ACES nodes used:    {nodes if nodes is not None else 'N/A (TAMULauncher)'}")
    print(f"  Total wall time:    {tw:.0f}s ({tw/60:.1f} min)")
    print(f"  Total core-seconds: {summary['total_core_seconds']:.0f}s")
    print(f"  Total sim-seconds:  {ts:.0f}s ({ts/60:.1f} min)")
    tph = summary.get("sims_per_wall_hour")
    if tph:
        print(f"  Throughput:         {tph:.0f} sims/wall-hour")
    print(f"  Avg sim duration:   {summary['avg_sim_duration']:.1f}s")
    if slurm_df is not None and summary.get("avg_slurm_elapsed"):
        print(f"  Avg task elapsed:   {summary['avg_slurm_elapsed']:.1f}s")
        print(f"  Avg batch overhead: {summary['avg_batch_overhead_s']:.1f}s "
              f"({summary['avg_batch_overhead_pct']:.1f}%)")
    pf = summary.get("parallelism_factor")
    if pf:
        print(f"  Parallelism factor: {pf:.1f}x")
        print(f"  Serial equivalent:  {ts:.0f}s on 1 core vs {tw:.0f}s wall")


if __name__ == "__main__":
    main()
