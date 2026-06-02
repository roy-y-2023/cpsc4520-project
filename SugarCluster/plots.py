from pathlib import Path
import matplotlib
matplotlib.use("Agg")
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


def load():
    df = pd.read_csv(RESULTS / "run_summary.csv")
    df["survived"] = df["survived"].astype(bool)
    return df


def load_slurm():
    return pd.read_csv(RESULTS / "slurm_timing.csv")


def load_cumulative():
    real = pd.read_csv(RESULTS / "cumulative_real.csv")
    theo = pd.read_csv(RESULTS / "cumulative_theoretical.csv")
    return real, theo


def load_node_dist():
    return pd.read_csv(RESULTS / "node_distribution.csv")


def get_sims_per_job():
    import re
    submit_slurm = PROJECT / "submit.slurm"
    if submit_slurm.exists():
        with open(submit_slurm, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'SIMS_PER_JOB="\$\{SIMS_PER_JOB:-(\d+)\}"', content)
            if match:
                return int(match.group(1))
    return 30


# ─── PLOT 1: Cumulative Completion (Real vs Theoretical) ────────

def plot_cumulative_completion():
    real, theo = load_cumulative()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(real["t_seconds"], real["cum_sims"], drawstyle="steps-post",
            linewidth=2, color="#2c7bb6", label="Real (SLURM sacct)")
    ax.plot(theo["t_seconds"], theo["cum_sims"], drawstyle="steps-post",
            linewidth=2, linestyle="--", color="#d7191c", label="Theoretical (perfect parallelism)")
    ax.axvline(theo["t_seconds"].max(), color="#d7191c", linestyle=":", alpha=0.4)
    ax.axvline(real["t_seconds"].max(), color="#2c7bb6", linestyle=":", alpha=0.4)
    ax.set_xlabel("Wall-clock Time (seconds)")
    ax.set_ylabel("Cumulative Simulations Completed")
    ax.set_title("Simulation Throughput: Real vs Theoretical")
    ax.legend(loc="lower right")
    
    max_sims = max(real["cum_sims"].max(), theo["cum_sims"].max()) if not real.empty else 1600
    ax.set_ylim(0, max_sims * 1.1)
    
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cumulative_completion.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved cumulative_completion.png")


# ─── PLOT 2: SLURM Task Duration Histogram ─────────────────────

def plot_slurm_task_duration():
    slurm = load_slurm()
    sims_per_job = get_sims_per_job()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(slurm["elapsed_seconds"], bins=12, color="#2c7bb6", edgecolor="white")
    ax.axvline(slurm["elapsed_seconds"].mean(), color="#d7191c", linestyle="--",
               label=f"Mean: {slurm['elapsed_seconds'].mean():.0f}s")
    ax.set_xlabel("SLURM Task Duration (seconds)")
    ax.set_ylabel("Number of Tasks")
    ax.set_title(f"Distribution of {len(slurm)} SLURM Task Durations ({sims_per_job} sims each)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "slurm_task_duration.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved slurm_task_duration.png")


# ─── PLOT 3: Node Distribution ─────────────────────────────────

def plot_node_distribution():
    nd = load_node_dist()
    slurm = load_slurm()
    num_nodes = slurm["node"].nunique() if not slurm.empty else 20
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


# ─── PLOT 4: Per-Sim Timing by Penalty ─────────────────────────

def plot_timing_by_penalty():
    sim_timing = pd.concat(
        [pd.read_csv(f) for f in sorted((PROJECT / "timing").glob("timing_*.csv"))],
        ignore_index=True
    )
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


# ─── PLOT 5: Heatmap (Penalty=0 Only) ──────────────────────────

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


# ─── PLOT 6: Survival Stacked by Penalty ───────────────────────

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


# ─── PLOT 7: Gini Delta for Penalty=0 ──────────────────────────

def plot_gini_penalty0():
    df = load()
    disease = df[(df["run_type"] == "disease") & (df["penalty"] == 0)].copy()
    disease["framework"] = pd.Categorical(disease["framework"], categories=FRAMEWORKS)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=disease, x="framework", y="delta_final_gini",
                order=FRAMEWORKS, hue="framework", palette="Set2", legend=False, ax=ax)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_ylabel("Gini Change (disease final - baseline final)")
    ax.set_title("Wealth Inequality Change Under Pandemic by Framework (penalty=0 only)")
    ax.set_xticks(range(len(FRAMEWORKS)))
    ax.set_xticklabels(FW_LABELS, rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "gini_penalty0.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved gini_penalty0.png")


# ─── PLOT 8: Peak Memory Usage by Penalty ───────────────────────

def plot_memory_by_penalty():
    sim_timing = pd.concat(
        [pd.read_csv(f) for f in sorted((PROJECT / "timing").glob("timing_*.csv"))],
        ignore_index=True
    )
    if "peak_memory_mb" not in sim_timing.columns:
        print("  skipping memory plot (no peak_memory_mb column)")
        return

    merged = pd.read_csv(RESULTS / "run_summary.csv")
    sim_timing = sim_timing.merge(
        merged[["job_id", "penalty"]], on="job_id", how="left"
    )
    sim_timing["penalty"] = sim_timing["penalty"].fillna(-1).astype(float)
    unique_penalties = sorted(sim_timing["penalty"].unique())
    
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=sim_timing, x="penalty", y="peak_memory_mb",
                hue="penalty", palette="Spectral_r", legend=False, ax=ax)
    ax.set_xlabel("Disease Metabolism Penalty")
    ax.set_ylabel("Peak Memory Usage (MB)")
    ax.set_title("Peak Memory Usage by Disease Penalty Level")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "memory_by_penalty.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved memory_by_penalty.png")


# ─── MAIN ───────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating timing + stratified plots...")
    plot_cumulative_completion()
    plot_slurm_task_duration()
    plot_node_distribution()
    plot_timing_by_penalty()
    plot_heatmap_penalty0()
    plot_survival_stacked()
    plot_gini_penalty0()
    plot_memory_by_penalty()
    print(f"Done. 8 plots saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
