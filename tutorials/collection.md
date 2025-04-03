# Collecting Evaluation Tasks for Kotlin-Bench
Aman Gottumukkala &bull; March 25, 2025

In this tutorial, we explain how to use the Kotlin-Bench repository to collect evaluation task instances from GitHub repositories.

<div align="center">
    <img style="width:70%" src="../assets/collection.png">
</div>

## ⛏️ Collecting Candidate Tasks

Supply the *repository name(s)* and *logging folders* as arguments to the `run_get_tasks_pipeline.sh` script, then run it like so:
```bash
cd swebench/collect && ./run_get_tasks_pipeline.sh 
```

At this point, for a repository, you should have...
* A `<repo name>-prs.jsonl` file containing all the repository's PRs.
* A `<repo name>-task-instances.jsonl` file containing all the candidate task instances.

## 📙 Specify Execution Parameters

This step is the most manual of all parts.
To create an appropriate execution environment for task instances from a new repository, you must do the following steps:
* Assign a repository-specific *version* (i.e. `1.2`) to every task instance.
* Specify repository+version-specific installation commands in `harness/constants.py`.

### Part A: Versioning
Determining a version for each task instance can be accomplished in a number of ways, depending on the availability + feasability with respect to each repository.
* Scrape from code: A version is explicitly specified in the codebase (in `gradle.properties`, etc.).
* Scrape from web: Repositories with websites (i.e. [xarray.dev](https://xarray.dev/)) have a "Releases" or "What's New" page (i.e. [release page](https://docs.xarray.dev/en/stable/whats-new.html) for xarray). This can be scraped for information.
* Build from code: Sometimes, version-related files (i.e. `_version.py`) are purposely omitted by a developer (check `.gitignore` to verify). In this case, per task instance you can build the repository source code locally and extract the version number from the built codebase.

Examples and technical details for each are included in `/versioning/`. Please refer to them as needed.

### Part B: Installation Configurations
Per repository, you must provide installation instructions per version. In `constants.py`...
1. In `MAP_VERSION_TO_INSTALL`, declare a `<repo owner/name>: MAP_VERSION_TO_INSTALL_<repo name>` key/value pair.
2. Define a `MAP_VERSION_TO_INSTALL_<repo name>`, where the key is a version as a string, and the value is a dictionary of installation fields that include the following information:
```python
{
    "jdk_version": "", # Example: 17.0.9-tem
    "install": "", # cp gradle.properties-example gradle.properties
}
```

### Part C: Test Configuration
You must also provide test instructions per version. In `constants.py`

1. In `MAP_REPO_TO_TEST_FRAMEWORK_KT`, declare how to invoke tests for that specific repo.

2. Define a `MAP_VERSION_TO_INSTALL_<repo name>`, where the key is a version as a string, and the value is a dictionary of installation fields that include the following information:

Example:
```python
{
    "ankidroid/Anki-Android": "./gradlew :AnkiDroid:testPlayDebugUnitTest"
}
```

We currently only support running a single base test command per repo. Feel free to open a PR that supports templating and running of tests from multiple modules, including androidTests

## ⚙️ Execution-based Validation with [Modal](https://modal.com/)
Congrats, you got through the trickiest part! It's smooth sailing from here on out.


Execution-based validation ensures task instances meet specific criteria:

- Tests fail before applying the code patch.
- Tests pass after applying the code patch.

This validation approach creates a controlled evaluation environment where an AI model must implement missing code based on issue descriptions and PR context. We can definitively measure success by verifying that tests that initially fail will pass after the AI's implementation.

> Code patch refers to any non-test code in a PR

> TODO: Only consider tests that fail AND compile before applying code patch. There were too few Kotlin task instances available on Github with our current methodologyso we made the tradeoff to consider tests that didn't compile as well.

The `engine_validation_modal` file filters task instances, confirming that each:
- Fails tests before applying the patch
- Passes tests after applying the patch
- This process yields a refined, high-quality dataset suitable for evaluating AI performance.

Running multiple Gradle builds and tests for many task instances locally is inefficient and time-consuming. To efficiently handle this validation process, we utilized Modal to parallelize the workload. The script `engine_validation_modal.py` concurrently initializes and runs Gradle tests across hundreds of containerized Android and Kotlin projects, significantly reducing the validation time.

### Run Concurrent Execution-based Validation on Modal

Run `modal run swebench/harness/engine_validation_modal.py` and supply the following arguments:
* `instances_path`: Path to versioned candidate task instances
* `log_dir`: Path to folder to store task instance-specific execution logs
* `temp_dir`: Path to directory to perform execution
* `verbose`: Whether to print logging traces to standard output.

> In practice, you may have to iterate between this step and **Installation Configurations** a couple times. If your instructions are incorrect/under-specified, it may result in candidate task instances not being installed properly.

## 🔄 Convert to Task Instances
At this point, we now have all the information necessary to determine if task instances can be used for evaluation with SWE-bench, and save them if they do.

We provide the `validation.ipynb` Jupyter notebook provided in this folder to make the remaining steps easier.
At a high level, it enables the following:
* In **Monitor Validation**, check the results of the `./run_validation.sh` step.
* In **Get [FP]2[FP] Tests**, determine which task instances are non-trivial (solves at least one test)
* In **Create Task Instances `.json` file**, perform some final preprocessing and save your task instances to a `.json` file.

Thanks for reading! If you have any questions or comments about the details in the article, please feel free to follow up with an issue.

## Upload to HuggingFace (Optional)

TODO

## 🚀 Next Steps

Congratulations! You now have a validated set of task instances ready for AI evaluation.

The next step is to [generate AI predictions](predictions.md) for your task instances and evaluate the results.