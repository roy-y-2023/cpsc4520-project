# Speaking Notes — SugarCluster Presentation

## Slide 1: Title (0:00–0:20)

> Good afternoon. I'm presenting SugarCluster — middleware to run parameter
> sweeps on the Sugarscape agent-based simulation engine at scale across
> ACES, Texas A&M's HPC cluster.

> This is for CPSC 4520 Distributed Systems. The code is in the SugarCluster
> folder of our repository.

---

## Slide 2: Agenda (0:20–0:30)

> Quick roadmap for our 8-minute presentation: overview and research questions, 
> then our distributed middleware architecture, followed by a head-to-head 
> comparison of our two execution approaches. After that, we will discuss 
> our timing stats, scientific findings, engineering challenges, and wrap up 
> with future work.

---

## Slide 3: Overview & Research Questions (0:30–1:30)

> Sugarscape is an agent-based simulation where agents move around a grid
> collecting resources called "sugar" and "spice." They can catch diseases,
> trade, reproduce, and die. Our goal was to run systematic parameter sweeps
> at scale to answer two main questions:

> First: which disease parameters — transmission chance, tag string length,
> immune system strength, and metabolism penalty — maximize or minimize the
> spread of infection?

> Second: how do socio-economic factors like wealth inequality interact with
> pandemics? Does an ethical framework like altruism or egoism change the
> outcome?

> To answer these, we swept 5 transmission chances, 3 tag lengths, 3 immunity 
> lengths, and 6 metabolism penalties across 8 ethical frameworks. That is 
> 2,160 disease combinations plus 8 baseline runs without disease, for a total of 
> 2,168 simulations. We ran this entire sweep twice, once using standard SLURM 
> job arrays and once using TAMULauncher, allowing us to compare the two 
> distributed system strategies.

---

## Slide 4: Architecture (1:30–2:30)

> This is our middleware pipeline, designed to be fully declarative. Everything 
> is driven by a single TOML file called sweep.toml. There are no hard-coded 
> parameter values in Python. Adding a new knob simply requires adding one line 
> in the TOML file and one line in our config template.

> generate_configs.py reads sweep.toml, computes the Cartesian product, and
> emits 2,168 minimal JSON config files along with a jobs.csv manifest. The config 
> files only store keys that differ from Sugarscape's defaults, which prevents 
> configuration bloat.

> From there, we submit the runs using two strategies: standard SLURM Job Array 
> (submit.slurm) or TAMULauncher (submit_tamulauncher.slurm). Once the jobs 
> finish, we pull the results, aggregate.py parses the JSON outputs and timing logs 
> into run_summary.csv, and plots.py generates the 8 presentation figures.

---

## Slide 5: Approach 1: SLURM Job Array (2:30–3:30)

> Here's our first submission strategy: a SLURM Job Array. This slide displays 
> real data from SLURM's sacct command for job array 1741358.

> The primary bottleneck here was the ACES Quality of Service limits: the maximum 
> array size was too small to submit all 2,168 simulations as separate tasks, 
> and there is a global concurrency cap of 50 running jobs.

> To work around this, we implemented hybrid batching, bundling 28 simulations 
> into each SLURM task, resulting in 78 active tasks total.

> With this hybrid batching, the sweep ran across 13 unique ACES nodes. The total 
> wall time was 12 minutes and 5 seconds. The serial equivalent execution is 
> 23,186 seconds (or 386.4 minutes), meaning we achieved a 32.0× speedup and 
> an effective throughput of 10,761 simulations per wall-clock hour.

---

## Slide 6: Approach 2: TAMULauncher (3:30–4:30)

> Our second submission strategy is TAMULauncher, a custom task launcher on ACES. 
> Instead of bundling simulations into hybrid tasks, we generate a commands.txt 
> file with one command line per simulation — 2,168 lines total — and let 
> TAMULauncher automatically dispatch them.

> This approach bypasses SLURM job array size limits and requires no complex 
> batching logic. It also supports automatic check-pointing, skipping 
> already-completed simulations on resubmission.

> We requested 20 nodes with 12 tasks per node, giving us 240 concurrent slots. 
> The sweep completed in just 2 minutes and 27 seconds of wall time. The serial 
> equivalent is 22,480 seconds (or 374.7 minutes), representing a 152.6× speedup 
> and an effective throughput of 52,983 simulations per wall-clock hour.

---

## Slide 7: SLURM vs TAMULauncher: Head-to-Head (4:30–5:15)

> Comparing the two backends head-to-head, TAMULauncher is the clear winner for 
> raw execution speed: it completes the sweep in 2 minutes 27 seconds compared 
> to SLURM's 12 minutes 5 seconds. This is a 4.9× improvement in wall time, 
> increasing the throughput from 10K to 52K simulations per hour.

> However, scheduling trade-offs are important. While requesting 128 cores with 
> high density (16 tasks per node) in previous tests led to memory contention 
> and killed tasks, our updated request of 240 CPUs across 20 nodes (increasing 
> density to 12 tasks per node) resolved the issue and allowed near-instant queue clearance.

> Additionally, portability is a key factor. SLURM job arrays are portable to 
> almost any cluster, whereas TAMULauncher is specific to ACES. We recommend 
> TAMULauncher for massive sweeps where execution wall time dominates, and SLURM 
> Job Arrays when queue wait times or portability are the primary concerns.

---

## Slide 8: Results: Distributed Systems (5:15–5:45)

> This plot shows the cumulative completion curves for both runs. 

> The blue staircase line represents the SLURM Job Array, where the steps clearly 
> reflect our 28-simulation hybrid batches completing.

> The green line shows TAMULauncher, which has a much smoother and steeper curve 
> because tasks complete individually. It finishes much earlier, at 2 minutes 27 seconds.

> The dashed red line represents the theoretical perfect parallelism baseline, 
> and the gap between the curves and the baseline highlights scheduler dispatch 
> overhead on ACES.

---

## Slide 9: Results: Timing Breakdown (5:45–6:15)

> Looking at per-simulation duration, we see a tightly unimodal distribution, 
> shown in the histogram on the left and the boxplot on the right.

> Simulations run to completion at around 10.4 seconds across all configurations.

> Unlike previous runs, the bimodal duration distribution is gone. Because agents 
> start with zero diseases and contract them from the environment, the initial 
> disease load is low. This prevents early mass extinctions, enabling 100% 
> survival of the simulation population to the 1,000-timestep limit.

---

## Slide 10: Results: Scientific Findings (6:15–6:45)

> Here are the infection heatmaps for the penalty=0 subset, stratified across the 
> 8 ethical frameworks. Each cell shows the peak sick percentage based on 
> transmission chance and immunity length.

> Transmission of 1.0 combined with an immunity length of 10 leads to 100% 
> infection peaks. A transmission chance of 0.05 and immunity length of 60 
> minimizes the spread.

> Crucially, all 8 ethical frameworks look nearly identical. Because we initialize 
> the runs with 5 starting diseases and 0 diseases per agent, the dynamic load is 
> identical across frameworks, and disease physics dominates ethical decision-making.

---

## Slide 11: Results: Survival by Penalty (6:45–7:05)

> This slide displays the survival rate stacked by disease penalty level.

> We see 100% survival across all penalty levels from 0.0 to 2.0.

> Because agents start with 0 diseases, the severe metabolic penalty doesn't lead 
> to early population collapse. Ethical frameworks do not change survival outcomes; 
> all frameworks show identical 100% survival.

---

## Slide 12: Results: Inequality (Gini Coefficient) (7:05–7:25)

> We also analyzed wealth inequality by looking at the change in the Gini coefficient.

> Under the disease sweep with penalty=0.1, wealth inequality slightly 
> decreases, with a mean delta Gini of approximately −0.008.

> The metabolic penalty acts as a mild wealth compression force. The Gini coefficient 
> drops from 0.30 to 0.291 across all frameworks. Economic parameters of the disease 
> continue to dominate over ethical behavior, but the effect is highly compressed 
> due to the mild disease progression.

---

## Slide 13: Challenges: Engineering Lessons (7:25–7:55)

> We encountered several platform challenges during implementation.

> First, ACES job array and concurrency limits forced us to use hybrid batching 
> for SLURM (80 tasks × 28 sims), which we bypassed using TAMULauncher.

> We also ran into Windows-to-Linux friction: path separators (`\`) and Windows 
> CRLF line endings in commands.txt caused silent TAMULauncher worker failures, 
> which we fixed by forcing Unix LF line endings in our generators.

> Additionally, `$SLURM_SUBMIT_DIR` resolves to a temporary staging directory 
> on ACES, so we switched to using an absolute `PROJECT_DIR` environment variable. 
> Finally, we learned to interpret TAMULauncher's log outputs, where normal 
> teardown looked like process termination but was actually normal behavior.

---

## Slide 14: Challenges: Middleware Design (7:55–8:15)

> A key design goal was to keep our middleware reusable and decoupled from this 
> specific experiment.

> We succeeded by separating declarative configuration in sweep.toml from the 
> Python generator and execution backends.

> Adding a new parameter knob requires only a single line in the TOML file and 
> one line in the config template. Swapping the execution engine is as simple as 
> switching from submit.slurm to submit_tamulauncher.slurm without changing 
> any simulation or middleware code.

---

## Slide 15: Future Work (8:15–8:45)

> We propose four areas for future research.

> First, expanding the parameter sweep to cover environmental variables such as 
> resource peak locations and pollution rates, or agent genetics.

> Second, running multiple seeds per configuration. Since we demonstrated a 
> throughput of 52K simulations per hour, running 30 seeds per config (over 65K runs) 
> is now fully tractable in under two hours.

> Third, building a live dashboard to monitor ACES jobs in real time.

> Fourth, containerizing the setup using Singularity/Docker for zero-install 
> cluster portability.

---

## Slide 16: Thank You / Questions (8:45–9:00)

> In summary, SugarCluster is a TOML-driven middleware pipeline that ran 2,168 
> simulations across two different cluster execution engines. SLURM completed 
> in 12 minutes 5 seconds with 32.0× parallelism, while TAMULauncher completed 
> in 2 minutes 27 seconds with 152.6× parallelism and near-instant queue clearance.

> All code and analysis scripts are located in the SugarCluster directory.

> Thank you, and I am happy to take any questions.

---

*Repository: github.com/roy-y-2023/cpsc4520-project · SLURM job: 1741358 · TAMULauncher job: 1741350*
