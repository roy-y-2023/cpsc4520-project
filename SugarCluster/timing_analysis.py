"""Compute timing and throughput metrics from per-sim JSON timing files."""

import json
import shutil
from pathlib import Path
import datetime

import pandas as pd

PROJECT = Path(__file__).resolve().parent
TIMING_DIR = PROJECT / "timing"
OUT_DIR = PROJECT / "results"


# Data loaders

def load_submit_time(backend: str) -> "datetime.datetime | None":
    """Read the sbatch submission timestamp from submit_time_<backend>.txt."""
    path = PROJECT / f"submit_time_{backend}.txt"
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        # Format written by `date -u +"%Y-%m-%dT%H:%M:%SZ"`
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as e:
        print(f"WARNING: Could not parse {path}: {e}")
        return None


def load_sim_timing(backend: str) -> "pd.DataFrame | None":
    """Load per-sim timing JSON files for the given backend ('slurm' or 'tamu')."""
    pattern = f"timing_sim_*_{backend}.json"
    records = []
    for p in sorted(TIMING_DIR.glob(pattern)):
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


# Curve builders

def compute_cumulative_real(
    sim_df: pd.DataFrame,
    t_zero: "datetime.datetime | None",
) -> pd.DataFrame:
    """Cumulative sims completed vs wall time, with t=0 at submission."""
    df = sim_df.dropna(subset=["end_time"]).copy()
    df = df.sort_values("end_time").reset_index(drop=True)

    if t_zero is None:
        if "start_time" in df.columns and df["start_time"].notna().any():
            t_zero = df["start_time"].min()
        else:
            t_zero = df["end_time"].min()
        print("  WARNING: submit_time_*.txt not found — using first sim start_time as t=0.")

    df["t_seconds"] = (df["end_time"] - t_zero).dt.total_seconds()
    df["cum_sims"] = range(1, len(df) + 1)

    zero_row = pd.DataFrame([{"t_seconds": 0.0, "cum_sims": 0}])
    return pd.concat([zero_row, df[["t_seconds", "cum_sims"]]], ignore_index=True)


def compute_cumulative_theoretical(sim_df: pd.DataFrame) -> pd.DataFrame:
    """Theoretical infinite-parallelism curve: all sims start at t=0."""
    df = sim_df[["duration_seconds"]].dropna().copy()
    df = df.sort_values("duration_seconds").reset_index(drop=True)
    df["cum_sims"] = range(1, len(df) + 1)
    return df[["duration_seconds", "cum_sims"]].rename(
        columns={"duration_seconds": "t_seconds"}
    )


# Analysis

def analyze(
    sim_df: pd.DataFrame,
    submit_time: "datetime.datetime | None",
    backend: str,
) -> "tuple[dict, pd.DataFrame, pd.DataFrame]":
    """Compute summary stats and cumulative curves for one backend."""
    has_timestamps = (
        "start_time" in sim_df.columns and sim_df["start_time"].notna().any()
        and "end_time" in sim_df.columns and sim_df["end_time"].notna().any()
    )

    # Determine t=0 for wall-clock measurements
    if submit_time is not None:
        t_zero = submit_time
    elif has_timestamps:
        t_zero = sim_df["start_time"].dropna().min()
    else:
        t_zero = None

    # Total wall time: submission → last end
    if t_zero is not None and has_timestamps:
        last_end = sim_df["end_time"].dropna().max()
        total_wall = (last_end - t_zero).total_seconds()
    else:
        total_wall = sim_df["duration_seconds"].max()

    total_sim = sim_df["duration_seconds"].sum()

    real_cum = (
        compute_cumulative_real(sim_df, t_zero)
        if has_timestamps
        else compute_cumulative_theoretical(sim_df)
    )
    theo_cum = compute_cumulative_theoretical(sim_df)

    summary = {
        "backend": backend,
        "total_sims": len(sim_df),
        "total_wall_seconds": total_wall,
        "total_wall_minutes": round(total_wall / 60, 2),
        "total_sim_seconds": total_sim,
        "avg_sim_duration": round(sim_df["duration_seconds"].mean(), 2),
        "min_sim_duration": round(sim_df["duration_seconds"].min(), 2),
        "max_sim_duration": round(sim_df["duration_seconds"].max(), 2),
        "sims_per_wall_hour": round(len(sim_df) / (total_wall / 3600), 1) if total_wall > 0 else None,
        "parallelism_factor": round(total_sim / total_wall, 2) if total_wall > 0 else None,
        "total_duration_hhmmss": f"{int(total_wall // 60)}:{int(total_wall % 60):02d}",
        "submit_time": submit_time.isoformat() if submit_time else None,
        "wall_includes_queue_wait": submit_time is not None,
        "ok_count": int((sim_df["status"] == "OK").sum()) if "status" in sim_df.columns else None,
        "fail_count": int((sim_df["status"] != "OK").sum()) if "status" in sim_df.columns else None,
    }
    return summary, real_cum, theo_cum


# Main

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    primary_real = None
    primary_theo = None
    primary_summary_path = None

    for backend in ("slurm", "tamu"):
        sim_df = load_sim_timing(backend)
        if sim_df is None:
            print(f"[timing_analysis] {backend}: no timing_sim_*_{backend}.json found — skipping")
            continue

        submit_time = load_submit_time(backend)
        if submit_time:
            print(f"[timing_analysis] {backend}: submit_time = {submit_time.isoformat()}")
        else:
            print(f"[timing_analysis] {backend}: submit_time_{backend}.txt not found — using first sim start_time")

        summary, real_cum, theo_cum = analyze(sim_df, submit_time, backend)

        tag = backend
        summary_path = OUT_DIR / f"timing_summary_{tag}.csv"
        pd.DataFrame([summary]).to_csv(summary_path, index=False)
        real_cum.to_csv(OUT_DIR / f"cumulative_real_{tag}.csv", index=False)
        theo_cum.to_csv(OUT_DIR / f"cumulative_theoretical_{tag}.csv", index=False)

        _print_summary(summary)

        # tamu preferred for backward-compat aliases; slurm is fallback
        if primary_real is None or backend == "tamu":
            primary_real = real_cum
            primary_theo = theo_cum
            primary_summary_path = summary_path

    # Backward-compat aliases consumed by plots.py
    if primary_real is not None:
        primary_real.to_csv(OUT_DIR / "cumulative_real.csv", index=False)
        primary_theo.to_csv(OUT_DIR / "cumulative_theoretical.csv", index=False)
        shutil.copy(primary_summary_path, OUT_DIR / "timing_summary.csv")
    else:
        print(
            "ERROR: No timing data found. Pull timing JSONs first:\n"
            "  make pull_data"
        )


def _print_summary(summary: dict) -> None:
    backend = summary["backend"].upper()
    tw = summary["total_wall_seconds"]
    ts = summary["total_sim_seconds"]
    print(f"=== {backend} Timing Summary ===")
    print(f"  Total sims:          {summary['total_sims']}")
    if summary.get("ok_count") is not None:
        print(f"  OK / Failed:         {summary['ok_count']} / {summary['fail_count']}")
    print(f"  Total wall time:     {tw:.0f}s ({tw/60:.1f} min)"
          + (" [incl. queue wait]" if summary.get("wall_includes_queue_wait") else ""))
    print(f"  Total sim-seconds:   {ts:.0f}s ({ts/60:.1f} min)")
    if summary.get("sims_per_wall_hour"):
        print(f"  Throughput:          {summary['sims_per_wall_hour']:.0f} sims/wall-hour")
    print(f"  Avg sim duration:    {summary['avg_sim_duration']:.1f}s")
    print(f"  Min/Max sim:         {summary['min_sim_duration']:.1f}s / {summary['max_sim_duration']:.1f}s")
    if summary.get("parallelism_factor"):
        print(f"  Parallelism factor:  {summary['parallelism_factor']:.1f}x")
    if summary.get("submit_time"):
        print(f"  Submission time:     {summary['submit_time']}")


if __name__ == "__main__":
    main()
