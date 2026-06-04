# Speaking Notes — SugarCluster Presentation (Revised)

## Slide 1: Title (0:00–0:20)

> Hi everyone, I'm presenting SugarCluster. It's middleware we built to run thousands of simulations on Texas A&M's ACES supercomputer. This is for CPSC 4520, and all the code is in the SugarCluster folder.

---

## Slide 2: Overview & Research Questions (0:20–1:10)

> First, a quick intro to Sugarscape. It's a simulation where agents move around a grid, collect sugar and spice, catch diseases, trade, reproduce, and die. It's a great model for studying how diseases spread.

> We wanted to answer two main questions. First: which disease settings make infections spread faster or slower? Second: do ethical frameworks—like altruism or egoism—affect how pandemics impact wealth inequality?

> To test this, we ran over 2,100 simulations, varying five disease settings across eight ethical frameworks. We ran the whole sweep twice—once with standard SLURM job arrays and once with TAMULauncher—so we could compare the two approaches.

---

## Slide 3: Architecture (1:10–2:00)

> Our middleware is fully automatic. It starts with a single TOML file that defines all the parameters. No hard-coded values in Python—just add a line to the TOML file.

> A script reads that file, generates 2,168 individual config files, and creates a job manifest. Then we submit the runs using either SLURM or TAMULauncher. When they finish, another script pulls all the results and timing data into one summary file. Finally, we generate plots.

---

## Slide 4: Challenges: Too Many Ways to Run a Job (2:00–2:40)

> One early challenge was figuring out how to run all these simulations. ACES gives you at least five different options, and it's not obvious which one is best.

> SLURM job arrays seem simple, but there are limits on how many you can submit. TAMULauncher is specific to ACES and not well-documented. Other options like Drona are GUI-based, MPI has too much overhead, and Work Queue adds external dependencies.

> We decided to start with SLURM—it's the most familiar—and see how far we could push it.

---

## Slide 5: Approach 1: SLURM Job Array (2:40–3:30)

> Here's our first approach. We used a SLURM job array. This slide shows real data from ACES for job 1741358.

> The main issue was the limit on array size. We couldn't submit all 2,168 simulations as separate tasks. So we bundled multiple simulations into each task—about 28 per job. That gave us 78 active tasks across 13 nodes.

> It worked—finished in about 12 minutes—but the batching logic was complicated, and a global concurrency cap limited how much we could parallelize.

---

## Slide 6: Approach 2: TAMULauncher (3:30–4:20)

> Our second approach was TAMULauncher. Instead of bundling simulations, we wrote one command per simulation into a text file—2,168 lines—and let TAMULauncher handle the rest.

> This approach avoided the array-size limit entirely. It also supports checkpointing, so if we resubmitted, it would skip already-completed runs.

> We used 20 nodes with 12 tasks each, giving us 240 concurrent slots. The whole sweep finished in just under two and a half minutes. That's over 150 times faster than running serially, with a throughput of about 53,000 simulations per hour.

---

## Slide 7: SLURM vs TAMULauncher: Head-to-Head (4:20–5:05)

> Comparing the two, TAMULauncher is clearly faster—about 5 times faster in wall time. It also handles the array-size limit automatically.

> But SLURM is more portable—it works on almost any cluster. TAMULauncher is specific to ACES.

> We recommend TAMULauncher for large sweeps where speed matters, and SLURM when portability or queue wait times are more important.

---

## Slide 8: Results: Distributed Systems (5:05–5:35)

> This plot shows how the simulations completed over time. The blue line is SLURM—you can see the steps where batches of 28 finished together. The green line is TAMULauncher—it's smoother and finishes much earlier, at about two and a half minutes.

---

## Slide 9: Results: Timing Breakdown (5:35–6:05)

> Looking at individual simulation durations, they're all very consistent—around 10.4 seconds. Baseline runs without disease are slightly faster.

> Because agents start with no diseases, there's no early mass extinction. Everyone survives to the end, so all simulations take about the same time.

---

## Slide 10: Results: Scientific Findings (6:05–6:35)

> Here are the infection heatmaps for the zero-penalty group, across all eight ethical frameworks. The cells show peak infection rates.

> High transmission with low immunity leads to 68% infection. Low transmission with high immunity keeps it down to 2%.

> Interestingly, all eight ethical frameworks look nearly identical. The disease physics dominate the ethical behavior.

---

## Slide 11: Results: Survival by Penalty (6:35–6:55)

> This shows survival rates by disease penalty. Everyone survived—100% across all penalty levels. Because agents start healthy, even with high penalties, the population doesn't collapse early.

> Ethics don't change survival outcomes here—every framework shows the same result.

---

## Slide 12: Results: Inequality (Gini Coefficient) (6:55–7:15)

> We also looked at wealth inequality using the Gini coefficient. Under disease, inequality decreases slightly—by about 0.008.

> The disease's metabolic penalty acts as a mild wealth compressor, but the effect is small. Economics matter more than ethics here, but the overall impact is subtle.

---

## Slide 13: Challenges: Engineering Lessons (7:15–7:45)

> We hit a few engineering hurdles along the way.

> First, a misleading log message made us think TAMULauncher was crashing—it turned out to be normal shutdown behavior.

> Second, the SLURM submit directory pointed to a temporary folder, not our project, so we had to use absolute paths.

> Third, Windows path separators broke on Linux, so we forced forward slashes.

> Fourth, Windows line endings caused silent failures, so we enforced Unix-style line endings.

> Finally, parsing thousands of output files was slow, so we parallelized it.

---

## Slide 14: Future Work (7:45–8:15)

> For future work, we'd like to explore more parameters—like environmental settings and trading behavior.

> We could also run multiple seeds per configuration for better statistical confidence. At our current speed, that's totally feasible.

> Other ideas include a live dashboard for monitoring jobs, automatic tuning of task density, and making the middleware work on other clusters with minimal changes.

---

## Slide 15: Thank You / Questions (8:15–8:30)

> To wrap up: SugarCluster is a TOML-driven pipeline that ran 2,168 simulations across two different engines. SLURM took about 12 minutes, TAMULauncher just over 2.

> All the code is in the SugarCluster directory. Thanks for listening—I'm happy to take questions.

---

*Repository: github.com/roy-y-2023/cpsc4520-project · SLURM job: 1741358 · TAMULauncher job: 1741350*