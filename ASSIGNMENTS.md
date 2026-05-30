# Final Project -- CPSC 4520 Distributed Systems
Due date: 5/31/2026

## 1 Top Level Overview of the Final Project
In a team 3 students, you will look into the provided (currently serial) application and come up with a project proposal to scale it up to a distributed application, develop your project, and prepare a final presentation of what you created and any relevant results. For those interested publishing a research paper during your time as a student, this would be an excellent opportunity to try something novel and interesting. Once your proposal is deemed sufficient, you will get the green light to begin your project.

## 2 Scaling Up a Societal Simulation
The [Sugarscape](https://github.com/nkremerh/sugarscape) societal simulation has been used for decades to model and analyze emergent social behaviors such as tribe formation, market development, socio-economic inequality, and more. It was first introduced in the book *Growing Artificial Societies: Social Science from the Bottom Up (GAS)*. A recent implementation in Python 3 provides all the functionality described in GAS, verifies the examples provided in the book, and provides extensibility for new features. Details of this version of Sugarscape can be found in the provided paper on the assignment Canvas page.

One of these features is the implementation of different decision models which affect the simulated agents' behaviors. The data collection process for Sugarscape involves running each of the implemented decision models for a certain number of timesteps (typically around 2,000 timesteps). This process is repeated for 100 randomly generated seeds. A seed is an integer used to populate the random number generator, and it has profound impacts on the starting state of the simulation as well as the outcomes of every pseudorandom event that occurs. This all leads to 100 seeds * # of decision models total simulation runs, each for 2,000 timesteps. Because of the long duration of an individual simulation run, the more complex decision models can take many hours to complete.

The current data collection process has some limited, entirely local parallelism. A user-configurable number of simultaneous simulations can be run, but the upper limit to this scalability is quickly reached on commodity hardware. Additionally, the runtime memory footprint of some of the more complex decision models can range up to 2GB for a single run. Running multiple of these simulations quickly leads to memory exhaustion (and failure in machines without a swap file or partition). As a final complication, the resulting dataset is a collection of JSON log files. The total space consumed depends on the number of timesteps, but running for 2,000 timesteps across all runs leads to a collection of log files in single digit gigabytes. In modern systems, this is a negligible storage concern, but it is something to keep in mind in case it becomes relevant for your project.

## 3 Running Sugarscape
Full details on how to run the software locally can be found in the README in the [GitHub repository](https://github.com/nkremerh/sugarscape). The simulation optionally reads a configuration file (written in JSON) to set up the environment and agent behaviors. Without this config file, the simulation provides a default configuration with nearly all the interesting features turned off. Also by default, the program runs with a GUI enabled. This requires direct input from the user to begin the simulation whereas headless mode starts the simulation without a GUI and begins it as soon as setup is complete. The GUI can be turned off in the configuration by setting `headlessMode` to true (note the capitalization).

A configuration file is already provided in the repository with all features of the software listed. You are encouraged to get a sense of what all is possible with Sugarscape. However, you should probably start by seeing what it looks like out-of-the-box. To see an example of the simulation with nearly every feature enabled, you can simply run:

`make run`

## 4 Project Proposal
Your project must be approved by the instructor before you can begin work. Likewise, no team can have the same project, so proposals will be reviewed and approved on a first come, first served basis. There is an incentive to get your proposal submitted early to maximize the chance that your initial project idea gets accepted. Some generic project pathways to jumpstart your brainstorming include (but are not limited to): scaling up the simulation data collection process, testing a specific feature (or set of features) at scale, or performing a specific experiment at scale. The proposal consists of 4 sections: an introduction, project idea, experimental methodology, and anticipated results.

### 4.1 Introduction
The introduction serves as an executive overview of the project proposal. Within 1-2 paragraphs, describe the project (the what), its purpose (the critical why), the proposed methodology (the how), and anticipated results/conclusions. This should tee up the remainder of the proposal.

### 4.2 Project Idea
The project idea section is the core of the proposal. It should include some depth about project details: what exactly you are wanting to do, why it is interesting/important, and a rough timeline of the project identifying key deliverables (such as when you anticipate data collection to start, when the presentation slides will be complete, etc.). This should make up 4-5 paragraphs of your proposal.

### 4.3 Experimental Methodology
Your project's experimental methodology is a description of how you will go about gathering results. Depending on the nature of your project, this could look quite different from other teams. You should include plans to run the simulation at scale (e.g. technologies and platforms used, execution sites - like [OSG](https://osg-htc.org/), etc.). Also include what your results look like (in terms of the kinds of data you need to collect) and how you will interpret that data (e.g. performing some analysis after collection). This section should be 2-3 paragraphs.

### 4.4 Anticipated Results
The anticipated results section should describe the hypothesis of your project. Based on your project idea and experimental methodology, describe what you believe is the most likely result(s). Also include brief discussion of factors which could lead to deviations from your hypothesis. This section should include how you intend to present the data as well (e.g. types of charts) and should be 2-3 paragraphs.

## 5 Doing the Project
This project is a chance for you to flex your technical skills. We have only had time in the course to recreate and utilize a small subset of the distributed systems out there. This would be an excellent opportunity to try something new!

While the development of your project is up to you, here are a few commonsense recommendations about where you could do that development and testing:

### 5.1 Running on Supercomputers and Clusters
The supercomputing resources your group assigned to is [ACES](https://hprc.tamu.edu/aces/).

### 5.2 Running on Local Servers
While OSG and the other resources that make up ACCESS are well-suited for a variety of distributed applications, your project may not be a good fit for what they provide. If that is the case (e.g. running a persistent service like a web server), you may use [cs1.seattleu.edu](ssh://cs1.seattleu.edu) and [cs2.seattleu.edu](ssh://cs2.seattleu.edu) for your development and testing. Since there are only two servers hosted on campus, you are encouraged to also include your personal machines in the pool of compute resources utilized by your project. Additionally, you will need to discuss your resource needs for the two servers with Renny Philipose. Depending on your use case, he may not be able to accommodate your request.

## 6 Project Presentation
The research project will culminate in an 8 minute presentation from each team. Your presentation should include an overview of the project goal(s), briefly describe the technology stack used (including at least one diagram of the application's software architecture), showcase results from your project, and end with a brief discussion of challenges encountered, lessons learned about distributed systems, and any interesting avenues for future work (even if you do not intend to do that work yourself). Every team member must speak during the presentation, and speaking time should be (roughly) equal.

The presentation consists of a slideshow and talking. You are encouraged to use the board for drawing if that is useful, but this is not required. Additionally, you should refrain from showing the class a live demo of your system in action unless the following two conditions are met: the demo is practically guaranteed to produce an interesting, non-failing result and the demo does not take up more than 2 minutes of the presentation. If you decide to show a demo, you must speak over it rather than simply letting it unfold for us to see. Tell us what is happening and what we should be looking for in the results.

## 7 General Hints
* Depending on your project, it may be worth getting in touch with the [Cooperative Computing Lab](https://ccl.cse.nd.edu/). While we use [Makeflow](https://ccl.cse.nd.edu/software/makeflow/) and [Work Queue](https://ccl.cse.nd.edu/software/workqueue/) in the course, there is other software in [CCTools](https://ccl.cse.nd.edu/software/) that could be used to scale up the simulation, and they may be able to help you select the right tools. Plus, your project idea may be an interesting first step for one of their PhD students and you to continue after the quarter is done.
* As with all course projects, it is better to start early than to start late. This is fairly hands-off when it comes to instructor supervision, so the success of your project is in your hands. When it comes time to present in class, you should be proud to showcase your work to your peers!
* Since this is a team project, there is an acknowledgement that sometimes teams are not aligned in their goals or the division of work is unequal. If there are issues with communication or followthrough in your team, you are encouraged to let the instructor know as soon as possible. At the end of the quarter, you will be provided an opportunity to provide feedback about your other team members if you do not believe the amount of work completed per member was (roughly) equal and fair.

## 8 Turn-In
Your project proposal should be emailed to the instructor as a PDF when you are ready to have it reviewed. Your project must have a README document explaining how to install and run it. Additionally, it is strongly preferred your project has a Makefile to automate installation and deployment if practical.

You must turn in all relevant code and data related to your project as a zipped archive called `final.zip`. If the combined size of your uncompressed code and data is greater than 2GB, make a note of the uncompressed size on the Canvas assignment as a comment. Your presentation slides should be submitted as a PDF with the rest of your project materials.

## 9 Rubric
| Criteria | Rating 1 | Rating 2 | Rating 3 | Rating 4 | Total Points |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Code: Correctness** | Evidently Correct<br>15 pts | Very Likely Correct<br>10 pts | Unlikely Correct<br>5 pts | Broken/Unable to Verify Correctness<br>0 pts | /15 pts |
| **Code: Documentation** | Good Documentation<br>5 pts | Acceptable Documentation<br>3 pts | Poor Documentation<br>1 pt | No/Very Poor Documentation<br>0 pts | /5 pts |
| **Code: Style** | Good Style<br>5 pts | Acceptable Style<br>3 pts | Poor Style<br>1 pt | Very Poor Style<br>0 pts | /5 pts |
| **Presentation: Overview** | Detailed Overview<br>5 pts | Acceptable Overview<br>3 pts | Vague Overview<br>1 pt | No/Poor Overview<br>0 pts | /5 pts |
| **Presentation: Results** | Evidently Accurate Results<br>5 pts | Likely Accurate Results<br>3 pts | Improbably Accurate Results<br>1 pt | Evidently Inaccurate Results<br>0 pts | /5 pts |
| **Presentation: Obstacles** | Detailed Discussion<br>5 pts | Acceptable Discussion<br>3 pts | Vague Discussion<br>1 pt | No/Poor Discussion<br>0 pts | /5 pts |
| **Presentation: Lessons Learned** | Detailed Discussion<br>5 pts | Acceptable Discussion<br>3 pts | Vague Discussion<br>1 pt | No/Poor Discussion<br>0 pts | /5 pts |
| **Presentation: Style** | Good Style<br>5 pts | Acceptable Style<br>3 pts | Poor Style<br>1 pt | Very Poor Style<br>0 pts | /5 pts |
