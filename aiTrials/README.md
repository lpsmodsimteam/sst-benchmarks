# Introduction

Scientists, engineers, and other users of high-performance computing (HPC)
systems often conduct large-scale parameter sweeps as part of simulation,
modeling, and data analysis workflows. Ensuring that such workflows are
well-documented and reproducible is highly desirable, as reproducibility is a
key tenet of both scientific and software engineering practice. It enables
independent verification, provides a record that can be revisited and referenced
later, and allows others to reliably build upon existing work.

In practice, however, users often rely on manual data-gathering approaches or
ad-hoc scripts to conduct these workflows. While such scripts can provide a
degree of implicit documentation, they frequently encode environment-specific
assumptions and dependencies, which can hinder portability and reproducibility.
This can result in failures when workflows are transferred across systems or
users, commonly summarized as an “it works on my machine” problem.

To address these challenges, reproducible workflow-management and
parameter-sweep frameworks have been developed. However, these systems are often
optimized for relatively static, production-oriented pipelines rather than
iterative exploratory analysis. As a result, many users perceive them as
infrastructure-heavy, requiring substantial configuration and workflow
specification before becoming productive.

At the same time, there has been widespread adoption of large language models
(LLMs) for code generation and software assistance. This raises the question of
whether it is possible to leverage these models to support lightweight,
exploratory computational workflows while still maintaining reproducibility and
strong documentation practices as first-class requirements.

In this work, we investigate this question by starting from a hand-written,
Jupyter-notebook-based workflow that was designed to be self-documenting and
highly reproducible. The workflow uses containers to improve portability and has
previously been used to study the scalability of SST on Cray EX systems. Using
GPT-5.3-Codex at medium setting through GitHub Copilot in Visual Studio Code, we
evaluate a series of “wishlist” prompts representing realistic workflow
adaptations and extensions that HPC users may wish to perform during exploratory
computational studies.

# The original example workflow and workflows module

The original workflow that we adapt using our wishlist prompts is in
`scale_model_size.ipynb`. This notebook runs a single-node SST scaling study
using the [phold](https://github.com/hpc-ai-adv-dev/sst-benchmarks) benchmark.
It downloads a containerized SST build, clones and compiles the benchmark, then
launches a series of jobs with increasing numbers of simulation components
(e.g., 10k–50k). After the runs complete, it extracts timing data from the
output logs, saves results to a CSV, and plots total simulation duration vs.
component count. The notebook relies on a shared `utils/workflows.py` module
that factors out common tasks (container management, job launch, log parsing,
etc.) used across these workflows. Most of the wishlist prompts result in
changes to the notebook itself, though some also required modifications to this
shared module as well.

# The wishlist prompts

We apply the following prompts to the notebook. For each prompt we give a
camel_cased name that we use as the filename for the associated workbook where
we apply the prompt.  These prompts are intentionally informal and loosely
specified. The goal is not to demonstrate effective prompt engineering, but to
reflect the kinds of casual, off-the-cuff requests a user might make during
real-world exploratory work.

### Changing data gathering parameters:

- [**change_bounds**](00_change_bounds/change_bounds.ipynb): Change this to to run trials between 1 and 10 million components. Generate 5 data points.
- [**change_sst_version**](01_change_sst_version/change_sst_version.ipynb): Change this to run using SST version 15.1.
- [**change_benchmark**](02_change_benchmark/change_benchmark.ipynb): Change the benchmark to use GOL.

### Changing data presentation:

- [**change_graph_presentation**](03_change_graph_presentation/change_graph_presentation.ipynb): Modify the graph produced at the end to be titled 'SST PHOLD Scaling', with the xlabel as 'Number of devices' and the ylabel as 'Delay (s)'. Make the line thick and red make the individual data points blue circles.
- [**change_graph_datasource**](04_change_graph_datasource/change_graph_datasource.ipynb): Rather than showing the total execution time show the resulting total memory usage.
- [**fit_linear_model**](05_fit_linear_model/fit_linear_model.ipynb): Fit a simple linear model to the data, report the slope and R-squared, annotate the plot with the fit results.

### Enhancing the existing workflow:

- [**add_documentation**](06_add_documentation/add_documentation.ipynb): Read the workflow and come up with a summary description, put it into a README cell at the top of the notebook.
- [**make_testing_infrastructure**](07_make_testing_infrastucture/make_testing_infrastructure.ipynb): I would like to use this workflow to generate a regression tests. How can I do that?
- [**add_additional_logging**](08_add_additional_logging/add_additional_logging.ipynb): I would like to log more data about the environment I produce these runs in. Augment the workflow to gather data that would be useful for reproducing it.

### Changing underlying technology:

- [**run_bare_metal**](09_run_bare_metal/run_bare_metal.ipynb): rather than using containers can you download SST and run it on the bare metal?

### Producing more complex workflows given a simple workflow:

- [**make_sst_ver_comparison_workflow**](10_make_sst_ver_comparison_workflow/make_sst_ver_comparison_workflow.ipynb): Structure this workflow to run twice once using SST version 15.1 and once using SST version 15.2. Present both results in a single gaph that I can use to compare the relative performance.
- [**make_weak_scaling_workflow**](11_make_weak_scaling_workflow/make_weak_scaling_workflow.ipynb): Produce an SST weak scaling workflow. Define a global parameter that I can use to set a fixed number of components per node.
- [**make_debug_overhead_workflow**](12_make_debug_overhead_workflow/make_debug_overhead_workflow.ipynb): I want to measure how much overhead occurs when using SST's debugger and attaching watchpoints. For each trial, produce a debugger replay script that will add watchpoints to all components then measure the total execution time when we run SST and have it replay this script. Present the results in a plot with two lines, one showing the time with the watchpoints attached and one without.
- [**make_artifical_work_workflow**](13_make_artifical_work_workflow/make_artifical_work_workflow.ipynb): I would like to evaluate the effect of adding in artifial work. Have PHOLD launch onto 8 nodes and alter the amount passed to its --componentCompute parameter. Pass values ranging from 0 to 1 million with 5 evenly spaced points.


## Trial-by-Trial Summary

The table below gives a compact view of how Copilot performed applying each
wishlist prompt to the `scale_model_size.ipynb` notebook.  The "Prompt Summary"
column, gives a short description of the prompt (for the full text see the
section above).  The  "Did it functionally work?" column evaluates, without
examining the resulting source-code, if when run the resulting notebook appears
to satisfy the prompt.  The "Critique Summary" column elaborates more, and
comments on stylistic decisions Copilot made.  For more detailed critique see
the individual notebook files or [all_trials_diff.html](all_trials_diff.html),
which contains the critique text for each notebook along with their diffs.

Of the 14 trials, at a strictly functional level, ignoring code style and
maintainabilty, there were 9 cases that passed.  Of the remaining cases, I
believe most of them could be made to work with minimal hand-made edits or
additional followup prompts with added context.


| Notebook | Prompt Summary | Did it functionally work? | Critique summary |
|---|---|---|---|
| `00_change_bounds` | Change sweep range | Yes | Correctly made the update but did so in an area marked "DO NOT MODIFY". |
| `01_change_sst_version` | Run using SST version 15.1 | No, but easily fixable | Updated the right variable to the wrong value, applied change in wrong place again, and model churned before settling. |
| `02_change_benchmark` | Switch benchmark to GOL | No, but worked with added context | First attempt failed without context; second succeeded when additional context was provided, including an argument inference from source. Again, changes were made in the "DO NOT MODIFY" area.|
| `03_change_graph_presentation` | Restyle plot (title, axis labels, line/point styling) | No got stuck in a loop, worked with a different model | Would hang with GPT-5.3, succeeded with GPT-5.4.  Also made an unrequested stylistic change, inlining the use of a variable that I had previously separated out. |
| `04_change_graph_datasource` | Plot memory usage instead of execution time | Yes | Succeeded by pulling in context from workflows module. Even though it wasn't prompted to, it made the made the output more readable by converting bytes to GiB, but it also added unrequested defensive checks that in this case I find heavier-than-necessary. |
| `05_fit_linear_model` | Add linear fit, report slope and R², annotate plot | Yes | Correct implementation; self-validation failed only because no real data had been gathered yet. |
| `06_add_documentation` | Generate a README cell summarizing the workflow | Yes | Good first draft with sensible structure; still needs human review for terminology precision and local convention alignment. |
| `07_make_testing_infrastucture` | Add regression testing infrastructure | Yes | Produced functional regression scaffolding and useful reporting; still needs threshold tuning and some simplification/refactoring decisions. |
| `08_add_additional_logging` | Log environment data to support reproducibility | Yes | Initial run hung, retry succeeded. Resulting logging structure and command-capture approach are useful and extensible. |
| `09_run_bare_metal` | Download and run SST bare metal instead of using containers | Arguably yes, although it ran into a file-system bug that I've also encountered when making manual edits. | Strong result despite long run/reprompt. Good structural adaptation; observed execution issues were environment-specific rather than code-design flaws. |
| `10_make_sst_ver_comparison_workflow` | Compare two SST versions in a single plot | No, but easily fixable | Good overall structure and output handling, but required manual fixes (tag format and per-version build correctness concerns). |
| `11_make_weak_scaling_workflow` | Build a weak-scaling workflow with configurable components-per-node | Yes | Reasonable implementation with useful structural updates; sizing algorithm differs from intended method and can degrade for some inputs. |
| `12_make_debug_overhead_workflow` | Measure watchpoint overhead, plot with/without comparison | No | Promising first draft with the right high-level structure, but not correct as produced: it inferred replay-file support and paired runs, yet guessed invalid PHOLD component names/watch expressions and added avoidable duplication. Likely recoverable with additional context and follow-up edits. |
| `13_make_artifical_work_workflow` | Sweep `--componentCompute` parameter across 8 nodes | Yes, after fixing my human error when prompting it. | Partially successful, but undermined by prompt and placement issues. Copilot set up the 8-node sweep structure, but used the user-requested wrong flag name, placed new core parameters in the override section, and left an obsolete sizing parameter behind. |
| `14_infer_from_data` | Extrapolate runtime to 5M and 5B components | Yes | Strong success. It fit a linear model to the gathered data, reported plausible estimates for 5M and 5B components, and included an appropriate warning about the risks of extrapolating far beyond the measured range. |
