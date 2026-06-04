# Speaking Notes — SugarCluster Presentation

## Slide 1: Title (0:00–0:20)

> Good afternoon. I'm presenting SugarCluster — middleware to run parameter
> sweeps on the Sugarscape agent-based simulation engine at scale across
> ACES, Texas A&M's HPC cluster.

> This is for CPSC 4520 Distributed Systems. The code is in the SugarCluster
> folder of our repository.

---

## Slide 2: Overview & Research Questions (0:20–1:10)

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

## Slide 3: Architecture (1:10–2:00)

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
> into run_summary.csv, and plots.py generates the presentation figures.

---

## Slide 4: Challenges: Too Many Ways to Run a Job (2:00–2:40)

> When designing the middleware, one of our biggest challenges was selecting the right 
> execution strategy. ACES offers at least five different ways to run jobs, and it wasn't 
> obvious which one was optimal.

> SLURM Job Arrays sounded straightforward but we quickly hit QOS array-size limits. 
> TAMULauncher is ACES-specific and underdocumented, making it feel like a risky complexity. 
> Other options like the Drona GUI engine lacked terminal control, while MPI/OpenMP had too 
> much overhead for independent simulations, and CCTools Work Queue added external dependencies.

> Ultimately, we decided to start with the option that seemed most familiar—standard SLURM Job Arrays—and see how far we could push standard batch scheduling.

---

## Slide 5: Approach 1: SLURM Job Array (2:40–3:30)

> Here's our first submission strategy: a SLURM Job Array. This slide displays 
> real data from SLURM's sacct command for job array 1741358.

> The immediate challenge we hit was the strict ACES Quality of Service limits: the maximum 
> array size was too small to submit all 2,168 simulations as separate tasks, 
> and there is a global concurrency cap of 40 running jobs that prevented us from running multiple arrays in parallel.

> To work around this and fit within the limits, we had to implement hybrid batching: 
> writing a Python runner script to sequentially run multiple simulation tasks within a 
> single SLURM job. Specifically, we bundled 28 simulations into each task, 
> resulting in 78 active tasks across an 80-task array.

> While this hybrid batching got the job done across 13 ACES nodes in 12 minutes 
> and 5 seconds, it introduced significant scripting complexity, and the global concurrency cap 
> of 40 running jobs limited our parallelism factor to 32×.

---

## Slide 6: Approach 2: TAMULauncher (3:30–4:20)

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

> While we could request more CPUs per node (like 48 cores) to increase throughput, 
> the queue wait time would shoot up to half a day or more due to resource constraints. 
> So, we found that requesting 12 CPUs per node strikes the best balance between concurrency 
> and rapid queue clearance.

---

## Slide 7: SLURM vs TAMULauncher: Head-to-Head (4:20–5:05)

> Comparing the two backends head-to-head, TAMULauncher is the clear winner for 
> raw execution speed: it completes the sweep in 2 minutes 27 seconds compared 
> to SLURM's 12 minutes 5 seconds. This is a 4.9× improvement in wall time, 
> increasing the throughput from 10K to 52K simulations per hour.

> However, scheduling trade-offs are important. While requesting high density 
> (such as 48 tasks per node) in other environments can cause queue waits or memory 
> contention, our balanced request of 240 CPUs via 12 tasks per node resolved queue 
> times and resource caps.

> Additionally, portability is a key factor. SLURM job arrays are portable to 
> almost any cluster, whereas TAMULauncher is specific to ACES. We recommend 
> TAMULauncher for massive sweeps where execution wall time dominates, and SLURM 
> Job Arrays when queue wait times or portability are the primary concerns.

---

## Slide 8: Results: Distributed Systems (5:05–5:35)

> This plot shows the cumulative completion curves for both runs. 

> The blue staircase line represents the SLURM Job Array, where the steps clearly 
> reflect our 28-simulation hybrid batches completing.

> The green line shows TAMULauncher, which has a much smoother and steeper curve 
> because tasks complete individually. It finishes much earlier, at 2 minutes 27 seconds.

> The gap between the curves highlights the difference in scheduling dispatch 
> overhead between standard SLURM arrays and TAMULauncher on ACES.

---

## Slide 9: Results: Timing Breakdown (5:35–6:05)

> Looking at per-simulation duration, we see a tightly unimodal distribution, 
> shown in the histogram on the left and the boxplot on the right.

> Simulations run to completion at around 10.4 seconds across all configurations. 
> The baseline runs without disease, labeled as penalty -1.0 on the plot, finish slightly 
> faster at around 10.2 seconds.

> Unlike previous runs, the bimodal duration distribution is gone. Because agents 
> start with zero diseases and contract them from the environment, the initial 
> disease load is low. This prevents early mass extinctions, enabling 100% 
> survival of the simulation population to the 1,000-timestep limit.

---

## Slide 10: Results: Scientific Findings (6:05–6:35)

> Here are the infection heatmaps for the penalty=0 subset, stratified across the 
> 8 ethical frameworks. Each cell shows the peak sick percentage based on 
> transmission chance and immunity length.

> Transmission of 1.0 combined with an immunity length of 10 leads to a 68% 
> infection peak. A transmission chance of 0.05 and immunity length of 60 
> minimizes the spread to just 2%.

> Crucially, all 8 ethical frameworks look nearly identical. Because we initialize 
> the runs with 5 agents with disease, the dynamic load is 
> identical across frameworks, and disease physics dominates ethical decision-making.

---

## Slide 11: Results: Survival by Penalty (6:35–6:55)

> This slide displays the survival rate stacked by disease penalty level.

> We see 100% survival across all penalty levels from 0.0 to 2.0.

> Because agents start with 0 diseases, the severe metabolic penalty doesn't lead 
> to early population collapse. Ethical frameworks do not change survival outcomes; 
> all frameworks show identical 100% survival.

---

## Slide 12: Results: Inequality (Gini Coefficient) (6:55–7:15)

> We also analyzed wealth inequality by looking at the change in the Gini coefficient.

> Under the disease sweep with penalty=0.1, wealth inequality slightly 
> decreases, with a mean delta Gini of approximately −0.008.

> The metabolic penalty acts as a mild wealth compression force. The Gini coefficient 
> drops from 0.30 to 0.291 across all frameworks. Economic parameters of the disease 
> continue to dominate over ethical behavior, but the effect is highly compressed 
> due to the mild disease progression.

---

## Slide 13: Challenges: Engineering Lessons (7:15–7:45)

> During implementation, we encountered several distinct engineering hurdles.

> First, we faced a misleading log issue under TAMULauncher: the workers reported 
> being killed, which looked like an out-of-memory or timeout error. After debugging, 
> we realized it was just normal teardown behavior when the launcher terminated.

> Second, the SLURM submit directory variable resolved to a temporary staging folder 
> on ACES rather than our project directory, which we resolved by forcing absolute paths.

> Third, cross-platform path separators caused issues: `os.path.join` produced backslashes 
> on Windows, which failed on ACES's Linux environment. We fixed this by enforcing 
> forward-slash separators in our job manifest.

> Fourth, CRLF line endings on Windows caused silent execution failures in the 
> TAMULauncher commands file, which we fixed by enforcing LF line endings in our generators.

> Finally, when parsing the 2,168 simulation output files became a bottleneck, we parallelized 
> the parsing script using a ThreadPoolExecutor, drastically reducing aggregation time.

---

## Slide 14: Future Work (7:45–8:15)

> We propose five key areas for future research.

> First, expanding the parameters to cover environmental variables such as 
> resource peak locations, seasons, and agent trading behavior.

> Second, running multiple seeds per configuration. Since we demonstrated a 
> throughput of 52K simulations per hour, running 30 seeds per config (over 65K runs) 
> is now fully tractable in under two hours.

> Third, building a live, interactive dashboard to monitor ACES jobs in real time.

> Fourth, implementing automatic concurrency tuning to dynamically adjust task 
> density and optimize queue wait versus execution throughput.

> Fifth, establishing abstraction layers to run on other supercomputers or 
> clusters with minimal code changes.

---

## Slide 15: Thank You / Questions (8:15–8:30)

> In summary, SugarCluster is a TOML-driven middleware pipeline that ran 2,168 
> simulations across two different cluster execution engines. SLURM completed 
> in 12 minutes 5 seconds with 32.0× parallelism, while TAMULauncher completed 
> in 2 minutes 27 seconds with 152.6× parallelism and near-instant queue clearance.

> All code and analysis scripts are located in the SugarCluster directory.

> Thank you, and I am happy to take any questions.

---

*Repository: github.com/roy-y-2023/cpsc4520-project · SLURM job: 1741358 · TAMULauncher job: 1741350*
