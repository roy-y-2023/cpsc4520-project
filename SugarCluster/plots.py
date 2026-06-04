"""Generate all plots and save them to the plots/ directory"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="Set2")

PROJECT = Path(__file__).resolve().parent
RESULTS = PROJECT / "results"
OUT_DIR = PROJECT / "plots"

FRAMEWORKS = [
    "none", "altruist", "bentham", "egoist",
    "negativeBentham", "asimov", "temperance", "temperancePECS",
]
FW_LABELS = ["none", "altruist", "bentham", "egoist", "negBent", "asimov", "temper", "PECS"]


def load() -> pd.DataFrame:
    """Load run_summary.csv and coerce the survived column to bool."""
    df = pd.read_csv(RESULTS / "run_summary.csv")
    df["survived"] = df["survived"].astype(bool)
    return df


def load_sim_timing() -> pd.DataFrame:
    """Load per-sim timing from JSON files for both backends.

    De-duplicates by job_id, preferring tamu records over slurm records because
    the tamu backend captures richer wall-clock start/end timestamps.
    """
    chunks = []
    timing_dir = PROJECT / "timing"
    for pattern in ("timing_sim_*_slurm.json", "timing_sim_*_tamu.json"):
        records = []
        for p in sorted(timing_dir.glob(pattern)):
            try:
                records.append(json.loads(p.read_text()))
            except Exception:
                pass
        if records:
            chunks.append(pd.DataFrame(records))
    if not chunks:
        return pd.DataFrame()
    combined = pd.concat(chunks, ignore_index=True)
    # De-duplicate by job_id preferring tamu over slurm
    if "job_id" in combined.columns and "backend" in combined.columns:
        priority = {"slurm": 0, "tamu": 1}
        combined["_pri"] = combined["backend"].map(lambda b: priority.get(b, 0))
        combined = (
            combined.sort_values("_pri")
            .drop_duplicates(subset=["job_id"], keep="last")
            .drop(columns=["_pri"])
        )
    elif "job_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["job_id"], keep="first")
    return combined.reset_index(drop=True)

def load_cumulative():
    """Load cumulative completion curves for all available modes.

    Returns a dict with keys 'slurm', 'tamu', 'theoretical',
    each being a DataFrame or None.
    """
    def _try(name):
        p = RESULTS / name
        return pd.read_csv(p) if p.exists() else None

    return {
        "slurm": _try("cumulative_real_slurm.csv"),
        "tamu":  _try("cumulative_real_tamu.csv"),
        "theoretical": _try("cumulative_theoretical.csv"),
    }

def plot_cumulative_completion():
    curves = load_cumulative()
    fig, ax = plt.subplots(figsize=(9, 5))

    any_real = False
    if curves["slurm"] is not None:
        real = curves["slurm"]
        ax.plot(real["t_seconds"], real["cum_sims"], drawstyle="steps-post",
                linewidth=2, color="#2c7bb6", label="SLURM Job Array")
        any_real = True
    if curves["tamu"] is not None:
        real = curves["tamu"]
        ax.plot(real["t_seconds"], real["cum_sims"], drawstyle="steps-post",
                linewidth=2, color="#1a9641", label="TAMULauncher (per-sim timestamps)")
        any_real = True

    all_max = []
    for key in ("slurm", "tamu"):
        if curves[key] is not None:
            all_max.append(curves[key]["t_seconds"].max())
            ax.axvline(curves[key]["t_seconds"].max(),
                       color="#2c7bb6" if key == "slurm" else "#1a9641",
                       linestyle=":", alpha=0.4)

    cum_maxes = [curves[key]["cum_sims"].max() for key in ("slurm", "tamu") if curves[key] is not None]
    ax.set_ylim(0, (max(cum_maxes) if cum_maxes else 1000) * 1.1)
    ax.set_xlabel("Wall-clock Time (seconds)")
    ax.set_ylabel("Cumulative Simulations Completed")
    ax.set_title("Simulation Throughput: SLURM Array vs TAMULauncher")
    if any_real:
        ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cumulative_completion.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved cumulative_completion.png")

def plot_slurm_task_duration():
    sim_timing = load_sim_timing()
    if sim_timing.empty:
        print("  skipping sim_duration_hist.png (no per-sim timing data)")
        return
    ok = sim_timing[sim_timing["status"] == "OK"] if "status" in sim_timing.columns else sim_timing
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(ok["duration_seconds"], bins=20, color="#2c7bb6", edgecolor="white")
    ax.axvline(ok["duration_seconds"].mean(), color="#d7191c", linestyle="--",
               label=f"Mean: {ok['duration_seconds'].mean():.1f}s")
    ax.set_xlabel("Simulation Duration (seconds)")
    ax.set_ylabel("Number of Simulations")
    ax.set_title(f"Per-Sim Duration Distribution ({len(ok)} OK sims)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "sim_duration_hist.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved sim_duration_hist.png")

def plot_node_distribution():
    p = RESULTS / "node_distribution.csv"
    if not p.exists():
        print("  skipping node_distribution.png (no node_distribution.csv)")
        return
    nd = pd.read_csv(p)
    if nd.empty:
        print("  skipping node_distribution.png (empty node_distribution.csv)")
        return
    num_nodes = nd["num_nodes"].sum()
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(nd["tasks_per_node"].astype(str), nd["num_nodes"],
                  color="#2c7bb6", edgecolor="white")
    ax.set_xlabel("Tasks per Node")
    ax.set_ylabel("Number of Nodes")
    ax.set_title(f"ACES Node Load Distribution ({num_nodes} nodes total)")
    for bar, val in zip(bars, nd["num_nodes"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(val), ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "node_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved node_distribution.png")

def plot_timing_by_penalty():
    sim_timing = load_sim_timing()
    if sim_timing.empty:
        print("  skipping timing_by_penalty.png (no per-sim timing data)")
        return
    merged = pd.read_csv(RESULTS / "run_summary.csv")
    sim_timing = sim_timing.merge(
        merged[["job_id", "penalty", "survived"]], on="job_id", how="left"
    )
    sim_timing["penalty"] = sim_timing["penalty"].fillna(-1).astype(float)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=sim_timing, x="penalty", y="duration_seconds",
                hue="penalty", palette="Set2", legend=False, ax=ax)
    ax.set_xlabel("Disease Metabolism Penalty")
    ax.set_ylabel("Simulation Duration (seconds)")
    ax.set_title("Simulation Duration by Disease Penalty Level")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.1f}"))
    fig.tight_layout()
    fig.savefig(OUT_DIR / "timing_by_penalty.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved timing_by_penalty.png")

def plot_heatmap_penalty0():
    df = load()
    disease = df[(df["run_type"] == "disease") & (df["penalty"] == 0)].copy()

    fig, axes = plt.subplots(2, 4, figsize=(20, 10), sharex=True, sharey=True)
    axes = axes.flatten()
    for i, fw in enumerate(FRAMEWORKS):
        ax = axes[i]
        sub = disease[disease["framework"] == fw]
        pivot = sub.pivot_table(
            index="immunity", columns="transmission",
            values="peak_sick_percentage", aggfunc="mean",
        )
        sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd",
                    ax=ax, cbar=(i == 0), vmin=0, vmax=100)
        ax.set_title(FW_LABELS[i])
        ax.set_xlabel("Transmission")
        if i % 4 == 0:
            ax.set_ylabel("Immunity Length")
    fig.suptitle("Peak Infection % by Transmission & Immunity (penalty=0 only)",
                 fontsize=16, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "heatmap_penalty0.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved heatmap_penalty0.png")

def plot_survival_stacked():
    survival = pd.read_csv(RESULTS / "survival_by_penalty.csv")
    survival["framework"] = pd.Categorical(survival["framework"], categories=FRAMEWORKS)

    pivot = survival.pivot(index="framework", columns="penalty", values="survival_rate")
    pivot = pivot.reindex(FRAMEWORKS)
    
    unique_penalties = sorted(survival["penalty"].unique())
    colors = sns.color_palette("Spectral_r", len(unique_penalties))

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(kind="bar", stacked=False, ax=ax, color=colors, edgecolor="white", width=0.7)
    ax.set_xlabel("Ethical Framework")
    ax.set_ylabel("Survival Rate")
    ax.set_title("Survival Rate by Penalty Level")
    ax.set_ylim(0, 1.15)
    ax.legend(title="Penalty", labels=[str(p) for p in unique_penalties])
    ax.axhline(1.0, color="#2c7bb6", linestyle=":", alpha=0.3)
    ax.set_xticklabels(FW_LABELS, rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "survival_stacked.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved survival_stacked.png")

def plot_gini_penalty():
    df = load()
    # Filter by penalty == 0.1 and only include survived runs
    disease = df[
        (df["run_type"] == "disease") & (df["penalty"] == 0.1) & df["survived"]
    ].copy()
    disease["framework"] = pd.Categorical(disease["framework"], categories=FRAMEWORKS)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=disease, x="framework", y="delta_final_gini",
                order=FRAMEWORKS, hue="framework", palette="Set2", legend=False, ax=ax)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_ylabel("Gini Change (disease final - baseline final)")
    ax.set_title("Wealth Inequality Change Under Pandemic by Framework (penalty=0.1 only)")
    ax.set_xticks(range(len(FRAMEWORKS)))
    ax.set_xticklabels(FW_LABELS, rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "gini_penalty.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved gini_penalty.png")

def plot_memory_by_penalty():
    sim_timing = load_sim_timing()
    if sim_timing.empty or "peak_memory_mb" not in sim_timing.columns:
        print("  skipping memory plot (no peak_memory_mb data)")
        return

    merged = pd.read_csv(RESULTS / "run_summary.csv")
    sim_timing = sim_timing.merge(
        merged[["job_id", "penalty"]], on="job_id", how="left"
    )
    sim_timing["penalty"] = sim_timing["penalty"].fillna(-1).astype(float)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=sim_timing, x="penalty", y="peak_memory_mb",
                hue="penalty", palette="Spectral_r", legend=False, ax=ax)
    ax.set_xlabel("Disease Metabolism Penalty")
    ax.set_ylabel("Peak Memory Usage (MB)")
    ax.set_title("Peak Memory Usage by Disease Penalty Level")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "memory_by_penalty.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("saved memory_by_penalty.png")

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating timing + stratified plots...")
    plot_cumulative_completion()
    plot_slurm_task_duration()
    plot_node_distribution()
    plot_timing_by_penalty()
    plot_heatmap_penalty0()
    plot_survival_stacked()
    plot_gini_penalty()
    plot_memory_by_penalty()
    print(f"Done. 8 plots saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
