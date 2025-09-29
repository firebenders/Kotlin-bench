import logging, os, subprocess, json
import time
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from traceback import format_exc
import glob
import re

from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
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


logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger_taskenv = logging.getLogger("taskenv_modal")


class LogWrapper:
    """Simple wrapper for logging to both file and logger"""
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
    """Wrapper for subprocess execution with logging"""
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


class ModalTaskEnvManager:
    """
    A simplified context manager for task environments in Modal containers.
    
    This class is designed to work in pre-configured containers where JDK
    and other dependencies are already installed in the Modal image.
    """
    
    def __init__(
        self,
        instance: dict,
        testbed: str,
        log_dir: str,
        verbose: bool = False,
        timeout: int = None,
        log_suffix: str = None,
        jdk_volume_path: str = None,
        android_sdk_path: str = None,
    ):
        """
        Sets up execution context for a single task instance in a Modal container

        Args:
            instance (dict): Task instance dictionary
            testbed (str): Path to testbed directory in the container
            log_dir (str): Path to log directory (shared volume in Modal)
            verbose (bool): Whether to show verbose logs
            timeout (int): Timeout for actions in seconds
            log_suffix (str): Optional suffix for log files
            jdk_volume_path (str): Path to the shared JDK volume
            android_sdk_path (str): Path to the Android SDK
        """
        if verbose:
            logger_taskenv.setLevel(logging.INFO)
        
        self.instance = instance
        self.cwd = os.getcwd()
        self.testbed = testbed
        self.testbed_name = os.path.basename(testbed)
        self.timeout = timeout
        self.jdk_volume_path = jdk_volume_path
        self.android_sdk_path = android_sdk_path
        
        # Setup logging
        instance_id = instance.get(KEY_INSTANCE_ID, "unknown")
        model = instance.get(KEY_MODEL, "unknown")
        
        # Log file naming
        log_file_suffix = f".{log_suffix}" if log_suffix else ""
        log_file_name = f"{instance_id}{log_file_suffix}.log"
        
        # Ensure log directory exists
        # log_dir should already be an absolute path to the mounted volume
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, log_file_name)
        
        # Initialize logger
        self.log = LogWrapper(
            self.log_file, 
            logger=logger_taskenv,
            prefix=f"[{self.testbed_name}] [{instance_id}]"
        )
        
        # Set environment with Mockito fix
        env = {**os.environ}
        
        # Add Mockito environment variable to fix ByteBuddy agent issue
        env["JAVA_TOOL_OPTIONS"] = env.get("JAVA_TOOL_OPTIONS", "") + " -Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker"
        
        # Initialize subprocess executor
        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": False,
                "text": True,
                "env": env,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            },
            logger=self.log,
        )

    def __enter__(self):
        """
        Enter task environment, prepare workspace and logging
        """
        # Create testbed directory if it doesn't exist
        os.makedirs(self.testbed, exist_ok=True)
        os.chdir(self.testbed)
        
        # Set up logging
        enter_msg = (
            f"Task Metadata:\n\t- "
            f"Instance ID: {self.instance.get(KEY_INSTANCE_ID, 'unknown')}\n\t- "
            f"Repo: {self.instance.get('repo', 'unknown')}\n\t- "
            f"Version: {self.instance.get('version', 'unknown')}\n\t- "
            f"Testbed: {self.testbed}"
        )
        
        if KEY_MODEL in self.instance:
            enter_msg += f"\n\t- Model: {self.instance[KEY_MODEL]}"
            
        # Log if we're using a shared JDK volume
        if self.jdk_volume_path:
            enter_msg += f"\n\t- JDK Volume: {self.jdk_volume_path}"
            
        self.log.write(enter_msg, mode="w")
        
        # Repository setup is now handled by the repo_volume in engine_validation_modal.py
        # The repository should already be cloned and copied to the working directory
        if not os.path.exists(os.path.join(self.testbed, ".git")):
            repo = self.instance.get("repo")
            if repo:
                self.log.write(f"Repository not found in working directory, attempting to clone {repo}")
                if clone_repo(repo, self.testbed, use_original_repo=True):
                    self.log.write(f"Successfully cloned repository {repo}")
                else:
                    self.log.write(f"Failed to clone repository {repo}", level=ERROR)
        else:
            self.log.write(f"Using pre-cloned repository in {self.testbed}")
        
        return self

    def reset_task_env(self, instance: dict):
        """
        Reset task environment to base commit
        
        Args:
            instance (dict): Task instance
            
        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            # First, check and remove any git lock files that might be present
            self.log.write("Checking for stale git lock files...")
            for lock_file in glob.glob(os.path.join(self.testbed, ".git", "**", "*.lock"), recursive=True):
                try:
                    os.remove(lock_file)
                    self.log.write(f"Removed git lock file: {lock_file}")
                except Exception as lock_err:
                    self.log.write(f"Unable to remove lock file {lock_file}: {lock_err}", level=WARNING)
            
            # Reset git repo + checkout base commit
            self.exec("git restore .".split(" "), raise_error=False)
            self.exec("git reset HEAD .".split(" "), raise_error=False)
            self.exec("git clean -fdx".split(" "), raise_error=False)
            
            # Check out the base commit for the task instance
            if "base_commit" in instance:
                try:
                    self.exec(
                        f"git -c advice.detachedHead=false checkout {instance['base_commit']}".split(" ")
                    )
                    self.log.write(f"Reset task environment to {instance['base_commit']}")
                except Exception as checkout_err:
                    # If checkout fails, try with a more aggressive approach
                    self.log.write(f"Initial checkout failed: {checkout_err}", level=WARNING)
                    self.log.write("Attempting more aggressive repository reset...", level=WARNING)
                    
                    # Try to force checkout with a fresh working tree
                    try:
                        self.exec("git reset --hard HEAD".split(" "), raise_error=False)
                        self.exec("git clean -fdx".split(" "), raise_error=False)
                        self.exec(f"git -c advice.detachedHead=false checkout -f {instance['base_commit']}".split(" "))
                        self.log.write(f"Reset task environment to {instance['base_commit']} with aggressive approach")
                    except Exception as force_err:
                        self.log.write(f"Failed aggressive checkout: {force_err}", level=ERROR)
                        raise force_err
            else:
                self.log.write("No base commit specified, using current HEAD")
                
            return True
        except Exception as e:
            err_msg = f"{RESET_FAILED}; Failed to reset task environment: {e}"
            self.log.write(err_msg, level=ERROR)
            return False
    
    def configure_jdk(self, jdk_version: str):
        """
        Configure environment to use the specified JDK version from the shared volume.
        
        Args:
            jdk_version (str): JDK version to use
            
        Returns:
            bool: True if configuration successful, False otherwise
        """
        try:
            # The JDK should already be installed in the shared volume by engine_validation_modal.py
            if not self.jdk_volume_path:
                self.log.write("No JDK volume path provided", level=ERROR)
                return False
                
            java_home = os.path.join(self.jdk_volume_path, jdk_version)
            if not os.path.exists(java_home):
                self.log.write(f"JDK {jdk_version} not found in shared volume at {java_home}", level=ERROR)
                return False
                
            self.log.write(f"Using JDK {jdk_version} from shared volume at {java_home}")
                
            # Update environment variables
            self.exec.subprocess_args["env"]["JAVA_HOME"] = java_home
            self.exec.subprocess_args["env"]["PATH"] = f"{java_home}/bin:{self.exec.subprocess_args['env'].get('PATH', '')}"
            
            # Verify JDK is properly configured by checking java version
            version_output = self.exec(["java", "-version"], raise_error=False)
            if version_output.returncode == 0:
                self.log.write(f"JDK {jdk_version} is properly configured")
                return True
            else:
                self.log.write(f"Failed to verify JDK {jdk_version} installation", level=ERROR)
                return False
                
        except Exception as e:
            self.log.write(f"Error configuring JDK: {e}", level=ERROR)
            return False

    def run_install_task(self, instance: dict) -> bool:
        """
        Run project-specific installation for a task instance
        
        Args:
            instance (dict): Task instance
        
        Returns:
            bool: True if installation successful, False otherwise
        """            
        specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]
        
        # Set up JDK if version is specified
        if "jdk_version" in specifications:
            jdk_version = specifications["jdk_version"]
            if not self.configure_jdk(jdk_version):
                self.log.write(f"Failed to configure JDK {jdk_version}", level=ERROR)
                with open(self.log_file, "a") as f:
                    f.write(f"{INSTALL_FAIL}; Failed to configure JDK {jdk_version}")
                return False
                
        # Make sure ANDROID_HOME is set and local.properties exists
        android_sdk_path = self.android_sdk_path or os.environ.get("ANDROID_HOME", "/root/android-sdk")
        
        # Update environment variables in the subprocess executor
        self.log.write(f"Setting up Android SDK environment: {android_sdk_path}")
        self.exec.subprocess_args["env"]["ANDROID_HOME"] = android_sdk_path
        
        # Create or update local.properties with sdk.dir
        local_properties_path = os.path.join(self.testbed, "local.properties")
        if not os.path.exists(local_properties_path):
            self.log.write(f"Creating local.properties with sdk.dir={android_sdk_path}")
            with open(local_properties_path, "w") as f:
                f.write(f"sdk.dir={android_sdk_path}\n")
        else:
            self.log.write(f"local.properties already exists, updating with sdk.dir={android_sdk_path}")
            # Read existing content and update/add sdk.dir
            with open(local_properties_path, "r") as f:
                lines = f.readlines()
            
            # Look for sdk.dir line
            sdk_dir_found = False
            for i, line in enumerate(lines):
                if line.startswith("sdk.dir="):
                    lines[i] = f"sdk.dir={android_sdk_path}\n"
                    sdk_dir_found = True
                    break
            
            # Add sdk.dir if not found
            if not sdk_dir_found:
                lines.append(f"sdk.dir={android_sdk_path}\n")
            
            # Write updated content
            with open(local_properties_path, "w") as f:
                f.writelines(lines)
                    
            # Make gradlew executable
            if os.path.exists(os.path.join(self.testbed, "gradlew")):
                self.log.write("Making gradlew executable")
                self.exec(["chmod", "+x", "gradlew"])
        
        # Run installation command if provided
        if "install" in specifications:
            try:
                install_cmd = specifications["install"]
                self.log.write(f"Running installation command: {install_cmd}")
                out_install = self.exec(install_cmd, shell=True, timeout=self.timeout)
                
                if out_install.returncode != 0:
                    self.log.write(f"Installation command failed with return code {out_install.returncode}", level=ERROR)
                    with open(self.log_file, "a") as f:
                        f.write(f"{INSTALL_FAIL}; Installation command failed with return code {out_install.returncode}")
                    return False
                
                self.log.write("Installation successful")
                with open(self.log_file, "a") as f:
                    f.write(f"\n{INSTALL_PASS}\n")
                return True
            except subprocess.TimeoutExpired:
                self.log.write("Installation timed out", level=ERROR)
                with open(self.log_file, "a") as f:
                    f.write(f"{INSTALL_TIMEOUT} after {self.timeout} seconds\n")
                return False
            except Exception as e:
                self.log.write(f"Installation failed: {e}", level=ERROR)
                with open(self.log_file, "a") as f:
                    f.write(f"{INSTALL_FAIL}; {e}\n")
                return False
        else:
            # If no install command provided, just mark as success
            self.log.write("No installation command provided, skipping")
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_PASS}\n")
            return True

    def apply_patch(
        self, patch: str, patch_type: str = "", revert: bool = False
    ) -> bool:
        """
        Apply patch to task environment
        
        Args:
            patch (str): Plaintext of patch to apply
            patch_type (str): Type of patch (e.g. "eval", "test")
            revert (bool): Whether to revert the patch
            
        Returns:
            bool: True if patch applied successfully, False otherwise
        """
        # Skip if patch is None
        if patch is None:
            self.log.write(f"Patch is `None` ({patch_type})")
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; Patch is `None`")
            return False
            
        # Write patch to temporary file
        patch_path = os.path.join(
            "/tmp",
            f"temp_{self.instance.get(KEY_INSTANCE_ID, 'unknown')}_{patch_type}.patch",
        )
        
        with open(patch_path, "w") as f:
            f.write(patch)
            
        # Restore test files before applying if patch_type is 'test'
        if patch_type == PatchType.PATCH_TEST.value and "test_directives" in self.instance:
            for test in self.instance["test_directives"]:
                if os.path.exists(test):
                    self.exec(f"git restore {test}".split(" "), raise_error=False)
                    
        # Apply or revert patch
        apply_cmd = f"git apply -v -R {patch_path}" if revert else f"git apply -v {patch_path}"
        out_patch = self.exec(apply_cmd.split(" "), raise_error=False, check=False)
        
        # Clean up temp file
        os.remove(patch_path)
        
        # Log result
        log_cmd = "Revert" if revert else "Apply"
        if out_patch.returncode != 0:
            # Patch apply failed
            print(f"Patch apply failed ({out_patch.stdout})")
            self.log.write(f"{log_cmd} patch failed ({patch_type})", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; ({patch_type})\nOutput:\n")
                f.write(out_patch.stdout)
            return False
            
        # Patch apply succeeded
        self.log.write(f"{log_cmd} patch successful ({patch_type})")
        with open(self.log_file, "a") as f:
            f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
        return True
        
    def _apply_patch_with_service(self, patch: str, patch_type: str) -> bool:
        """
        Apply patch using ApplyService API when git apply fails
        
        Args:
            patch (str): Plaintext of patch to apply
            patch_type (str): Type of patch
            
        Returns:
            bool: True if patch applied successfully, False otherwise
        """
        try:
            # Extract file paths and changes from the patch
            file_pattern = re.compile(r'^--- a/(.*?)$', re.MULTILINE)
            file_paths = file_pattern.findall(patch)
            
            if not file_paths:
                self.log.write("No file paths found in patch", level=ERROR)
                return False
                
            success_count = 0
            total_count = 0
            
            # Process each file in the patch
            for file_path in set(file_paths):  # Use set to handle duplicates
                # Skip if this is a readme file
                if 'readme' in file_path.lower():
                    continue
                    
                total_count += 1
                    
                # Get the file path relative to repo root
                abs_file_path = os.path.join(self.testbed, file_path)
                
                # Check if file exists
                if not os.path.exists(abs_file_path):
                    self.log.write(f"File not found: {file_path}", level=WARNING)
                    continue
                    
                # Read original file content
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                    
                # Extract the change for this file from the patch
                file_chunk_pattern = re.compile(
                    r'--- a/' + re.escape(file_path) + r'.*?(?=^--- a/|\Z)',
                    re.MULTILINE | re.DOTALL
                )
                file_chunk_match = file_chunk_pattern.search(patch)
                
                if not file_chunk_match:
                    self.log.write(f"Could not extract patch chunk for {file_path}", level=WARNING)
                    continue
                    
                file_patch = file_chunk_match.group(0)
                
                # Prepare data for ApplyService API call
                user_msg = f"Apply patch to {file_path}"
                
                # Call the ApplyService API
                result_content = self._call_apply_service(
                    original_content=original_content,
                    file_path=file_path,
                    code_snippet=file_patch,
                    user_msg=user_msg
                )
                
                # If API call failed, skip this file
                if result_content is None:
                    self.log.write(f"ApplyService API failed for {file_path}, skipping", level=WARNING)
                    continue
                
                # Check if content actually changed
                if result_content == original_content:
                    self.log.write(f"ApplyService API returned unchanged content for {file_path}, skipping", level=WARNING)
                    continue
                
                # Write the updated content to the file
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(result_content)
                
                self.log.write(f"Successfully applied patch to {file_path} using ApplyService API")
                success_count += 1
                
            # Consider the patch successful if we updated at least one file
            if success_count > 0:
                self.log.write(f"ApplyService API patch application successful ({success_count}/{total_count} files updated)")
                with open(self.log_file, "a") as f:
                    f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
                return True
            else:
                self.log.write(f"ApplyService API patch application failed (0/{total_count} files updated)", level=ERROR)
                with open(self.log_file, "a") as f:
                    f.write(f"{APPLY_PATCH_FAIL}; Could not apply patch to any files\n")
                return False
            
        except Exception as e:
            self.log.write(f"ApplyService API patch application error: {str(e)}", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; ApplyService API error: {str(e)}\n")
            return False

    def run_tests_task(self, instance: dict):
        """
        Run tests for task instance
        
        Args:
            instance (dict): Task instance
            
        Returns:
            bool: True if tests ran successfully, False otherwise
        """
        try:
            # Ensure test command exists
            if "test_cmd" not in instance:
                # Generate test command if not already present
                instance["test_directives"] = get_test_directives(instance)
                instance["test_cmd"] = get_android_test_cmd(instance)
                
            test_cmd = instance["test_cmd"]
            if test_cmd is None:
                self.log.write("No test command found for instance", level=ERROR)
                return True
            
            # # Log test command
            # with open(self.log_file, "a") as f:
            #     f.write(f"Test Script: {test_cmd};\n")

            # Set environment variables for testing if specified
            specifications = MAP_VERSION_TO_INSTALL.get(instance.get("repo", ""), {}).get(instance.get("version", ""), {})
            if "env_vars_test" in specifications:
                self.exec.subprocess_args["env"].update(specifications["env_vars_test"])
            
            # Set additional JVM arguments to fix ByteBuddy/Mockito issues
            mockito_fix = "-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true"
            current_java_opts = self.exec.subprocess_args["env"].get("JAVA_TOOL_OPTIONS", "")
            if mockito_fix not in current_java_opts:
                self.exec.subprocess_args["env"]["JAVA_TOOL_OPTIONS"] = f"{current_java_opts} {mockito_fix}".strip()
                self.log.write(f"Added Mockito fix to JAVA_TOOL_OPTIONS: {self.exec.subprocess_args['env']['JAVA_TOOL_OPTIONS']}")
            
            android_sdk_path = self.android_sdk_path or os.environ.get("ANDROID_HOME", "/root/android-sdk")
            self.log.write(f"Setting Android environment variables: ANDROID_HOME={android_sdk_path}")
            self.exec.subprocess_args["env"]["ANDROID_HOME"] = android_sdk_path
            
            # Update PATH to include Android tools
            self.exec.subprocess_args["env"]["PATH"] = (
                f"{android_sdk_path}/platform-tools:{android_sdk_path}/cmdline-tools/latest/bin:"
                f"{self.exec.subprocess_args['env'].get('PATH', '')}"
            )
            
            # Double-check local.properties exists before running tests
            local_properties_path = os.path.join(self.testbed, "local.properties")
            if not os.path.exists(local_properties_path):
                self.log.write(f"Creating local.properties with sdk.dir={android_sdk_path}")
                with open(local_properties_path, "w") as f:
                    f.write(f"sdk.dir={android_sdk_path}\n")
            
            # Add Mockito fix to gradle.properties
            gradle_properties_path = os.path.join(self.testbed, "gradle.properties")
            mockito_gradle_fix = "org.gradle.jvmargs=-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true"
            
            if os.path.exists(gradle_properties_path):
                self.log.write("Updating gradle.properties with Mockito fix")
                # Read existing content
                with open(gradle_properties_path, "r") as f:
                    lines = f.readlines()
                
                # Check if org.gradle.jvmargs is already defined
                jvmargs_found = False
                for i, line in enumerate(lines):
                    if line.startswith("org.gradle.jvmargs="):
                        if "mockito.mock.maker" not in line:
                            # Append Mockito fix to existing jvmargs
                            lines[i] = line.strip() + " -Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true -Dnet.bytebuddy.experimental=true\n"
                        jvmargs_found = True
                        break
                
                # Add jvmargs if not found
                if not jvmargs_found:
                    lines.append(f"{mockito_gradle_fix}\n")
                
                # Write updated content
                with open(gradle_properties_path, "w") as f:
                    f.writelines(lines)
            else:
                # Create new gradle.properties file
                self.log.write("Creating gradle.properties with Mockito fix")
                with open(gradle_properties_path, "w") as f:
                    f.write(f"{mockito_gradle_fix}\n")
            
            # Run test command
            self.log.write(f"Running test command: {test_cmd}")
            out_test = self.exec(test_cmd, shell=True, timeout=self.timeout, check=False)
            
            # Unset environment variables
            if "env_vars_test" in specifications:
                for key in specifications["env_vars_test"]:
                    if key in self.exec.subprocess_args["env"]:
                        del self.exec.subprocess_args["env"][key]
                        
            # Write test results to log file
            with open(self.log_file, "a") as f:
                if out_test.returncode != 0:
                    f.write(f"\n{TESTS_FAILED}\n")
                    # Add detailed test output to help identify which predictions failed
                    f.write("=== Detailed Test Output ===\n")
                    if hasattr(out_test, 'stdout') and out_test.stdout:
                        f.write(out_test.stdout)
                    if hasattr(out_test, 'stderr') and out_test.stderr:
                        f.write(out_test.stderr)
                    f.write("=== End Test Output ===\n")
                else:
                    f.write(f"\n{TESTS_PASSED}\n")
                    
            self.log.write(f"Test script completed with return code {out_test.returncode}")
            return True
            
        except subprocess.TimeoutExpired:
            self.log.write("Test script timed out", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{TESTS_TIMEOUT}\n")
            return False
            
        except Exception as e:
            self.log.write(f"Test script failed: {e}", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{TESTS_ERROR}: {e}\n")
            return False

    def apply_full_file_changes(self, full_file_content: str, patch_type: str = "pred") -> bool:
        """
        Applies changes from a full file format response by updating the files directly.
        Uses ApplyService API to handle imperfectly formatted changes when possible.
        
        Args:
            full_file_content (str): The model output in full file format with [start of]/[end of] markers
            patch_type (str): Type of patch being applied (pred or gold)
        
        Returns:
            bool: True if changes were applied successfully, False otherwise
        """
        # Use the regex pattern from eval_retrieval.py to extract file contents
        file_pattern = re.compile(
            r'\[start of (.*?)]'  # Match "[start of " and capture the path (non-greedy)
            r'\n?'               # Optionally match a newline after the start marker
            r'(.*?)'             # Capture the content between markers (non-greedy)
            r'\n?'               # Optionally match a newline before the end marker
            r'\[end of \1]',      # Match "[end of " and the same path captured earlier (\1)
            re.DOTALL
        )
        matches = list(file_pattern.finditer(full_file_content))

        if not matches:
            self.log.write("No matches found in full file content", level=ERROR)
            return False
        
        try:
            for match in matches:
                file_path = match.group(1)
                new_content = match.group(2)
                
                # Skip if this is a readme file
                if 'readme' in file_path.lower():
                    continue
                    
                # Construct absolute path relative to repo root
                abs_file_path = os.path.join(self.testbed, file_path)
                
                # Create directories if they don't exist
                os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                
                try:
                    # Read existing content if file exists
                    if os.path.exists(abs_file_path):
                        with open(abs_file_path, 'r', encoding='utf-8') as f:
                            original_content = f.read()
                    else:
                        original_content = ""
                    
                    # Only proceed if content is different
                    if original_content != new_content:
                        # Use ApplyService API to get correctly formatted file content
                        user_msg = f"Apply changes to {file_path}"
                        
                        # Call the ApplyService API
                        result_content = None
                        # result_content = self._call_apply_service(
                        #     original_content=original_content,
                        #     file_path=file_path,
                        #     code_snippet=new_content,
                        #     user_msg=user_msg
                        # )
                        
                        # If API call failed, fall back to direct content
                        if result_content is None:
                            self.log.write(f"ApplyService API failed, falling back to direct content for {file_path}", level=WARNING)
                            result_content = new_content
                        
                        # Write the result content to the file
                        with open(abs_file_path, 'w', encoding='utf-8') as f:
                            f.write(result_content)
                        
                        # Log the change
                        self.log.write(f"Updated file: {file_path}")
                        
                except Exception as e:
                    self.log.write(f"Error updating file {file_path}: {str(e)}", level=ERROR)
                    return False
            
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
                
            return True
            
        except Exception as e:
            self.log.write(f"Error applying full file changes: {str(e)}", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; {str(e)}\n")
            return False

    def _call_apply_service(self, original_content: str, file_path: str, code_snippet: str, user_msg: str = None) -> str:
        """
        Call the ApplyService API to get corrected file content
        
        Args:
            original_content (str): Original file content
            file_path (str): Path to the file being modified
            code_snippet (str): The code snippet or patch to apply
            user_msg (str): Optional user message providing context
            
        Returns:
            str: The corrected file content, or None if the API call fails
        """
        try:
            import json
            import urllib.request
            import urllib.error
            
            # Default user message if not provided
            if user_msg is None:
                user_msg = f"Apply changes to {file_path}"
                
            # Get the instructions and code snippet as markdown
            instructions = f"**Original Request**: {user_msg}\n\n**Full Solution**:\n```\n{code_snippet}\n```"
            
            # Prepare request data
            request_data = {
                "agent": False,
                "instructions": instructions,
                "currentFileContext": original_content,
                "codeFileName": file_path,
                "codeSnippet": code_snippet
            }
            
            # URL to ApplyService API - get from environment variable with fallback
            url = "https://apply-service.firebender.workers.dev/v1/apply"
            
            # Prepare the request
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
            }
            
            # Log API request
            self.log.write(f"Calling ApplyService API for file: {file_path}")
            
            # Convert request data to JSON
            data = json.dumps(request_data).encode('utf-8')
            
            # Create the request
            req = urllib.request.Request(
                url=url,
                data=data,
                headers=request_headers,
                method="POST"
            )
            
            try:
                # Send the request
                with urllib.request.urlopen(req, timeout=30) as response:
                    response_data = response.read().decode('utf-8')
                    
                    # Parse the response
                    response_json = json.loads(response_data)
                    
                    # Extract the result content
                    if 'result' in response_json:
                        self.log.write(f"Successfully received response from ApplyService API for {file_path}")
                        return response_json['result']
                    else:
                        self.log.write(f"ApplyService API response missing result for {file_path}", level=WARNING)
                        return None
                        
            except urllib.error.HTTPError as http_err:
                self.log.write(f"ApplyService API HTTP error for {file_path}: {http_err.code} - {http_err.reason}", level=ERROR)
                
                # Try to read error response
                error_response = http_err.read().decode('utf-8')
                self.log.write(f"ApplyService API error response: {error_response}", level=ERROR)
                return None
                
            except urllib.error.URLError as url_err:
                self.log.write(f"ApplyService API connection error for {file_path}: {str(url_err)}", level=ERROR)
                return None
                
            except json.JSONDecodeError as json_err:
                self.log.write(f"ApplyService API response parsing error for {file_path}: {str(json_err)}", level=ERROR)
                return None
                
        except Exception as e:
            self.log.write(f"ApplyService API error for {file_path}: {str(e)}", level=ERROR)
            return None

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Clean up when exiting the context manager"""
        os.chdir(self.cwd) 