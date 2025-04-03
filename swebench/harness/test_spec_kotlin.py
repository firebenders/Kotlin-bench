import hashlib
import json
import platform
import re

from dataclasses import dataclass
from typing import Union

from swebench.harness.constants import (
    SWEbenchInstance,
    MAP_REPO_TO_INSTALL,
    MAP_VERSION_TO_INSTALL,
    MAP_REPO_TO_TEST_FRAMEWORK_KT,  # Use Kotlin-specific test framework map
    USE_X86,
)
from swebench.harness.dockerfiles import (
    get_dockerfile_base,
    get_dockerfile_env,
    get_dockerfile_instance,
)
from swebench.harness.utils import (
    get_requirements,
    get_environment_yml,
    get_test_directives,
    get_android_test_cmd,  # Import Android-specific test command generator
)

DIFF_MODIFIED_FILE_REGEX = r"--- a/(.*)"


@dataclass
class TestSpec:
    """
    A dataclass that represents a test specification for a single instance of SWE-bench.
    """
    instance_id: str
    repo: str
    version: str
    repo_script_list: str
    eval_script_list: str
    env_script_list: str
    arch: str
    FAIL_TO_PASS: list[str]
    PASS_TO_PASS: list[str]

    @property
    def setup_env_script(self):
        return "\n".join(["#!/bin/bash", "set -euxo pipefail"] + self.env_script_list) + "\n"

    @property
    def eval_script(self):
        return "\n".join(["#!/bin/bash", "set -uxo pipefail"] + self.eval_script_list) + "\n"
        # Don't exit early because we need to revert tests at the end

    @property
    def install_repo_script(self):
        return "\n".join(["#!/bin/bash", "set -euxo pipefail"] + self.repo_script_list) + "\n"

    @property
    def base_image_key(self):
        return f"sweb.base.{self.arch}:latest"

    @property
    def env_image_key(self):
        """
        The key for the environment image is based on the hash of the environment script list.
        If the environment script list changes, the image will be rebuilt automatically.

        Note that old images are not automatically deleted, so consider cleaning up old images periodically.
        """
        hash_object = hashlib.sha256()
        hash_object.update(str(self.env_script_list).encode("utf-8"))
        hash_value = hash_object.hexdigest()
        val = hash_value[:22]  # 22 characters is still very likely to be unique
        return f"sweb.env.{self.arch}.{val}:latest"

    @property
    def instance_image_key(self):
        return f"sweb.eval.{self.arch}.{self.instance_id}:latest"

    def get_instance_container_name(self, session_id=None):
        if not session_id:
            return f"sweb.eval.{self.instance_id}"
        return f"sweb.eval.{self.instance_id}.{session_id}"

    @property
    def base_dockerfile(self):
        return get_dockerfile_base(self.platform, self.arch)

    @property
    def env_dockerfile(self):
        return get_dockerfile_env(self.platform, self.arch)

    @property
    def instance_dockerfile(self):
        return get_dockerfile_instance(self.platform, self.env_image_key)

    @property
    def platform(self):
        if self.arch == "x86_64":
            return "linux/x86_64"
        elif self.arch == "arm64":
            return "linux/arm64/v8"
        else:
            raise ValueError(f"Invalid architecture: {self.arch}")
        

def get_test_specs_from_dataset(dataset: Union[list[SWEbenchInstance], list[TestSpec]]) -> list[TestSpec]:
    """
    Idempotent function that converts a list of SWEbenchInstance objects to a list of TestSpec objects.
    """
    if isinstance(dataset[0], TestSpec):
        return dataset
    return list(map(make_test_spec, dataset))


def make_repo_script_list(install, repo, repo_directory, base_commit, env_name):
    """
    Create a list of bash commands to set up the repository for testing.
    This is the setup script for the instance image.
    """
    setup_commands = [
        f"git clone -o origin https://github.com/{repo} {repo_directory}",
        f"chmod -R 777 {repo_directory}",  # So nonroot user can run tests
        f"cd {repo_directory}",
        f"git reset --hard {base_commit}",
        # Remove the remote so the agent won't see newer commits.
        f"git remote remove origin",
        # Make sure gradle wrapper is executable
        f"chmod +x {repo_directory}/gradlew",
        # Make sure conda is available for later use
        "source /opt/miniconda3/bin/activate",
        f"conda activate {env_name}",
        f'echo "Current environment: $CONDA_DEFAULT_ENV"',
    ]
    if repo in MAP_REPO_TO_INSTALL:
        setup_commands.append(MAP_REPO_TO_INSTALL[repo])

    # Run pre-install set up if provided
    if "pre_install" in install:
        for pre_install in install["pre_install"]:
            setup_commands.append(pre_install)

    # For Android/Kotlin projects, ensure Android SDK is properly configured
    if "android_sdk" in install and install["android_sdk"]:
        # Set up local.properties with Android SDK path
        sdk_path = "/root/android-sdk"
        setup_commands.append(f'echo "sdk.dir={sdk_path}" > {repo_directory}/local.properties')

    if "install" in install:
        setup_commands.append(install["install"])
    return setup_commands


def make_env_script_list(instance, install, env_name):
    reqs_commands = []
        
    # For Android/Kotlin projects, ensure JDK is properly configured
    if "jdk_version" in install:
        jdk_version = install["jdk_version"]
        reqs_commands.append(f"export JAVA_HOME=/root/.sdkman/candidates/java/{jdk_version}")
        reqs_commands.append("export PATH=$JAVA_HOME/bin:$PATH")
    
    # If this is an Android project, configure Android SDK
    if "android_sdk" in install and install["android_sdk"]:
        reqs_commands.append("export ANDROID_HOME=/root/android-sdk")
        reqs_commands.append("export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH")
        
    return reqs_commands


def make_eval_script_list(instance, install, env_name, repo_directory, base_commit, test_patch):
    """
    Applies the test patch and runs the tests.
    """
    HEREDOC_DELIMITER = "EOF_114329324912"
    test_files = re.findall(DIFF_MODIFIED_FILE_REGEX, test_patch)
    # Reset test files to the state they should be in before the patch.
    reset_tests_command = f"git checkout {base_commit} {' '.join(test_files)}"
    apply_test_patch_command = (
        f"git apply -v - <<'{HEREDOC_DELIMITER}'\n{test_patch}\n{HEREDOC_DELIMITER}"
    )
    
    # Use Kotlin-specific test framework command
    test_command = " ".join(
        [
            MAP_REPO_TO_TEST_FRAMEWORK_KT[instance["repo"]][instance["version"]],
            *get_test_directives(instance),
        ]
    )
    
    eval_commands = [
        f"source /opt/miniconda3/bin/activate",
        f"conda activate {env_name}",
        f"cd {repo_directory}",
    ]
    
    # For Kotlin/Android projects, configure environment variables
    if "jdk_version" in install:
        eval_commands.append(f"export JAVA_HOME=/root/.sdkman/candidates/java/{install['jdk_version']}")
        eval_commands.append("export PATH=$JAVA_HOME/bin:$PATH")
        
    if "android_sdk" in install and install["android_sdk"]:
        eval_commands.append("export ANDROID_HOME=/root/android-sdk")
        eval_commands.append("export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH")
    
    if "eval_commands" in install:
        eval_commands += install["eval_commands"]
        
    eval_commands += [
        f"git config --global --add safe.directory {repo_directory}",  # for nonroot user
        f"cd {repo_directory}",
        # This is just informational, so we have a record
        f"git status",
        f"git show",
        f"git diff {base_commit}",
        "source /opt/miniconda3/bin/activate",
        f"conda activate {env_name}",
    ]
    
    if "install" in install:
        eval_commands.append(install["install"])
        
    # Set Mockito fix for Kotlin tests
    eval_commands.append('export JAVA_TOOL_OPTIONS="-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true"')
        
    eval_commands += [
        reset_tests_command,
        apply_test_patch_command,
        test_command,
        reset_tests_command,  # Revert tests after done, leave the repo in the same state as before
    ]
    return eval_commands


def make_test_spec(instance: SWEbenchInstance) -> TestSpec:
    if isinstance(instance, TestSpec):
        return instance
    instance_id = instance["instance_id"]
    repo = instance["repo"]
    version = instance["version"]
    base_commit = instance["base_commit"]
    problem_statement = instance["problem_statement"]
    hints_text = instance["hints_text"]  # Unused
    test_patch = instance["test_patch"]
    pass_to_pass = instance["PASS_TO_PASS"]
    fail_to_pass = instance["FAIL_TO_PASS"]

    env_name = "testbed"
    repo_directory = f"/{env_name}"
    install = MAP_VERSION_TO_INSTALL[repo][version]

    repo_script_list = make_repo_script_list(install, repo, repo_directory, base_commit, env_name)
    env_script_list = make_env_script_list(instance, install, env_name)
    eval_script_list = make_eval_script_list(
        instance, install, env_name, repo_directory, base_commit, test_patch
    )
    if platform.machine() in {"aarch64", "arm64"}:
        # use arm64 unless explicitly specified
        arch = "arm64" if instance_id not in USE_X86 else "x86_64"
    else:
        arch = "x86_64"

    return TestSpec(
        instance_id=instance_id,
        repo=repo,
        env_script_list=env_script_list,
        repo_script_list=repo_script_list,
        eval_script_list=eval_script_list,
        version=version,
        arch=arch,
        FAIL_TO_PASS=fail_to_pass,
        PASS_TO_PASS=pass_to_pass,
    )