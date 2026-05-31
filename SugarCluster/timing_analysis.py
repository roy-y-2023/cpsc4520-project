from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parent
SLURM = PROJECT / "results" / "slurm_timing.csv"
TIMING_DIR = PROJECT / "timing"
OUT_DIR = PROJECT / "results"


def load_per_sim_timing():
    files = sorted(TIMING_DIR.glob("timing_*.csv"))
    chunks = [pd.read_csv(f) for f in files]
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()


def compute_batch_durations(sim_df):
    grouped = sim_df.groupby("job_id")["duration_seconds"].sum().reset_index()
    sim_df["batch_id"] = ((sim_df["job_id"] - 1) // 10) + 1
    batch = sim_df.groupby("batch_id").agg(
        sim_count=("job_id", "count"),
        total_sim_seconds=("duration_seconds", "sum"),
        max_sim=("duration_seconds", "max"),
    ).reset_index()
    return batch


def compute_cumulative_real(slurm_df):
    df = slurm_df.copy()
    df["end_time"] = pd.to_datetime(df["end_time"])
    df = df.sort_values("end_time")
    start = df["end_time"].min()
    df["t_seconds"] = (df["end_time"] - start).dt.total_seconds()
    df["cum_sims"] = (df.index + 1) * 10
    return df[["t_seconds", "cum_sims"]]


def compute_cumulative_theoretical(sim_df):
    batches = compute_batch_durations(sim_df)
    batches = batches.sort_values("total_sim_seconds")
    batches["cum_sims"] = batches["sim_count"].cumsum()
    batches = batches.rename(columns={"total_sim_seconds": "t_seconds"})
    return batches[["t_seconds", "cum_sims"]]


def main():
    slurm = pd.read_csv(SLURM)
    sim = load_per_sim_timing()

    slurm["start_time"] = pd.to_datetime(slurm["start_time"])
    slurm["end_time"] = pd.to_datetime(slurm["end_time"])

    first_start = slurm["start_time"].min()
    last_end = slurm["end_time"].max()
    total_wall_seconds = (last_end - first_start).total_seconds()
    total_core_seconds = slurm["elapsed_seconds"].sum()
    total_sim_seconds = sim["duration_seconds"].sum()
    num_nodes = slurm["node"].nunique()
    num_tasks = len(slurm)

    batch = compute_batch_durations(sim)
    slurm_rename = slurm[["task_id", "elapsed_seconds"]].rename(
        columns={"task_id": "batch_id", "elapsed_seconds": "slurm_elapsed"}
    )
    batch = batch.merge(slurm_rename, on="batch_id", how="left")
    batch["overhead_seconds"] = batch["slurm_elapsed"] - batch["total_sim_seconds"]
    batch["overhead_pct"] = batch["overhead_seconds"] / batch["slurm_elapsed"] * 100

    real_cum = compute_cumulative_real(slurm)
    theo_cum = compute_cumulative_theoretical(sim)

    real_cum.to_csv(OUT_DIR / "cumulative_real.csv", index=False)
    theo_cum.to_csv(OUT_DIR / "cumulative_theoretical.csv", index=False)

    tasks_per_node = slurm.groupby("node").size().reset_index(name="count")
    node_counts = tasks_per_node.groupby("count").size().reset_index(name="num_nodes")
    node_counts.columns = ["tasks_per_node", "num_nodes"]
    node_counts = node_counts.sort_values("tasks_per_node")
    node_counts.to_csv(OUT_DIR / "node_distribution.csv", index=False)

    timing_summary = pd.DataFrame([{
        "total_sims": len(sim),
        "total_slurm_tasks": num_tasks,
        "num_nodes": num_nodes,
        "total_wall_seconds": total_wall_seconds,
        "total_wall_minutes": total_wall_seconds / 60,
        "total_core_seconds": total_core_seconds,
        "total_sim_seconds": total_sim_seconds,
        "avg_slurm_elapsed": slurm["elapsed_seconds"].mean(),
        "min_slurm_elapsed": slurm["elapsed_seconds"].min(),
        "max_slurm_elapsed": slurm["elapsed_seconds"].max(),
        "avg_sim_duration": sim["duration_seconds"].mean(),
        "sims_per_wall_hour": len(sim) / (total_wall_seconds / 3600),
        "avg_batch_overhead_pct": batch["overhead_pct"].mean(),
        "avg_batch_overhead_s": batch["overhead_seconds"].mean(),
        "parallelism_factor": total_sim_seconds / total_wall_seconds,
        "total_duration_hhmmss": f"{int(total_wall_seconds // 60)}:{int(total_wall_seconds % 60):02d}",
    }])
    timing_summary.to_csv(OUT_DIR / "timing_summary.csv", index=False)

    print("=== Distributed Systems Timing Summary ===")
    print(f"  Total sims:         {len(sim)}")
    print(f"  SLURM tasks:        {num_tasks}")
    print(f"  ACES nodes used:    {num_nodes}")
    print(f"  Total wall time:    {total_wall_seconds:.0f}s ({total_wall_seconds/60:.1f} min)")
    print(f"  Total core-seconds: {total_core_seconds:.0f}s ({total_core_seconds/60:.1f} min)")
    print(f"  Total sim-seconds:  {total_sim_seconds:.0f}s ({total_sim_seconds/60:.1f} min)")
    print(f"  Throughput:         {len(sim)/(total_wall_seconds/3600):.0f} sims/wall-hour")
    print(f"  Avg sim duration:   {sim['duration_seconds'].mean():.1f}s")
    print(f"  Avg task elapsed:   {slurm['elapsed_seconds'].mean():.1f}s")
    print(f"  Avg batch overhead: {batch['overhead_seconds'].mean():.1f}s ({batch['overhead_pct'].mean():.1f}%)")
    print(f"  Parallelism factor: {total_sim_seconds/total_wall_seconds:.1f}x")
    print(f"  Serial equivalant:  {total_sim_seconds:.0f}s on 1 core vs {total_wall_seconds:.0f}s wall")


if __name__ == "__main__":
    main()
