# Speaking Notes — SugarCluster Presentation

## Slide 1: Title (0:00–0:20)

> Good afternoon. I'm presenting SugarCluster — middleware to run parameter
> sweeps on the Sugarscape agent-based simulation engine at scale across
> ACES, Texas A&M's HPC cluster.

> This is for CPSC 4520 Distributed Systems. The code is in the SugarCluster
> folder of our repository.

---

## Slide 2: Agenda (0:20–0:30)

> Quick roadmap: overview and research questions, then our distributed
> architecture, results with timing stats, challenges we ran into during
> engineering, and future work. Eight minutes total.

---

## Slide 3: Overview & Research Questions (0:30–1:30)

> Sugarscape is an agent-based simulation where agents move around a grid
> collecting resources called "sugar" and "spice." They can catch diseases,
> trade, reproduce, and die. Our goal was to run systematic parameter sweeps
> at scale to answer two questions.

> First: which disease parameters — transmission chance, tag string length,
> immune system strength, and metabolism penalty — maximize or minimize the
> spread of infection?
> Second: how do socio-economic factors like wealth inequality interact with
> pandemics? Does an ethical framework like altruism or egoism change the
> outcome?

> The scale: we swept 3 values for 3 disease knobs and 7 values for the
> metabolism penalty across 8 ethical frameworks — that's 1,512 disease combinations
> plus 8 baseline runs without disease. Total: 1,520 simulations, 1,000 timesteps
> each. We actually ran this whole sweep twice using two different execution engines
> to compare them — which is a key part of the distributed systems story.

---

## Slide 4: Architecture (1:30–3:00)

> This is the middleware pipeline. Everything is driven by a single TOML file
> called sweep.toml. It declares the parameter knobs and their values. No
> hard-coded Python — adding a new knob means adding one line of TOML.

> generate_configs.py reads that TOML, computes the cartesian product, and
> emits 1,520 minimal JSON config files plus a jobs.csv manifest. "Minimal"
> means each config only contains the keys that differ from Sugarscape's
> internal defaults — this keeps configs small and avoids cascading when
> Sugarscape's defaults change upstream.

> We then had two submission strategies. The first is a SLURM job array —
> the traditional approach. The second is TAMULauncher, an ACES-specific
> parallel task runner. We ran both and can compare them directly.

> After both runs, aggregate.py parses everything into a single run_summary.csv
> and plots.py generates the figures.

---

## Slide 5: SLURM Job Array (3:00–4:00)

> Here's what the SLURM job array execution looked like. This is real data
> from SLURM's sacct command for job array 1730737.

> The key constraint we hit: ACES has a hard QOS limit on job array size,
> and separately, a global concurrency limit of 40 running jobs at once.
> So we couldn't submit 1,520 individual tasks. The workaround was hybrid
> batching — bundle 30 simulations into each task, giving 51 tasks total.
> That fits under the limits.

> Results: 51 tasks across 11 ACES nodes. Total wall time — 5 minutes and
> 16 seconds. Serial equivalent — 6,599 seconds, or 110 minutes. That's a
> 20.9× speedup, and 17,316 simulations per wall-clock hour.

> Overhead is 6% — Python interpreter startup and config loading costs about
> 8.6 seconds per batch of 30 sims. Everything else is actual simulation work.

---

## Slide 6: TAMULauncher (4:00–5:00)

> The second approach was TAMULauncher. Instead of bundling simulations into
> tasks, we generated a commands.txt file with one line per simulation — 1,520
> lines — and let TAMULauncher dispatch them across all available cores.

> No job array limit. No batching complexity. TAMULauncher checkpoints progress
> and automatically skips sims that already completed on resubmission.

> Results: 60 seconds wall time. That's a 5× speedup over the SLURM approach.
> Throughput: 91,144 simulations per wall-hour — five times better.
> The parallelism factor is 70× — because there's no batching overhead, and
> sims run truly one-per-core concurrently.

> The trade-off: we requested 8 nodes with 16 tasks per node for 128
> concurrent slots. On a busy ACES cluster, that large resource request means
> a longer queue wait — about 30 minutes before the job even started. So
> TAMULauncher won on raw throughput but lost on time-to-start.

---

## Slide 7: Head-to-Head Comparison (5:00–5:30)

> Here's the direct comparison. TAMULauncher is faster by every compute
> metric — 60 seconds versus 5 minutes, 91K versus 17K sims per hour,
> 70× versus 20× parallelism.

> But the queue wait is real. Requesting 128 CPUs across 8 nodes put us lower
> in the priority queue. TAMULauncher submitted at 6 PM and was still PENDING
> at 6:45 PM. SLURM job arrays with smaller individual resource asks clear
> the queue much faster.

> Portability also matters: SLURM job arrays work on any cluster running SLURM.
> TAMULauncher is ACES-specific — it wouldn't run on TACC Frontera or AWS,
> for example.

> Our recommendation: TAMULauncher for large sweeps where wall time matters
> more than queue time. SLURM job arrays when you need faster queue clearance
> or need to run on a non-ACES cluster.

---

## Slide 8: Results — SLURM Cumulative Completion (5:30–6:00)

> Here's the cumulative completion plot from the SLURM run. The solid blue
> line is real execution — you can see the staircase pattern as batches of
> 30 sims complete together. The dashed red line is theoretical perfect
> parallelism. The gap shows ACES scheduling overhead.

---

## Slide 9: Results — Timing Breakdown (6:00–6:30)

> Looking at per-simulation timing, there's a clear bimodal distribution.
> Simulations either run to completion at around 24.4 seconds for penalty=0,
> or they end in under half a second.

> The box plot tells the story: penalty=0 runs take ~24.4 seconds because
> agents survive to timestep 1,000. Penalty levels from 0.1 to 3.0 cause
> instant mass extinction — all agents die at timestep 1 because their
> metabolism cost exceeds the available sugar.

> This was a calibration challenge. Our original design used penalties of 0,
> 2, and 5 — but at penalty 5, everyone died instantly. We expanded the sweep
> to study intermediate penalties including 0.1, 0.25, 0.5, and 1.0.
> Even a tiny penalty of 0.1 leads to the same 89% extinction rate at timestep 1.

---

## Slide 10: Results — Heatmaps (6:30–7:00)

> Here are the scientific heatmaps for the penalty=0 subset — the only
> configuration where we can actually observe framework differences.

> Each cell shows peak infection percentage for a given transmission chance
> and immune system length. Red is 100% infected, yellow is lower. All 8
> frameworks look nearly identical — the disease physics dominate. Ethical
> decision-making doesn't register.

> Because of our scaled-up disease initialization with 25 starting diseases
> and 10 per agent, almost all agents start infected. The initial pandemic
> load simply overwhelms any transmission or immunity variations.

---

## Slide 11: Results — Survival & Inequality (7:00–7:20)

> Survival rate stacked by penalty: penalty=0 is solid across all frameworks,
> near 100%. Penalties from 0.1 to 3.0 are around 11% — only the parameter
> combos with the longest immune system and shortest disease tag survive.

> For inequality: delta Gini ≈ -0.01 for penalty=0. Wealth inequality actually
> slightly decreases under the pandemic. The flat metabolic load acts as a
> wealth compression mechanism. The effect is small — disease physics dominate
> over ethics and economics alike.

---

## Slide 12: Challenges (7:20–8:00)

> Several platform issues bit us during implementation.

> The QOS job limit was the first — ACES rejected our initial 1,520-task array.
> The initial fix was hybrid batching. The better fix was TAMULauncher.

> The global concurrency cap of 40 jobs is a separate limit. TAMULauncher
> bypasses it entirely since it's a single job that manages its own internal
> concurrency.

> Windows-to-Linux friction: backslash paths, CRLF line endings in commands.txt —
> TAMULauncher silently fails if commands.txt has Windows line endings.
> We enforce LF-only in generate_commands.py.

> $SLURM_SUBMIT_DIR doesn't point where you think — it resolves to a temp
> staging directory. We switched to PROJECT_DIR, an absolute path set as an
> environment variable.

> And the interesting TAMULauncher finding: requesting a lot of nodes means a
> long queue wait. The 8-node job sat pending for 30+ minutes. Next time we'd
> request fewer nodes with higher tasks-per-node to reduce the resource ask
> and clear the queue faster.

---

## Slide 13: Future Work (8:00–8:45)

> Five directions.

> First: tune TAMULauncher resource requests — fewer nodes, more tasks per node,
> to reduce queue wait while keeping high throughput.
> Second: sweep more parameters — environmental knobs like resource peak
> locations and pollution rates.
> Third: multiple seeds per config. With 91K sims/wall-hour we demonstrated,
> running 30 seeds per config for 45,600 total sims would take about 30 minutes.
> Fourth: a live dashboard monitoring jobs on ACES in real time.
> Fifth: Singularity containers for zero-install portability to other clusters.

---

## Slide 14: Thank You (8:45–9:00)

> To recap: SugarCluster is a TOML-driven middleware pipeline. 1,520 simulations,
> run with two execution strategies. SLURM: 5 minutes 16 seconds, 20.9×
> parallelism. TAMULauncher: 60 seconds, 70× parallelism, but ~30 minutes
> queue wait. All code is in the SugarCluster directory. Questions?
