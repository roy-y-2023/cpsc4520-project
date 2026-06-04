# Oral Presentation Script — SugarCluster

## Title (0:00–0:20)

Hey everyone, thanks for coming. So today I'm going to talk about SugarCluster — it's middleware we built to run parameter sweeps on the Sugarscape agent-based simulation, and we ran it at scale on Texas A&M's ACES cluster.

This is for CPSC 4520, Distributed Systems. All the code lives in the SugarCluster folder of our repo.

---

## Agenda (0:20–0:30)

Here's the roadmap for our eight minutes. I'll start with an overview and our research questions, then go through our distributed middleware architecture. After that, we'll compare our two execution strategies side by side, look at the timing data, go over our scientific findings, talk about the engineering challenges we hit, and wrap up with future work.

---

## Overview & Research Questions (0:30–1:30)

So what is Sugarscape? It's an agent-based simulation where agents move around a grid collecting resources — sugar and spice. They can trade with each other, catch diseases, reproduce, and die. Pretty rich little world.

Our goal was to run systematic parameter sweeps at scale to answer two main questions.

First — which disease parameters maximize or minimize the spread of infection? We're talking transmission chance, tag string length, immune system strength, and metabolism penalty.

Second — how do socio-economic factors like wealth inequality interact with pandemics? Does an ethical framework like altruism or egoism actually change the outcome?

To answer these, we swept five transmission chances, three tag lengths, three immunity lengths, and six metabolism penalties across eight ethical frameworks. That gives us 2,160 disease combinations plus eight baseline runs with no disease — 2,168 simulations total. And we ran the whole thing twice: once with SLURM job arrays, once with TAMULauncher. That way we could compare the two distributed strategies.

---

## Architecture (1:30–2:30)

Here's our middleware pipeline. Everything is driven by one TOML file called `sweep.toml`. No hard-coded parameter values anywhere in Python. If you want to add a new knob, you just add one line to the TOML and one line to the config template.

`generate_configs.py` reads that TOML file, computes the Cartesian product, and spits out 2,168 minimal JSON configs plus a `jobs.csv` manifest. The config files only store the keys that differ from Sugarscape's defaults — so no configuration bloat.

From there, we submit the runs using two strategies. Standard SLURM Job Array, or TAMULauncher. Once the jobs finish, we pull the results, and `aggregate.py` parses all the JSON outputs and timing logs into `run_summary.csv`. Then `plots.py` generates the seven figures you'll see in our results slides.

---

## Approach 1: SLURM Job Array (2:30–3:30)

Okay, so here's our first submission strategy: SLURM Job Array.

The big bottleneck we ran into was ACES's Quality of Service limits. The max array size was too small to submit all 2,168 simulations as separate tasks, and there's a global concurrency cap of 40 running jobs.

So here's what we did — we implemented hybrid batching. We bundled 28 simulations into each SLURM task, which gives us 78 active tasks total. It's not ideal, but it works around the limit.

With this hybrid setup, the sweep ran across 13 unique ACES nodes. The total wall time was 12 minutes and 5 seconds. If you ran all 2,168 sims one by one, that'd take about 386 minutes. So we got a 32× speedup — that's an effective throughput of 10,761 simulations per wall-clock hour.

---

## Approach 2: TAMULauncher (3:30–4:30)

Now for our second strategy: TAMULauncher. It's a custom task launcher on ACES.

Instead of bundling simulations into hybrid tasks, we generate a `commands.txt` file with one command line per simulation — 2,168 lines — and let TAMULauncher dispatch them automatically.

The big win here is that it bypasses SLURM job array size limits. No complex batching logic needed. And it supports automatic check-pointing, so if you resubmit, it skips sims that already finished.

We requested 20 nodes with 12 tasks per node — 240 concurrent slots. The sweep completed in just 2 minutes and 27 seconds. The serial equivalent is about 375 minutes, so that's a 152.6× speedup — 52,983 simulations per wall-clock hour. Pretty wild.

---

## SLURM vs TAMULauncher: Head-to-Head (4:30–5:15)

Alright, let's put them side by side.

TAMULauncher is the clear winner on raw speed. It finishes in 2 minutes 27 seconds compared to SLURM's 12 minutes 5 seconds — that's a 4.9× improvement. Throughput jumps from about 10K to 53K simulations per hour.

But there are trade-offs. In earlier tests, we tried requesting 128 cores with 16 tasks per node — high density — and that led to memory contention that killed tasks. So we bumped it to 240 CPUs across 20 nodes, 12 tasks per node, and that resolved the issue. Queue clearance was nearly instant.

Portability matters too. SLURM job arrays work on basically any cluster, but TAMULauncher is ACES-specific. Our recommendation: use TAMULauncher for massive sweeps where wall time dominates, and SLURM job arrays when queue wait or portability are the priority.

---

## Results: Distributed Systems (5:15–5:45)

This plot shows the cumulative completion curves for both runs.

The blue staircase line is the SLURM Job Array — you can clearly see the steps where each batch of 28 sims completes. The green line is TAMULauncher. It's much smoother and steeper because tasks finish individually. It wraps up at 2 minutes 27 seconds.

The gap between those curves really shows the difference in scheduling dispatch overhead between standard SLURM arrays and TAMULauncher on ACES.

---

## Results: Timing Breakdown (5:45–6:15)

Now let's look at how long each simulation actually takes. What we see is a tightly unimodal distribution — both the histogram and boxplot confirm this.

Simulations run to completion in about 10.4 seconds across all configurations. The baseline runs with no disease — labeled as penalty -1.0 — finish a bit faster, around 10.2 seconds.

Here's the interesting part. Unlike previous runs, the bimodal duration distribution is gone. Because agents start with zero diseases and contract them from the environment, the initial disease load is low. That prevents early mass extinctions. So we get 100% survival of the population to the 1,000-timestep limit.

---

## Results: Scientific Findings (6:15–6:45)

These are the infection heatmaps for the penalty=0 subset, broken down across the eight ethical frameworks. Each cell shows the peak sick percentage based on transmission chance and immunity length.

The short version: transmission of 1.0 combined with immunity length 10 gives you a 68% infection peak. On the flip side, transmission of 0.05 with immunity length 60 minimizes spread to just 2%.

Now here's the kicker — all eight ethical frameworks look nearly identical. Since we initialize runs with 5 starting diseases and 0 diseases per agent, the dynamic load is the same across frameworks. Disease physics completely dominates ethical decision-making.

---

## Results: Survival by Penalty (6:45–7:05)

This slide shows survival rate stacked by disease penalty level.

We see 100% survival across all penalty levels from 0.0 to 2.0. Because agents start with no diseases, the severe metabolic penalty doesn't cause early population collapse. And ethical frameworks don't change survival outcomes either — all frameworks show identical 100% survival.

---

## Results: Inequality — Gini Coefficient (7:05–7:25)

We also looked at wealth inequality using the Gini coefficient.

Under the disease sweep with penalty=0.1, wealth inequality slightly decreases. The mean delta Gini is about minus 0.008.

Basically, the metabolic penalty acts as a mild wealth compression force. Gini drops from 0.30 to 0.291 across all frameworks. The disease economics still dominate over ethical behavior, but the effect is pretty compressed because the infection load is mild.

---

## Challenges: Engineering Lessons (7:25–7:55)

We hit several platform challenges along the way.

First, ACES job array and concurrency limits forced us into hybrid batching for SLURM — 80 tasks with 28 sims each. For TAMULauncher, we had to adjust the concurrency density to 12 tasks per node to get rapid queue clearance.

We also dealt with Windows-to-Linux friction. Path separators — backslashes — and CRLF line endings in `commands.txt` caused silent TAMULauncher worker failures. We fixed that by forcing Unix LF line endings in our generators.

Then there was the `$SLURM_SUBMIT_DIR` issue. It resolves to a temporary staging directory on ACES, not our project directory. So we switched to using an absolute `PROJECT_DIR` environment variable instead.

Oh, and we spent way too long debugging what looked like a process crash in the TAMULauncher logs. Turns out that was just normal teardown behavior — it's not actually an error. Learned that the hard way.

Finally, when the data analysis started running slow, we used `ThreadPoolExecutor` to parallelize parsing all the Sugarscape JSON outputs. That sped up aggregation a lot.

---

## Future Work (7:55–8:25)

We've got five areas for future work.

First, expanding the parameters to cover environmental variables — resource peak locations, seasons, agent trading behavior.

Second, running multiple seeds per configuration. Since we hit 52K simulations per hour, running 30 seeds per config — that's over 65K runs — is totally doable in under two hours now.

Third, building a live interactive dashboard so you can monitor ACES jobs in real time while they're running.

Fourth, implementing automatic concurrency tuning to dynamically adjust task density and optimize the balance between queue wait and execution throughput.

And fifth, building abstraction layers so you could run this on other supercomputers or clusters with minimal code changes.

---

## Thank You / Questions (8:25–8:40)

So to wrap up — SugarCluster is a TOML-driven middleware pipeline that ran 2,168 simulations across two different cluster execution engines. SLURM finished in 12 minutes 5 seconds with 32× parallelism. TAMULauncher finished in 2 minutes 27 seconds with 152.6× parallelism and near-instant queue clearance.

All the code and analysis scripts are in the SugarCluster directory of our repo.

Thanks, happy to take questions.

---

*Repository: github.com/roy-y-2023/cpsc4520-project · SLURM job: 1741358 · TAMULauncher job: 1741350*
