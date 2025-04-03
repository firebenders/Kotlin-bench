import logging, os, platform, subprocess, json
import time

from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    DEFAULT_CONDA_LINK,
    INSTALL_FAIL,
    INSTALL_PASS,
    INSTALL_TIMEOUT,
    KEY_INSTANCE_ID,
    KEY_MODEL,
    MAP_REPO_TO_INSTALL,
    MAP_REPO_TO_TEST_FRAMEWORK_KT,
    MAP_VERSION_TO_INSTALL,
    RESET_FAILED,
    TESTS_FAILED,
    TESTS_PASSED,
    TESTS_TIMEOUT,
    TESTS_ERROR,
    PatchType,
)
from swebench.harness.utils import (
    clone_repo,
    get_test_directives,
    get_android_test_cmd,
)
from tempfile import TemporaryDirectory
from traceback import format_exc

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger_testbed = logging.getLogger("testbed")


class LogWrapper:
    def __init__(
        self,
        log_file: str,
        logger: logging.Logger = None,
        prefix: str = None,
    ):
        self.log_file = log_file
        self.logger = logger
        self.prefix = prefix

    def write(
            self,
            message: str,
            mode: str = "a",
            level: int = INFO):
        with open(self.log_file, mode) as f:
            log = f"{self.prefix} {message} \n" if self.prefix \
                is not None else f"{message} \n"
            f.write(log)
        if self.logger is not None:
            self.logger.log(level, message)


class ExecWrapper:
    def __init__(
        self,
        subprocess_args: dict = None,
        logger: LogWrapper = None,
    ):
        self.logger = logger
        if subprocess_args is None:
            self.subprocess_args = {}
        else:
            self.subprocess_args = subprocess_args

    def __call__(self, cmd, raise_error=True, **kwargs):
        try:
            if isinstance(cmd, list):
                self.logger.write(f"Command: {' '.join(cmd)}", level=DEBUG)
            else:
                self.logger.write(f"Command: {cmd}", level=DEBUG)
            combined_args = {**self.subprocess_args, **kwargs}
            self.logger.write(f"Subprocess args: {json.dumps({k: str(v) for k, v in combined_args.items() if k != 'env'})}", level=DEBUG)
            
            # If shell=True is set, ensure cmd is a string, not a list
            if combined_args.get('shell', False) and isinstance(cmd, list):
                cmd = ' '.join(cmd)
                
            output = subprocess.run(cmd, **combined_args)
            if hasattr(output, 'stdout') and output.stdout:
                self.logger.write(f"Std. Output:\n{output.stdout}", level=DEBUG)
            if hasattr(output, 'stderr') and output.stderr:
                self.logger.write(f"Std. Error:\n{output.stderr}", level=DEBUG)
            return output
        except subprocess.CalledProcessError as e:
            if raise_error and self.logger is not None:
                self.logger.write(f"Error: {e}", level=ERROR)
                if hasattr(e, 'stdout') and e.stdout:
                    self.logger.write(f"Error stdout: {e.stdout}", level=ERROR)
                if hasattr(e, 'stderr') and e.stderr:
                    self.logger.write(f"Error stderr: {e.stderr}", level=ERROR)
                self.logger.write(f"Error traceback: {format_exc()}", level=ERROR)
                raise e


class TestbedContextManager:
    def __init__(
        self,
        task_instances: list,
        log_dir: str,
        temp_dir: str = None,
        testbed: str = None,
        timeout: int = None,
        verbose: bool = False,
    ):
        """
        Initialize testbed context. Creates temporary directories and groups task instances
        by repo/version for Android/Kotlin projects.

        Args:
            task_instances (list): List of task instances
            log_dir (str): Path to log directory
            testbed (str): Path to testbed directory
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            temp_dir (str): Path to temporary directory
        """
        if verbose:
            logger_testbed.setLevel(logging.INFO)
        self.log_dir = os.path.abspath(log_dir)
        self.old_dir = os.getcwd()
        self.timeout = timeout
        self.verbose = verbose
        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": False,
                "text": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            },
        )

        # Create log, temp directories if they don't exist
        if not os.path.exists(self.log_dir):
            logger_testbed.info(f"[Testbed] Creating log directory {self.log_dir}")
            os.makedirs(self.log_dir, exist_ok=True)
        if temp_dir is not None and not os.path.exists(temp_dir):
            logger_testbed.info(f"[Testbed] Creating temp directory {temp_dir}")
            os.makedirs(temp_dir, exist_ok=True)
        temp_dir = os.path.abspath(temp_dir) if temp_dir is not None else None

        # Sort task instances by created_at
        self.task_instances = sorted(
            task_instances, key=lambda x: x["created_at"], reverse=True
        )

        # Group repos by repo, then version
        self.task_instances_grouped = {}
        for instance in self.task_instances:
            # Create test command from framework + directives
            instance["test_directives"] = get_test_directives(instance)
            print("test_directives", instance["test_directives"])
            
            # Format test command for Android/Gradle projects
            # instance["test_cmd"] = f"{test_type} {' '.join(instance['test_directives'])}"
            instance["test_cmd"] = get_android_test_cmd(instance)
            print("test_cmd", instance["test_cmd"])

            # Group task instances by repo, version
            repo = instance["repo"]
            version = instance["version"] if "version" in instance else None
            if repo not in self.task_instances_grouped:
                self.task_instances_grouped[repo] = {}
            if version not in self.task_instances_grouped[repo]:
                self.task_instances_grouped[repo][version] = []
            self.task_instances_grouped[repo][version].append(instance)

        # Check if instances are from single repo/version
        self.is_single_repo_version = len(self.task_instances_grouped) == 1 and \
            len(list(self.task_instances_grouped.values())[0]) == 1

        # Create log file for testbed
        log_file_name = "testbed"
        if self.is_single_repo_version:
            key, versions = list(self.task_instances_grouped.items())[0]
            _, repo = key.split("/")
            version = list(versions.keys())[0]
            log_file_name += f"_{repo}_{version}.log"
        else:
            # TODO: Make log file name more intelligible, random 4 digit number for now
            # This random naming is necessary due to parallelized execution
            log_file_name += f"_{os.urandom(24).hex()}.log"

        self.log_file = os.path.join(self.log_dir, log_file_name)
        self.log = LogWrapper(self.log_file, logger=logger_testbed, prefix="[Testbed]")
        self.exec.logger = self.log
        self.log.write(f"Created log file {self.log_file}", mode="w")

        # Get reference set up instances for each repo/version
        self.setup_refs = {}
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            self.log.write(f"Repo {repo}: {len(map_version_to_instances)} versions")

            # Determine instances to use for environment installation
            self.setup_refs[repo] = {}
            for version, instances in map_version_to_instances.items():
                self.log.write(f"\tVersion {version}: {len(instances)} instances")
                # Use the first instance as set up for each version
                self.setup_refs[repo][version] = instances[0]

        # Set up testbed path, create in temp directory if None
        if testbed is not None:
            self.temp_dir_work = None
            self.testbed = os.path.abspath(testbed)
        else:
            self.temp_dir_work = TemporaryDirectory(dir=temp_dir)
            self.testbed = self.temp_dir_work.name
        self.log.write(f"Using working directory {self.testbed} for testbed")

        # Remove None versions, versions not in MAP_VERSION_TO_INSTALL
        self._custom_restraints()

    def __enter__(self):
        """
        Set up testbed (Android SDK environment, git repositories)
        """
        
        # Set up testbed (environment, github repo) for each repo
        for repo, version_to_setup_ref in self.setup_refs.items():
            repo_prefix = repo.replace("/", "__")

            # Run any repo-level installation commands if provided
            if repo in MAP_REPO_TO_INSTALL:
                install_cmd = MAP_REPO_TO_INSTALL[repo]
                self.log.write(f"Running custom install command for {repo}: {install_cmd}")
                self.exec(install_cmd)

            # Set up each version of the repo
            for version, install in MAP_VERSION_TO_INSTALL[repo].items():
                # Skip if none of the task instances are for this version
                if version not in version_to_setup_ref:
                    continue

                # Preinstall JDK version on machine for this repo / version
                jdk_version = install["jdk_version"]
                self.install_jdk_with_sdkman(jdk_version)

                # Name for both environment and github repo
                env_name = f"{repo_prefix}__{version}"
                self.log.write(f"Setting up testbed for {env_name}")

                # Clone github per repo/version
                repo_path = os.path.join(self.testbed, env_name)
                if not os.path.exists(repo_path):
                    if clone_repo(repo, repo_path, use_original_repo=True):
                        self.log.write(f"Cloned {repo} to {repo_path}")
                    else:
                        raise Exception(f"Failed to clone {repo} to {repo_path}")
                else:
                    self.log.write(f"Repo for {repo_prefix} version {version} exists: {repo_path}; skipping")
                
                # Run any repo-level installation commands if provided
                if repo in MAP_REPO_TO_INSTALL:
                    old_dir = os.getcwd()
                    try:
                        # Change to the repo directory before running the install command
                        os.chdir(repo_path)
                        install_cmd = MAP_REPO_TO_INSTALL[repo]
                        self.log.write(f"Running custom install command for {repo} in {repo_path}: {install_cmd}")
                        self.exec(install_cmd)
                    finally:
                        # Make sure we change back to the original directory
                        os.chdir(old_dir)

                # Set up the Android project
                # self.setup_android_project(repo, version, install, repo_path)

        return self
        
    def install_jdk_with_sdkman(self, jdk_version):
        """
        Set up JDK using sdkman with the specified version
        
        Args:
            jdk_version (str): The JDK version to install using sdkman
        """
        try:
            self.log.write(f"Setting up JDK {jdk_version} using sdkman")

            # Install sdkman if not already installed
            sdkman_dir = os.path.expanduser("~/.sdkman")
            if not os.path.exists(sdkman_dir):
                self.log.write("Installing sdkman")
                curl_cmd = 'curl -s "https://get.sdkman.io" | bash'
                self.exec(curl_cmd, shell=True)
                
                # Source the initialization script right after installation
                if os.path.exists(f"{sdkman_dir}/bin/sdkman-init.sh"):
                    self.log.write("Sdkman installed successfully")
                else:
                    self.log.write("Failed to install sdkman", level=ERROR)
                    return
            
            # Source sdkman
            sdkman_init = f'. {sdkman_dir}/bin/sdkman-init.sh'
        
            # Check if the specified JDK version is available in sdkman candidates
            jdk_path = os.path.join(sdkman_dir, "candidates", "java", jdk_version)
            if os.path.exists(jdk_path):
                self.log.write(f"Found JDK version {jdk_version} in sdkman candidates")
            else:
                self.log.write(f"JDK version {jdk_version} not found, attempting to install")
                try:
                    install_cmd = f'{sdkman_init} && sdk install java {jdk_version}'
                    self.exec(install_cmd, shell=True, timeout=600)  # Increased timeout for download
                    self.log.write(f"Successfully installed JDK {jdk_version}")
                except Exception as e:
                    self.log.write(f"Failed to install JDK {jdk_version}: {e}", level=ERROR)
                
        except Exception as e:
            self.log.write(f"Error setting up JDK with sdkman: {e}", level=ERROR)
            self.log.write(format_exc(), level=ERROR)

    # def setup_android_project(self, repo, version, install, repo_path):
    #     """
    #     Set up Android project environment
        
    #     Args:
    #         repo (str): Repository name
    #         version (str): Version name
    #         install (dict): Installation instructions
    #         repo_path (str): Path to repository
    #     """
    #     try:
    #         # Change to repo directory
    #         os.chdir(repo_path)
    #         self.log.write(f"Setting up Android project: {repo} version {version}")
            
    #         # Set Java/Kotlin version info
    #         if "jdk_version" in install:
    #             self.log.write(f"Using JDK version: {install['jdk_version']} for project")
            
    #         # Make gradlew executable
    #         if os.path.exists("gradlew"):
    #             self.log.write("Making gradlew executable")
    #             self.exec(["chmod", "+x", "gradlew"])
    #     except Exception as e:
    #         self.log.write(f"Error setting up Android project: {e}", level=ERROR)
    #     finally:
    #         # Return to original directory
    #         os.chdir(self.old_dir)

    def get_distributed_tasks(self) -> list:
        """
        Create task group (instances + keywords) for each repo/version

        Returns:
            list: List of task groups, each group containing task instances
                from the same repo with the same version
        """
        distributed_tasks = []
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            repo_prefix = repo.replace("/", "__")
            for version, instances in map_version_to_instances.items():
                env_name = f"{repo_prefix}__{version}"
                
                # Get JDK version from configuration (if available)
                jdk_version = None
                if repo in MAP_VERSION_TO_INSTALL and version in MAP_VERSION_TO_INSTALL[repo]:
                    jdk_version = MAP_VERSION_TO_INSTALL[repo][version].get('jdk_version', None)
                
                task_set = {
                    "jdk_version": jdk_version,  # JDK version from configuration
                    "log_dir": self.log_dir,
                    "task_instances": instances,
                    "testbed": os.path.join(self.testbed, env_name),
                    "timeout": self.timeout,
                    "venv": env_name,
                    "version": version,
                    "verbose": self.verbose,
                }
                distributed_tasks.append(task_set)
        return distributed_tasks

    def _custom_restraints(self):
        """
        Custom restraints per repo
        """
        for repo, group in self.task_instances_grouped.items():
            if None in group:
                self.log.write(f"Removed None version from repo {repo}")
                del group[None]
            versions = list(group.keys())
            for version in versions:
                if version not in MAP_VERSION_TO_INSTALL[repo]:
                    self.log.write((
                        f"Removed {version} version from repo "
                        f"{repo} (Install instructions not given)"
                    ))
                    del group[version]

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.temp_dir_work is not None:
            self.temp_dir_work.cleanup()


logger_taskenv = logging.getLogger("taskenv")


class TaskEnvContextManager:
    def __init__(
        self,
        instance: dict,
        testbed: str,
        venv: str,
        log_dir: str,
        conda_path: str,
        verbose: bool = False,
        timeout: int = None,
        is_eval: bool = False,
        log_suffix: str = None,
    ):
        """
        Sets up execution context for a single task instance

        Args:
            instance (dict): Task instance
            testbed (str): Path to testbed directory
            venv (str): Name of conda environment (should exist in conda_path)
            log_dir (str): Path to log directory
            conda_path (str): Path to conda installation
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            is_eval (bool): Whether this is for evaluating a model on SWE Bench
                (Mainly for logging purposes)
        """
        if verbose:
            logger_taskenv.setLevel(logging.INFO)
        self.instance = instance
        self.conda_path = conda_path
        # self.conda_cache_dir = os.path.join(self.conda_path, "cache")
        self.cwd = os.getcwd()
        self.is_eval = is_eval
        self.testbed = testbed
        self.testbed_name = testbed.split("/")[-1]
        self.venv = venv

        # Log file naming
        log_file_name = (
            f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.eval.log"
            if self.is_eval
            else f"{instance[KEY_INSTANCE_ID]}.log"
        )
        if log_suffix is not None:
            log_file_name = (
                f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.{log_suffix}.eval.log"
                if self.is_eval
                else f"{instance[KEY_INSTANCE_ID]}.{log_suffix}.log"
            )
        self.log_file = os.path.join(log_dir, log_file_name)
        self.log = LogWrapper(
            self.log_file, logger=logger_taskenv,
            prefix=f"[{self.testbed_name}] [{self.instance[KEY_INSTANCE_ID]}]")

        self.timeout = timeout

        repo_prefix = instance["repo"].replace("/", "__")
        gradle_home = os.path.join(os.path.dirname(testbed), "gradle-homes", f"{repo_prefix}__{instance['version']}")
        os.makedirs(gradle_home, exist_ok=True)
        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": False,
                "text": True,
                "env": {
                    **os.environ,
                    # "GRADLE_USER_HOME": gradle_home
                },
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            },
            logger=self.log,
        )

    def __enter__(self):
        """
        Enter task environment, set up log file
        """
        os.chdir(self.testbed)
        enter_msg = (
            f"Task Metadata:\n\t- "
            f"Instance ID: {self.instance[KEY_INSTANCE_ID]}\n\t- "
            f"Testbed: {self.testbed}\n\t- "
            f"Virtual Env.: {self.venv}"
        )
        if self.is_eval:
            enter_msg += f"\n\t- Evaluation Model: {self.instance[KEY_MODEL]}"
        self.log.write(enter_msg, mode="w")
        return self

    def reset_task_env(self, instance: dict):
        """
        Reset task environment + testbed and checkout base commit of given task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            if "env" not in self.exec.subprocess_args:
                self.exec.subprocess_args["env"] = {}
            self.exec.subprocess_args["env"]["JAVA_HOME"] = ""
            if hasattr(self, 'jdk_version'):
                path = self.exec.subprocess_args["env"].get("PATH", "")
                if path:
                    self.exec.subprocess_args["env"]["PATH"] = path.replace(f"{self.jdk_version}/bin:", "")


            # Remove all paths in .gitignore
            if os.path.exists(".gitignore"):
                self.exec(
                    "git ls-files --ignored --exclude-standard -o -z | xargs -0 -r rm -rf".split(),
                    raise_error=False,
                )

            # Reset git repo + checkout base commit
            self.exec("git restore .".split(" "))
            self.exec("git reset HEAD .".split(" "))
            self.exec("git clean -fdx".split(" "))
            self.exec(
                f"git -c advice.detachedHead=false checkout {instance['base_commit']}".split(
                    " "
                )
            )
            self.log.write(f"Reset task environment to {instance['base_commit']}")
            return True
        except Exception as e:
            err_msg = f"{RESET_FAILED}; Failed to reset task environment to {instance['base_commit']}: {e}"
            self.log.write(err_msg, level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(err_msg)
            return False

    def run_install_task(self, instance: dict) -> bool:
        """
        Run installation for task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if installation successful, False otherwise
        """
        # Get installation instructions by repo/version
        specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]
        
        if "install" not in specifications:
            self.log.write(f"No installation instructions provided for {instance['repo']} version {instance['version']}")
            return True

        try:
            cmd_install = specifications['install']
            self.log.write(f"Running installation command: {cmd_install}")

            # Run installation command
            out_install = self.exec(cmd_install, timeout=self.timeout, shell=True)
            if out_install.returncode != 0:
                raise Exception(f"Installation command: {cmd_install} failed with return code {out_install.returncode}")

            # Skip installation if no instructions provided
            if "jdk_version" not in specifications:
                raise Exception("No JDK version specified in installation instructions")
            
            # Configure the correct JDK version for the task instance
            self.jdk_version = specifications["jdk_version"]

            # Direct reference to SDKMAN's installed JDK
            sdkman_java_path = os.path.expanduser(f"~/.sdkman/candidates/java/{self.jdk_version}")
            
            # Ensure JDK is installed
            if not os.path.exists(sdkman_java_path):
                raise Exception(f"JDK {self.jdk_version} not found")
            else:
                self.log.write(f"JDK {self.jdk_version} found, reusing existing JDK")
            
            # Set environment variables
            self.exec.subprocess_args["env"]["JAVA_HOME"] = sdkman_java_path
            self.exec.subprocess_args["env"]["PATH"] = f"{sdkman_java_path}/bin:{self.exec.subprocess_args['env'].get('PATH', '')}"
        
            # Installation successful
            self.log.write(f"Installation successful")
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_PASS}\n")
            return True
        except subprocess.TimeoutExpired:
            # Installation timed out
            self.log.write(f"Installation timed out", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_TIMEOUT}\n")
            return False
        except Exception as e:
            # Installation failed
            print(f"Installation failed: {e}")
            self.log.write(f"Installation failed", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_FAIL}: {e}\n")
            return False

    def apply_patch(
        self, patch: str, patch_type: PatchType = "", revert: bool = False
    ) -> bool:
        """
        Apply patch to task environment

        Args:
            patch (str): Plaintext of patch to apply
            patch_type (str): Type of patch (e.g. "eval", "test")
        Returns:
            bool: True if patch applied successfully, False otherwise
        """
        # If patch is `None`, indicate in log and skip
        if patch is None:
            self.log.write(f"Patch is `None` ({patch_type})")
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; Prediction patch is `None`")
            return False

        # Write patch to temporary patch file in parent directory
        patch_path = os.path.join(
            os.path.dirname(self.testbed.rstrip("/")),
            f"temp_{self.instance[KEY_INSTANCE_ID]}_{patch_type}.patch",
        )
        with open(patch_path, "w") as f:
            f.write(patch)

        # Restore test files before applying if patch_type is 'test'
        if patch_type == PatchType.PATCH_TEST.value:
            for test in self.instance["test_directives"]:
                if os.path.exists(test):
                    self.exec(f"git restore {test}".split(" "))

        # Apply patch to testbed directory
        apply_cmd = (
            f"git apply -v -R {patch_path}" if revert else f"git apply -v {patch_path}"
        )
        out_patch = self.exec(apply_cmd.split(" "), raise_error=False, check=False)
        os.remove(patch_path)

        log_cmd = "Revert" if revert else "Apply"
        if out_patch.returncode != 0:
            # Patch apply failed
            self.log.write(f"{log_cmd} patch failed ({patch_type})", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; ({patch_type})\nOutput:\n")
                f.write(out_patch.stdout)
                if out_patch.stderr:
                    f.write(out_patch.stderr)
            return False

        # Patch apply succeeded
        self.log.write(f"{log_cmd} patch successful ({patch_type})")
        with open(self.log_file, "a") as f:
            f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
        return True

    def run_tests_task(self, instance: dict):
        """
        Run tests for task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if test script ran successfully, False otherwise
        """
        try:
            # Run test command for task instance
            test_cmd = instance['test_cmd']
            with open(self.log_file, "a") as f:
                f.write(f"Test Script: {test_cmd};\n")
            print(f"Test command: {test_cmd}")

            # Set environment variables if provided
            specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]
            if "env_vars_test" in specifications:
                self.exec.subprocess_args["env"].update(specifications["env_vars_test"])

            out_test = self.exec(
                test_cmd, shell=True, timeout=self.timeout, check=False
            )

            # Unset environment variables if provided
            if "env_vars_test" in specifications:
                for key in specifications["env_vars_test"]:
                    del self.exec.subprocess_args["env"][key]

            # Write pass/fail status to log file
            with open(self.log_file, "a") as f:
                if out_test.returncode != 0:
                    f.write(f"\n{TESTS_FAILED}\n")
                else:
                    f.write(f"\n{TESTS_PASSED}\n")

            self.log.write(f"Test script run successful")
            return True
        except subprocess.TimeoutExpired:
            # Test command run timed out
            self.log.write("Test script run timed out", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_TIMEOUT} after {self.timeout} seconds\n")
            return False
        except Exception as e:
            # Test command run failed
            self.log.write(f"Test script run failed", level=ERROR)
            print(f"Error: {e}")
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_ERROR}: {e}")
            return False

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.cwd)