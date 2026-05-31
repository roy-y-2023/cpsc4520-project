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

> The scale: we swept 3 values for each of 4 disease knobs across 8 ethical
> frameworks — that's 648 disease combinations plus 8 baseline runs without
> disease. Total: 656 simulations, 1,000 timesteps each. We used seed 12345
> and collected per-timestep metrics in JSON.

---

## Slide 4: Architecture (1:30–3:30)

> This is the middleware pipeline. Everything is driven by a single TOML file
> called sweep.toml. It declares the parameter knobs and their values. No
> hard-coded Python — adding a new knob means adding one line of TOML.

> generate_configs.py reads that TOML, computes the cartesian product, and
> emits 656 minimal JSON config files plus a jobs.csv manifest. "Minimal"
> means each config only contains the keys that differ from Sugarscape's
> internal defaults — this keeps configs small and avoids cascading when
> Sugarscape's defaults change upstream.

> The submit.slurm script dispatches these as a SLURM job array. But we
> couldn't submit 656 array tasks because ACES has a QOS limit on job array
> size. So we bundled 10 simulations into each task — 66 tasks total instead
> of 656. That's the SIMS_PER_JOB parameter, configurable via an environment
> variable.

> On ACES, each task runs run_batch.py which loops through its 10 configs,
> records per-simulation timing, and writes a per-batch timing CSV. After all
> jobs finish, we pull the data back with rsync — 656 JSON logs plus 66 timing
> files.

> Back on our local machine, aggregate.py parses everything into a single
> run_summary.csv. analyze.py computes grouped statistics. And plots.py
> generates the figures you'll see in the results section. The entire pipeline
> is automated — you change sweep.toml and re-run the scripts.

---

## Slide 5: Distributed Execution Details (3:30–5:00)

> Here's what the actual execution looked like on ACES. This is real data
> pulled from SLURM's sacct command for job array 1722415.

> 66 tasks across 20 different ACES nodes. Each task runs 10 simulations
> sequentially. Node distribution is shown here — most nodes handled 1–3 tasks.

> Key numbers: total wall time — 2 minutes and 23 seconds. That's the real
> clock time from first task start to last task end. The serial equivalent —
> if we ran all 656 sims one after another on a single core — would have been
> 3,681 seconds, or 61 minutes. So we got a 25.7x speedup.

> Throughput: over 16,000 simulations per wall-clock hour. Overhead is just
> 1.3% — the Python interpreter startup and config loading costs about 0.8
> seconds per batch of 10 sims. Everything else is actual simulation work.

> The cumulative completion plot visualizes this: the solid blue line is the
> real execution — you can see it takes about 50 seconds for the first few
> tasks to start completing, then it accelerates as more nodes get allocated.
> The dashed red line is the theoretical best case if all 66 tasks started
> simultaneously — the gap shows ACES scheduling overhead.

---

## Slide 6: Results — Timing Breakdown (5:00–5:45)

> Looking at per-simulation timing, there's a clear bimodal distribution.
> Simulations either run to completion at around 10 seconds, or they end in
> under half a second.

> The box plot tells the story: penalty=0 runs take ~10 seconds because agents
> survive to timestep 1,000. Penalty=2 and penalty=3 cause instant mass
> extinction — all 250 agents die at timestep 1 because their metabolism cost
> exceeds the available sugar on the map.

> This was actually a calibration challenge. Our original design used penalties
> of 0, 2, and 5 — but at penalty 5, every single config collapsed instantly,
> giving us no data to compare. We backed down to 0, 2, and 3 which gives
> roughly 89% extinction at the higher penalties but still leaves some
> surviving combos.

---

## Slide 7: Results — Heatmaps (5:45–6:30)

> Here are the scientific heatmaps for the penalty=0 subset — the only
> configuration where we can actually observe framework differences.

> Each cell shows peak infection percentage for a given transmission chance
> and immune system length. Red is 100% infected, yellow is lower. All 8
> frameworks look nearly identical — this is an important finding. The disease
> physics dominate; ethical decision-making doesn't register.

> The sweet spot: high transmission plus short immune system guarantees
> universal infection. Low transmission plus long immune system keeps it
> around 5% peak. Transmission is the dominant knob — immunity has a smaller
> effect at the same transmission level.

---

## Slide 8: Results — Survival & Inequality (6:30–7:00)

> Survival rate stacked by penalty: penalty=0 is solid across all frameworks,
> near 100%. Penalty=2 and 3 are around 11% — only the parameter combos with
> the longest immune system length survive.

> For inequality — we compute delta Gini as the disease run's final Gini
> coefficient minus the baseline run's final Gini. A positive delta means
> the pandemic increased inequality; negative means it decreased.

> The box plot shows that for penalty=0, the mean delta is near zero — roughly
> the same inequality with or without pandemic. This is surprising. You might
> expect a pandemic to drive inequality up, but the metabolism penalty
> mechanism just subtracts a fixed amount from every agent's metabolism budget,
> so it affects everyone equally.

---

## Slide 9: Challenges — Runtime Selection (7:00–7:45)

> This is the distributed systems part. We evaluated several runtime options.

> SLURM job arrays were the simplest — ACES already has SLURM, you just write
> a submission script with #SBATCH directives. No extra tools to install.

> Drona or TAMULauncher are ACES-specific workflow engines good for DAGs but
> less portable to other clusters.

> MPI via mpirun would work but is overkill — our simulations have zero data
> dependencies between them, so there's no communication overhead to manage.

> CCTools with Makeflow is excellent for reproducible workflows — it tracks
> provenance, handles retries, and works on any cluster. But it requires a
> custom software install on ACES, which is extra friction for students.

> In the end, we chose SLURM for simplicity. The trade-off was that we had to
> hand-roll the batching and timing collection that CCTools would have done
> automatically.

---

## Slide 10: Challenges — Engineering Lessons (7:45–8:15)

> Several platform issues bit us during implementation.

> The QOS job limit was the biggest — ACES rejected our initial 656-task array.
> The fix was hybrid batching: 10 sims per task, 66 tasks total, set via
> SIMS_PER_JOB.

> Windows-to-Linux friction: os.path.join produces backslashes on Windows,
> which break on Linux. We forced forward-slash paths in jobs.csv.

> CRLF line endings from Windows editors caused sed and bash to fail on ACES.
> We had to run dos2unix-style cleanup after every transfer.

> $SLURM_SUBMIT_DIR doesn't point where you think — it resolves to a temp
> staging directory, not your project folder. We switched to an absolute path
> set via a PROJECT_DIR environment variable.

> And the disease penalty calibration — as mentioned, our original [0, 2, 5]
> sweep gave zero surviving runs at penalty=5, wasting 216 simulations. We
> recalibrated to [0, 2, 3] to get meaningful data.

---

## Slide 11: Future Work (8:15–9:00)

> Five directions we'd take this project.

> First: port to CCTools Makeflow for formal workflow provenance and automatic
> retry of failed jobs.
> Second: sweep more parameters — environmental knobs like resource peak
> locations, pollution rates, and agent genetic parameters.
> Third: multiple seeds per config for statistical power. With 30 seeds per
> combos, the 25x parallelism we demonstrated makes this tractable.
> Fourth: a live dashboard that monitors running jobs on ACES.
> Fifth: Docker or Singularity containers for zero-install cluster portability.
> Any cluster with a container runtime could run our pipeline.

---

## Slide 12: Thank You (9:00–9:15)

> To recap: SugarCluster is a TOML-driven middleware pipeline. 656 simulations,
> 20 ACES nodes, 2 minutes 24 seconds wall time, 25x parallelism. All code is
> in the SugarCluster directory. Happy to take questions.
