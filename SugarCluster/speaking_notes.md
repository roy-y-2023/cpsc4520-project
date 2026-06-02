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
> each. We used seed 12345 and collected per-timestep metrics in JSON.

---

## Slide 4: Architecture (1:30–3:30)

> This is the middleware pipeline. Everything is driven by a single TOML file
> called sweep.toml. It declares the parameter knobs and their values. No
> hard-coded Python — adding a new knob means adding one line of TOML.

> generate_configs.py reads that TOML, computes the cartesian product, and
> emits 1,520 minimal JSON config files plus a jobs.csv manifest. "Minimal"
> means each config only contains the keys that differ from Sugarscape's
> internal defaults — this keeps configs small and avoids cascading when
> Sugarscape's defaults change upstream.

> The submit.slurm script dispatches these as a SLURM job array. But we
> couldn't submit 1,520 array tasks because ACES has a QOS limit on job array
> size. So we bundled 30 simulations into each task — 51 tasks total instead
> of 1,520. That's the SIMS_PER_JOB parameter, configurable via an environment
> variable.

> On ACES, each task runs run_batch.py which loops through its 30 configs,
> records per-simulation timing, and writes a per-batch timing CSV. After all
> jobs finish, we pull the data back with rsync — 1,520 JSON logs plus 51 timing
> files.

> Back on our local machine, aggregate.py parses everything into a single
> run_summary.csv. analyze.py computes grouped statistics. And plots.py
> generates the figures you'll see in the results section. The entire pipeline
> is automated — you change sweep.toml and re-run the scripts.

---

## Slide 5: Distributed Execution Details (3:30–5:00)

> Here's what the actual execution looked like on ACES. This is real data
> pulled from SLURM's sacct command for job array 1730737.

> 51 tasks across 11 different ACES nodes. Each task runs up to 30 simulations
> sequentially. Node distribution is shown here — node loading ranged from 1
> task up to 12 tasks on the most active node.

> Key numbers: total wall time — 5 minutes and 16 seconds. That's the real
> clock time from first task start to last task end. The serial equivalent —
> if we ran all 1,520 sims one after another on a single core — would have been
> 6,599 seconds, or 110 minutes. So we got a 20.9x speedup.

> Throughput: over 17,300 simulations per wall-clock hour. Overhead is 6.0% —
> the Python interpreter startup and config loading costs about 8.6 seconds
> per batch of 30 sims. Everything else is actual simulation work.

> The cumulative completion plot visualizes this: the solid blue line is the
> real execution — you can see it takes about 76 seconds for the first few
> tasks to start completing, then it accelerates as more nodes get allocated.
> The dashed red line is the theoretical best case if all 51 tasks started
> simultaneously — the gap shows ACES scheduling overhead.

---

## Slide 6: Results — Timing Breakdown (5:00–5:45)

> Looking at per-simulation timing, there's a clear bimodal distribution.
> Simulations either run to completion at around 24.4 seconds for penalty=0 (or
> around 5.2 seconds for surviving runs with penalty > 0), or they end in
> under half a second.

> The box plot tells the story: penalty=0 runs take ~24.4 seconds because agents
> survive to timestep 1,000. Penalty levels from 0.1 to 3.0 cause instant mass
> extinction — all agents die at timestep 1 because their metabolism cost
> exceeds the available sugar on the map.

> This was actually a calibration challenge. Our original design used penalties
> of 0, 2, and 5 — but at penalty 5, everyone died instantly. We expanded our
> sweep to study intermediate penalties including 0.1, 0.25, 0.5, and 1.0.
> Interestingly, even a tiny penalty of 0.1 leads to the exact same 89%
> extinction rate at timestep 1, highlighting how thin the resource buffer is.

---

## Slide 7: Results — Heatmaps (5:45–6:30)

> Here are the scientific heatmaps for the penalty=0 subset — the only
> configuration where we can actually observe framework differences.

> Each cell shows peak infection percentage for a given transmission chance
> and immune system length. Red is 100% infected, yellow is lower. All 8
> frameworks look nearly identical — this is an important finding. The disease
> physics dominate; ethical decision-making doesn't register.

> Because of our scaled-up disease initialization with 25 starting diseases and
> 10 per agent, almost all agents start infected. This pushes the peak infection
> percentage near 100% for almost all parameters, only dropping to 98.4% with
> max immunity. The initial pandemic load simply overwhelms any transmission
> or immunity variations.

---

## Slide 8: Results — Survival & Inequality (6:30–7:00)

> Survival rate stacked by penalty: penalty=0 is solid across all frameworks,
> near 100%. Penalties from 0.1 to 3.0 are around 11% — only the parameter combos
> with the longest immune system length and shortest disease tag survive.

> For inequality — we compute delta Gini as the disease run's final Gini
> coefficient minus the baseline run's final Gini. A positive delta means
> the pandemic increased inequality; negative means it decreased.

> The box plot shows that for penalty=0, the mean delta Gini is around -0.01 —
> wealth inequality actually slightly decreases under the pandemic, with Gini
> converging to ~0.29 compared to a baseline of 0.3. The flat metabolic load
> acts as a compression mechanism on the wealth distribution rather than
> exacerbating inequality, though the effect is small.

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

> The QOS job limit was the biggest — ACES rejected our initial 1,520-task array.
> The fix was hybrid batching: 30 sims per task, 51 tasks total, set via
> SIMS_PER_JOB.

> Windows-to-Linux friction: os.path.join produces backslashes on Windows,
> which break on Linux. We forced forward-slash paths in jobs.csv.

> CRLF line endings from Windows editors caused sed and bash to fail on ACES.
> We had to run dos2unix-style cleanup after every transfer.

> $SLURM_SUBMIT_DIR doesn't point where you think — it resolves to a temp
> staging directory, not your project folder. We switched to an absolute path
> set via a PROJECT_DIR environment variable.

> And the disease penalty calibration — we expanded the sweep to include intermediate
> values [0.1, 0.25, 0.5, 1.0] alongside [2.0, 3.0]. Strikingly, even a tiny penalty
> of 0.1 led to the same 89% extinction rate at timestep 1.

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

> To recap: SugarCluster is a TOML-driven middleware pipeline. 1,520 simulations,
> 11 ACES nodes, 5 minutes 16 seconds wall time, 20.9x parallelism. All code is
> in the SugarCluster directory. Happy to take questions.
