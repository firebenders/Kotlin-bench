import argparse
import os
import time
import json
import datetime
from typing import List, Dict, Any, Set

import modal

from swebench.harness.constants import PatchType, MAP_VERSION_TO_INSTALL
from swebench.harness.utils import get_instances
from swebench.harness.context_manager_modal import ModalTaskEnvManager

# Define base image with all required dependencies
base_image = (
    modal.Image.debian_slim()
    .apt_install(["git", "curl", "zip", "unzip", "ca-certificates"])
    .pip_install([
        "datasets",
        "docker",
        "pre-commit",
        "requests",
        "tqdm",
        "ghapi",
        "GitPython",
        "python-dotenv",
        "bs4",
        "unidiff"
    ])
    .run_commands([
        # Add this line to set JVM arguments that fix the ByteBuddy/Mockito issue
        'echo "export JAVA_TOOL_OPTIONS=-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true" >> /etc/profile'
    ])
    .add_local_dir(
        "swebench",
        remote_path="/root/swebench",
        ignore=lambda path: (
            str(path).endswith(".pyc") or 
            "__pycache__" in str(path) or
            ".git" in str(path)
        ),
        copy=True
    )
)

# Define the Modal app with ignore patterns for virtual environments and cache files
app = modal.App("ktbench-execution-validation", image=base_image)

# Create shared volumes
logs_volume = modal.Volume.from_name("logs-volume", create_if_missing=True)
jdk_volume = modal.Volume.from_name("jdk-volume", create_if_missing=True)
repos_volume = modal.Volume.from_name("repos-volume", create_if_missing=True)
android_sdk_volume = modal.Volume.from_name("android-sdk-volume", create_if_missing=True)

def validate_args(args):
    """
    Validation for command line arguments
    """
    if not os.path.exists(args.instances_path):
        raise ValueError(f"Could not find instances file at {args.instances_path}")
    if not os.path.exists(args.output_log_dir):
        raise ValueError(f"Could not find log directory at {args.output_log_dir}")

    # If value is provided, check that it is valid
    if args.timeout is not None and args.timeout < 0:
        raise ValueError(f"Timeout must be a positive integer")


def get_repo_path(repo: str) -> str:
    """
    Generate a path for a repository within the shared volume.
    
    Args:
        repo: Repository name (e.g., "org/repo")
        
    Returns:
        A path for the repository within the shared volume
    """
    # Create a valid directory name from the repo
    repo_dir = repo.replace('/', '__')
    return f"/repos/{repo_dir}"


@app.function(
    volumes={"/repos": repos_volume},
    timeout=600  # 10 minutes
)
def initialize_repo_volume(repo: str):
    """
    Initialize a repository within the shared repos volume.
    
    Args:
        repo: Repository name (e.g., "org/repo")
        
    Returns:
        bool: True if successful, False otherwise
    """
    import os
    from swebench.harness.utils import clone_repo
    import subprocess
    
    # Get path for this repo within the shared volume
    repo_path = get_repo_path(repo)
     
    # Create directory if it doesn't exist
    os.makedirs(repo_path, exist_ok=True)
    
    print(f"Initializing repository {repo} at {repo_path}")
    
    # Check if repository is already cloned
    if os.path.exists(os.path.join(repo_path, ".git")):
        print(f"Repository {repo} already exists in volume")
        
        try:
            # Navigate to repo directory
            os.chdir(repo_path)
            
            # Clean any local changes
            subprocess.run(["git", "restore", "."], check=False)
            subprocess.run(["git", "reset", "HEAD", "."], check=False)
            subprocess.run(["git", "clean", "-fdx"], check=False)
            
            # Try to pull latest changes
            try:
                subprocess.run(["git", "fetch", "--all"], check=False)
                print("Fetched latest changes")
            except:
                print("Failed to fetch latest changes, continuing with existing repo")
            
            return True
        except Exception as e:
            print(f"Failed to reset repository: {e}")
            # Try to re-clone if reset fails
            print("Attempting to re-clone repository...")
    else:
        print(f"Cloning repository {repo} to {repo_path}")
    
    try:
        os.chdir(repo_path)
        try:
            print("Fetching all branches and tags...")
            subprocess.run(["git", "fetch", "--all"], check=False)
            subprocess.run(["git", "fetch", "--tags"], check=False)
            print("Successfully fetched all branches and tags")
        except Exception as e:
            print(f"Warning: Failed to fetch branches and tags: {e}")
            
        print(f"Successfully initialized repository {repo}")
        return True
    except Exception as e:
        print(f"Error initializing repository: {e}")
        return False


@app.function(
    volumes={
        "/logs": logs_volume, 
        "/root/.sdkman/candidates/java": jdk_volume, 
        "/repos": repos_volume,
        "/root/android-sdk": android_sdk_volume
    },
    timeout=1200, # 20 minute timeout
    cpu=4.0,
    memory=8000,
)
def verify_task_instance(task_instance: Dict[str, Any], volume_log_dir: str, timeout: int = None, verbose: bool = False, log_suffix: str = None):
    """
    Verify a single task instance in a Modal container
    
    This function uses ModalTaskEnvManager to handle the task verification process.
    """
    import os
    import subprocess
    import glob
    
    # Get repo and version
    repo = task_instance.get("repo", "unknown")
    version = task_instance.get("version", "unknown")
    
    # Get the repository path within the shared volume
    repo_path = get_repo_path(repo)
    
    # Create a temporary working directory (to avoid modifying the shared repo directly)
    work_dir = f"/tmp/{repo.replace('/', '_')}_{version}"
    os.makedirs(work_dir, exist_ok=True)
    
    # Copy the repository to the work directory
    print(f"Copying repository from volume to {work_dir}")
    try:
        subprocess.run(["cp", "-r", f"{repo_path}/.", work_dir], check=True)
        print(f"Repository copied successfully")
        
        # Clean up any stale git lock files in the copied repository
        print("Cleaning up any git lock files...")
        for lock_file in glob.glob(f"{work_dir}/.git/**/*.lock", recursive=True):
            try:
                os.remove(lock_file)
                print(f"Removed lock file: {lock_file}")
            except Exception as e:
                print(f"Failed to remove lock file {lock_file}: {e}")
                
    except Exception as e:
        print(f"Error copying repository: {e}")
        # If copying fails, use the repository volume directly
        print(f"Falling back to using repository volume directly")
        work_dir = repo_path
    
    # Set up Android SDK for Android repositories
    android_repos = {"wordpress-mobile/WordPress-Android"}
    android_sdk_path = "/root/android-sdk"  # Define Android SDK path once

    if repo in android_repos:
        # Create local.properties file with sdk.dir
        print("Setting up Android SDK environment...")
        
        # Create or update local.properties file
        local_properties_path = os.path.join(work_dir, "local.properties")
        with open(local_properties_path, "w") as f:
            f.write(f"sdk.dir={android_sdk_path}\n")
        
        print(f"Created local.properties with Android SDK path: {android_sdk_path}")
        
        # Set environment variables
        os.environ["ANDROID_HOME"] = android_sdk_path
        os.environ["PATH"] = f"{android_sdk_path}/platform-tools:{android_sdk_path}/cmdline-tools/latest/bin:{os.environ['PATH']}"
    
    # Use the Modal-specific task environment manager with shared JDK volume
    # Ensure the volume log directory exists
    os.makedirs(volume_log_dir, exist_ok=True)
    
    try:
        with ModalTaskEnvManager(
            task_instance,
            work_dir,           # working directory with repo copy
            volume_log_dir,     # use run-specific directory in the logs volume
            verbose=verbose,
            timeout=timeout,
            log_suffix=log_suffix,
            jdk_volume_path="/root/.sdkman/candidates/java",  # Standard SDKMAN Java path
            android_sdk_path=android_sdk_path  # Pass the Android SDK path
        ) as tcm:
            # Run the verification steps in sequence
            success = (
                tcm.reset_task_env(task_instance) and
                tcm.run_install_task(task_instance) and
                tcm.apply_patch(task_instance["test_patch"], patch_type=PatchType.PATCH_TEST.value) and
                tcm.run_tests_task(task_instance) and
                tcm.apply_patch(task_instance["patch"], patch_type=PatchType.PATCH_GOLD.value) and
                tcm.run_tests_task(task_instance)
            )
            
            return {
                "instance_id": task_instance.get("instance_id", "unknown"),
                "repo": task_instance["repo"],
                "version": task_instance["version"],
                "success": success
            }
    except Exception as e:
        print(f"Task failed with error: {e}")
        # Ensure any subprocesses are killed
        import subprocess, signal, os
        try:
            subprocess.run(["pkill", "-9", "-f", "gradlew"], check=False)
            # Kill any remaining Java processes that might be hanging
            subprocess.run(["pkill", "-9", "java"], check=False)
        except:
            pass
        return {"instance_id": task_instance.get("instance_id", "unknown"),
                "repo": task_instance.get("repo", "unknown"),
                "version": task_instance.get("version", "unknown"),
                "success": False}


def get_required_jdk_versions(task_instances: List[Dict[str, Any]]) -> Set[str]:
    """
    Analyze task instances to determine all required JDK versions.

    Args:
        task_instances: List of task instances to analyze
        
    Returns:
        Set of required JDK versions
    """
    jdk_versions = set()
    
    for instance in task_instances:
        repo = instance.get("repo")
        version = instance.get("version")
        
        if not repo or not version:
                continue

        # Check if there are installation instructions for this repo/version
        if repo in MAP_VERSION_TO_INSTALL and version in MAP_VERSION_TO_INSTALL[repo]:
            specs = MAP_VERSION_TO_INSTALL[repo][version]
            if "jdk_version" in specs:
                jdk_versions.add(specs["jdk_version"])
                
    return jdk_versions


def build_image_for_jdk_setup() -> modal.Image:
    """
    Build a Docker image with SDKMAN for installing JDKs.
    """
    return base_image.run_commands([
        # Install zip/unzip if not already present
        'apt-get update && apt-get install -y zip unzip',
        # Install SDKMAN! with proper environment setup
        'curl -s "https://get.sdkman.io" | bash',
        # Initialize SDKMAN! in the current shell
        'bash -c "source $HOME/.sdkman/bin/sdkman-init.sh && sdk version"',
        # Configure SDKMAN to auto-answer prompts
        'bash -c "echo sdkman_auto_answer=true > $HOME/.sdkman/etc/config"'
    ])

@app.function(
    volumes={"/root/.sdkman/candidates/java": jdk_volume}
)
def initialize_jdk_volume(required_jdk_versions: Set[str]):
    """
    Check if the JDK volume is initialized properly and which JDK versions are missing.
    
    Args:
        required_jdk_versions: Set of JDK versions required for tasks
    
    Returns:
        Tuple[bool, Set[str]]: (is_volume_initialized, missing_jdk_versions)
    """
    import os
    
    java_dir = "/root/.sdkman/candidates/java"
    
    # Check if the java directory exists
    if not os.path.exists(java_dir):
        print(f"Java directory {java_dir} does not exist. Creating it.")
        os.makedirs(java_dir, exist_ok=True)
        return False, required_jdk_versions
    
    # List installed JDKs
    installed_jdks = [d for d in os.listdir(java_dir) 
                     if os.path.isdir(os.path.join(java_dir, d))]
    
    if installed_jdks:
        print(f"Found {len(installed_jdks)} JDKs: {', '.join(installed_jdks)}")
        
        # Determine which JDKs are missing
        missing_jdks = set(required_jdk_versions) - set(installed_jdks)
        
        if missing_jdks:
            print(f"Missing JDK versions that need to be installed: {', '.join(sorted(missing_jdks))}")
            return True, missing_jdks
        else:
            print("All required JDK versions are already installed.")
            return True, set()
    else:
        print("No JDK versions found. Need to install all required versions.")
        return False, required_jdk_versions


@app.function(
    volumes={"/root/.sdkman/candidates/java": jdk_volume},
    timeout=1800,  # 30 minutes
    image=build_image_for_jdk_setup()
)
def setup_jdk_shared_volume(jdk_versions: Set[str], force_reinstall: bool = False):
    """
    Modal function to set up the JDK shared volume by installing JDKs directly.
    
    Args:
        jdk_versions: Set of JDK versions to install
        force_reinstall: Force reinstallation of JDKs even if they exist
        
    Returns:
        bool: True if setup successful, False otherwise
    """
    import os
    import subprocess
    
    if not jdk_versions:
        print("No JDK versions to install.")
        return True
    
    print(f"Setting up JDKs: {', '.join(sorted(jdk_versions))}")
    
    java_dir = "/root/.sdkman/candidates/java"
    
    # Make sure the directory exists
    os.makedirs(java_dir, exist_ok=True)
    
    # Install each JDK version
    success = True
    for jdk_version in jdk_versions:
        # Check if JDK already exists and we're not forcing reinstall
        if os.path.exists(f"{java_dir}/{jdk_version}") and not force_reinstall:
            print(f"JDK {jdk_version} already installed. Skipping.")
            continue
            
        print(f"Installing JDK {jdk_version}...")
        
        # Install using SDKMAN
        install_cmd = f"bash -c 'source $HOME/.sdkman/bin/sdkman-init.sh && sdk install java {jdk_version} < /dev/null'"
        print(f"Running: {install_cmd}")
        
        try:
            result = subprocess.run(
                install_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            
            print(result.stdout)
            
            if result.returncode != 0:
                print(f"Failed to install JDK {jdk_version}. Error code: {result.returncode}")
                success = False
                continue
                
            # Verify the installation
            if not os.path.exists(f"{java_dir}/{jdk_version}"):
                print(f"JDK {jdk_version} was not found after installation")
                success = False
                continue
                
            print(f"JDK {jdk_version} successfully installed")
            
        except Exception as e:
            print(f"Error installing JDK {jdk_version}: {e}")
            success = False
    
    # Verify all required JDKs are installed
    installed = [d for d in os.listdir(java_dir) 
                if os.path.isdir(os.path.join(java_dir, d))]
    
    missing = jdk_versions - set(installed)
    if missing:
        print(f"Missing JDK versions: {', '.join(sorted(missing))}")
        return False
    else:
        print(f"All required JDK versions successfully installed: {', '.join(sorted(installed))}")
        return True


@app.function(volumes={"/logs": logs_volume})
def process_results(results: List[Dict[str, Any]], volume_log_dir: str):
    """
    Process and summarize results from all task verification runs
    """
    # Count successes and failures
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    # Group results by repo and version
    grouped_results = {}
    for result in results:
        repo = result["repo"]
        version = result["version"]
        
        if repo not in grouped_results:
            grouped_results[repo] = {}
        
        if version not in grouped_results[repo]:
            grouped_results[repo][version] = {"success": 0, "total": 0}
        
        grouped_results[repo][version]["total"] += 1
        if result["success"]:
            grouped_results[repo][version]["success"] += 1
    
    # Prepare summary
    summary = {
        "total_instances": total_count,
        "successful_instances": success_count,
        "success_rate": success_count / total_count if total_count > 0 else 0,
        "results_by_repo": grouped_results
    }
    
    # Write summary to the log directory
    summary_path = os.path.join(volume_log_dir, "validation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    return summary


@app.function()
def check_environment():
    """Check what packages are installed in the Modal container"""
    import subprocess
    result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
    print("Installed packages:")
    print(result.stdout)
    
    # Also check Python path
    import sys
    print("\nPython path:")
    for path in sys.path:
        print(path)


# Function to get required Android SDK versions
def get_required_android_sdk_versions(task_instances: List[Dict[str, Any]]) -> Set[str]:
    """
    Analyze task instances to determine if Android SDK is needed.
    
    Args:
        task_instances: List of task instances to analyze
        
    Returns:
        Set of required Android SDK versions (currently just "latest")
    """
    return set("35.0.1")


def build_image_for_android_sdk_setup() -> modal.Image:
    """
    Build a Docker image with tools needed for Android SDK setup.
    """
    return base_image.run_commands([
        # Install required packages
        'apt-get update && apt-get install -y unzip wget',
    ])


@app.function(
    volumes={
        "/root/android-sdk": android_sdk_volume,
        "/root/.sdkman/candidates/java": jdk_volume  # Add JDK volume access
    },
    timeout=3600,  # 60 minutes
    image=build_image_for_android_sdk_setup()
)
def initialize_android_sdk_volume(force_reinstall: bool = False):
    """
    Initialize the Android SDK volume by downloading and setting up the Android SDK.
    
    Args:
        force_reinstall: Force reinstallation of Android SDK even if it exists
        
    Returns:
        bool: True if setup successful, False otherwise
    """
    import os
    import subprocess
    import glob
    
    sdk_dir = "/root/android-sdk"
    cmdline_tools_dir = f"{sdk_dir}/cmdline-tools"
    
    # Check if already initialized and we're not forcing reinstall
    if os.path.exists(f"{sdk_dir}/.android_sdk_initialized") and not force_reinstall:
        print("Android SDK volume is already initialized. Use force_reinstall=True to reinstall.")
        return True
    
    print("Initializing Android SDK volume...")
    
    # Create directories
    os.makedirs(sdk_dir, exist_ok=True)
    os.makedirs(cmdline_tools_dir, exist_ok=True)
    
    # Set up JAVA_HOME - look for any JDK in the volume
    java_home = None
    jdk_volume_path = "/root/.sdkman/candidates/java"
    if os.path.exists(jdk_volume_path):
        # Get a list of all JDK versions in the volume
        jdk_versions = [d for d in os.listdir(jdk_volume_path) 
                        if os.path.isdir(os.path.join(jdk_volume_path, d))]
        
        if jdk_versions:
            # Use the first available JDK
            java_home = os.path.join(jdk_volume_path, jdk_versions[0])
            print(f"Found JDK in volume: {java_home}")
    
    if not java_home:
        print("No JDK found in volume. SDK setup requires Java.")
        return False
    
    # Set environment variables
    os.environ["JAVA_HOME"] = java_home
    os.environ["PATH"] = f"{java_home}/bin:{os.environ['PATH']}"
    
    print(f"Using JAVA_HOME: {java_home}")
    
    try:
        # Verify Java is available
        java_version = subprocess.run(
            "java -version", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        print(f"Java version: {java_version.stdout}")
        
        # Download Android SDK command-line tools
        cmdline_tools_url = "https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip"
        print(f"Downloading Android SDK command-line tools from {cmdline_tools_url}...")
        
        subprocess.run(
            f"wget -q {cmdline_tools_url} -O /tmp/cmdline-tools.zip",
            shell=True, check=True
        )
        
        # Extract command-line tools to the correct location
        print("Extracting Android SDK command-line tools...")
        subprocess.run(
            "unzip -q -o /tmp/cmdline-tools.zip -d /tmp/cmdline-tools",
            shell=True, check=True
        )
        
        # Move to correct directory structure expected by Android SDK
        if os.path.exists(f"{cmdline_tools_dir}/latest"):
            print("Removing existing cmdline-tools/latest directory...")
            subprocess.run(
                f"rm -rf {cmdline_tools_dir}/latest",
                shell=True, check=True
            )
        
        print("Moving command-line tools to the correct location...")
        subprocess.run(
            f"mv /tmp/cmdline-tools/cmdline-tools {cmdline_tools_dir}/latest",
            shell=True, check=True
        )
        
        # Set up Android SDK environment variables for the installation process
        env = {
            "ANDROID_HOME": sdk_dir,
            "JAVA_HOME": java_home,
            "PATH": f"{cmdline_tools_dir}/latest/bin:{java_home}/bin:{os.environ['PATH']}"
        }
        
        # Accept licenses
        print("Accepting Android SDK licenses...")
        subprocess.run(
            "yes | sdkmanager --licenses",
            shell=True, check=True, env=env
        )
        
        # Install essential Android SDK packages
        print("Installing essential Android SDK packages...")
        packages = [
            "platform-tools",
            "platforms;android-30",  # Android 11 (adjust as needed)
            "build-tools;30.0.3",    # Adjust version as needed
        ]
        
        for package in packages:
            print(f"Installing {package}...")
            try:
                subprocess.run(
                    f"sdkmanager '{package}'",
                    shell=True, check=True, env=env
                )
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to install {package}: {e}")
        
        # Create a marker file to indicate successful initialization
        with open(f"{sdk_dir}/.android_sdk_initialized", "w") as f:
            f.write("Android SDK initialized successfully")
        
        print("Android SDK volume initialized successfully.")
        return True
    
    except Exception as e:
        print(f"Error initializing Android SDK volume: {e}")
        return False


@app.function(volumes={"/logs": logs_volume})
def copy_logs_to_local(volume_run_dir: str):
    """
    Read logs from the volume and return their contents for transfer to the local machine.
    
    Args:
        volume_run_dir: Path to the run directory in the logs volume
    
    Returns:
        dict: A dictionary mapping filenames to their contents
    """
    import os
    
    try:
        # Check if the directory exists
        if not os.path.exists(volume_run_dir):
            print(f"Error: Directory {volume_run_dir} not found in the volume")
            return None
        
        print(f"Reading logs from {volume_run_dir}")
        
        # Dictionary to store file contents
        files_data = {}
        
        # Read all files from the volume run directory
        for filename in os.listdir(volume_run_dir):
            src_path = os.path.join(volume_run_dir, filename)
            if os.path.isfile(src_path):
                # Read the file content
                with open(src_path, 'rb') as f:
                    file_content = f.read()
                files_data[filename] = file_content
        
        print(f"Successfully read {len(files_data)} log files from volume")
        return files_data
            
    except Exception as e:
        print(f"Error reading logs from volume: {e}")
        return None

@app.local_entrypoint()
def main(*arglist):
    """
    Main entrypoint for validation script
    
    This function coordinates the validation process using Modal
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances_path", type=str, required=True)
    parser.add_argument("--output_log_dir", type=str, required=True)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--log_suffix", type=str)
    parser.add_argument("--skip_jdk_setup", action="store_true")
    parser.add_argument("--force_jdk_reinstall", action="store_true")
    parser.add_argument("--skip_repo_setup", action="store_true")
    parser.add_argument("--skip_android_setup", action="store_true")
    args = parser.parse_args(arglist)

    # Validate arguments
    validate_args(args)
    
    # Create a unique directory name for this run based on timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    
    # Define paths for logs
    volume_run_dir = f"/logs/{run_id}"  # Directory within the volume for this run
    local_log_dir = args.output_log_dir  # Local directory for logs
    
    print(f"Using run ID: {run_id}")
    print(f"Logs will be stored in volume directory: {volume_run_dir}")
    print(f"Logs will be copied to local directory: {local_log_dir}")
    
    # Ensure local log directory exists
    os.makedirs(local_log_dir, exist_ok=True)
    
    # Get task instances
    start_time = time.time()
    task_instances = get_instances(args.instances_path)
    print(f"Found {len(task_instances)} task instances to validate")
    
    # Analyze task instances to determine required JDK versions
    required_jdk_versions = get_required_jdk_versions(task_instances)
    print(f"Required JDK versions: {', '.join(sorted(required_jdk_versions))}")
    
    # Set up the JDK shared volume if needed
    if not args.skip_jdk_setup:
        print("Checking JDK volume status...")
        
        # Check if JDK volume is already initialized and which JDKs are missing
        is_initialized, missing_jdks = initialize_jdk_volume.remote(required_jdk_versions)
        print(f"JDK volume is initialized: {is_initialized}")
        print(f"Missing JDK versions: {missing_jdks}")
        
        # Determine if we need to set up JDKs
        if args.force_jdk_reinstall:
            print("Forcing reinstallation of all JDK versions...")
            jdks_to_install = required_jdk_versions
        else:
            jdks_to_install = missing_jdks
        
        # If not initialized or there are missing JDKs, set up the JDK volume
        if not is_initialized or jdks_to_install:
            if not is_initialized:
                print("Initializing JDK volume with required JDK versions...")
            else:
                print(f"Installing missing JDK versions: {', '.join(sorted(jdks_to_install))}")
                
            if setup_jdk_shared_volume.remote(jdks_to_install, args.force_jdk_reinstall):
                print("JDK volume initialization complete")
            else:
                raise Exception("Failed to initialize JDK volume")
        else:
            print("JDK volume is already initialized with all required versions. Skipping setup.")
    else:
        print("Skipping JDK setup as requested")
    
    # Check if Android SDK is needed and set it up
    required_android_sdk = get_required_android_sdk_versions(task_instances)
    if required_android_sdk and not args.skip_android_setup:
        print("Android SDK is required for task instances")
        if initialize_android_sdk_volume.remote(args.force_jdk_reinstall):
            print("Android SDK initialization complete")
        else:
            raise Exception("Failed to initialize Android SDK volume")
    elif args.skip_android_setup:
        print("Skipping Android SDK setup as requested")
    else:
        print("No Android SDK needed for these task instances")
    
    # Group task instances by both repo and version
    repo_version_groups = {}
    for instance in task_instances:
        repo = instance.get("repo", "unknown")
        version = instance.get("version", "unknown")
        key = (repo, version)
        
        if key not in repo_version_groups:
            repo_version_groups[key] = []
        repo_version_groups[key].append(instance)
    
    # Set up repository volumes if needed
    repo_setup_results = {}
    if not args.skip_repo_setup:
        unique_repos = {repo for repo, _ in repo_version_groups.keys()}
        print(f"Setting up repositories for {len(unique_repos)} unique repositories")
        
        # Create a list to store futures for each repo setup
        repo_setup_futures = []
        for repo in unique_repos:
            # Spawn repository setup in a concurrent job
            future = initialize_repo_volume.spawn(repo)
            repo_setup_futures.append((repo, future))
        
        # Wait for all repository setup jobs to finish
        for repo, future in repo_setup_futures:
            repo_setup_results[repo] = future.get()
        
        # Report setup results
        failed_repos = [k for k, v in repo_setup_results.items() if not v]
        if failed_repos:
            print(f"WARNING: Failed to set up {len(failed_repos)} repositories: {', '.join(failed_repos)}")
        else:
            print(f"Successfully initialized all {len(unique_repos)} repository volumes")
    else:
        print("Skipping repository setup as requested")
    
    # Process task instances
    print(f"Processing {len(task_instances)} task instances...")
    
    # Create a list to store futures for each task verification
    verify_task_futures = []
    for instance in task_instances:
        # Get task details
        instance_id = instance.get("instance_id", "unknown")
        
        if instance["repo"] not in MAP_VERSION_TO_INSTALL:
            print(f"No installation instructions found for repo {instance['repo']}")
            continue

        if "version" not in instance:
            print(f"No version specified for instance {instance_id}")
            continue
            
        if instance["version"] not in MAP_VERSION_TO_INSTALL[instance["repo"]]:
            print(MAP_VERSION_TO_INSTALL[instance["repo"]])
            print(f"No installation instructions found for version {instance['version']}")
            continue

        print(f"Scheduling verification for instance {instance_id}")
        
        # Spawn task verification in a concurrent job
        future = verify_task_instance.spawn(
            instance, 
            volume_run_dir,
            timeout=args.timeout, 
            verbose=args.verbose, 
            log_suffix=args.log_suffix
        )
        verify_task_futures.append((instance_id, future))
    
    # Wait for all task verification jobs to finish
    results = []
    failed_instances = []
    for instance_id, future in verify_task_futures:
        print(f"Instance {instance_id} completing...")
        try:
            result = future.get()
            results.append(result)
        except modal.exception.FunctionTimeoutError:
            print(f"WARNING: Instance {instance_id} timed out")
            failed_instances.append({
                "instance_id": instance_id,
                "error": "timeout",
                "success": False
            })
            results.append({
                "instance_id": instance_id,
                "repo": "unknown",  # We could store this from the original instance if needed
                "version": "unknown",
                "success": False
            })
        except Exception as e:
            print(f"WARNING: Instance {instance_id} failed with error: {e}")
            failed_instances.append({
                "instance_id": instance_id,
                "error": str(e),
                "success": False
            })
            results.append({
                "instance_id": instance_id,
                "repo": "unknown",
                "version": "unknown",
                "success": False
            })
    
    # Log failed instances to a separate file
    if failed_instances:
        # Ensure the volume run directory exists
        os.makedirs(volume_run_dir, exist_ok=True)
        
        failed_instances_path = os.path.join(volume_run_dir, "failed_instances.json")
        with open(failed_instances_path, "w") as f:
            json.dump(failed_instances, f, indent=2)
        print(f"Logged {len(failed_instances)} failed instances to {failed_instances_path}")
    
    # Process and summarize results
    summary = process_results.remote(results, volume_run_dir)
    
    # Copy logs from the volume to the local machine
    print(f"Copying logs from volume to local directory: {local_log_dir}")
    files_data = copy_logs_to_local.remote(volume_run_dir)

    local_run_dir = os.path.join(local_log_dir, run_id)
    if files_data:
        # Create the local run directory
        os.makedirs(local_run_dir, exist_ok=True)
        
        # Write files to the local machine
        files_copied = 0
        for filename, content in files_data.items():
            try:
                file_path = os.path.join(local_run_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(content)
                files_copied += 1
            except Exception as e:
                print(f"Error writing file {filename}: {e}")
        
        print(f"Successfully copied {files_copied} log files to {local_run_dir}")
    else:
        print(f"Warning: Failed to copy logs from volume")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"Total time taken: {elapsed_time:.2f} seconds")
    print(f"Total task instances processed: {len(task_instances)}")
    print(f"Successful task instances: {summary['successful_instances']}")
    print(f"Success rate: {summary['success_rate']:.2%}")
    print(f"Results saved to volume: {os.path.join(volume_run_dir, 'validation_summary.json')}")
    if local_run_dir:
        print(f"Results available locally at: {os.path.join(local_run_dir, 'validation_summary.json')}")

# python3 ./harness/engine_validation_modal.py \
#   --instances_path ./collect/data/tasks/versioned/WordPress-Android-task-instances_versions.json \
#   --log_dir ./modal_logs \
#   --verbose

# modal run ./harness/engine_validation_modal.py \
#   --instances_path ./collect/data/tasks/versioned/WordPress-Android-task-instances_versions.json \
#   --log_dir ./modal_logs \
#   --verbose