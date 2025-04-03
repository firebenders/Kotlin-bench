from enum import Enum
from typing import TypedDict, List


class SWEbenchInstance(TypedDict):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: List[str]
    PASS_TO_PASS: List[str]
    environment_setup_commit: str

MAP_VERSION_TO_INSTALL_WORDPRESS = {
    k: {
        "jdk_version": "17.0.9-tem",
        "install": "if [ -f gradle.properties-example ]; then cp gradle.properties-example gradle.properties; fi",
    }
    for k in [
        "25.72", "25.71", "25.62", "25.4", "25.41", "25.31", "25.01",
        "24.92", "24.72", "24.83", "24.82", "24.73", "24.5", "24.71",
        "24.61", "24.51", "24.42", "24.41", "24.31", "24.2", "24.22",
        "24.21", "24.1", "24.12", "24.13", "24.01", "23.93", "23.92",
        "23.71", "23.91", "23.85", "23.83", "23.84", "23.82", "23.7",
        "23.61", "23.5", "23.52", "23.51", "23.4", "23.43", "23.32",
        "23.31", "23.2", "23.21", "23.12", "23.11", "23.02", "23.01",
        "22.91"
    ]
}

ANKI_INSTALL_SCRIPT = """
if [ -f gradle.properties ]; then sed -i 's|org.gradle.jvmargs=.*|org.gradle.jvmargs=-Xmx2048M -XX:MaxMetaspaceSize=512M -Dfile.encoding=UTF-8|' gradle.properties; fi

if [ -f settings.gradle.kts ]; then
    awk '/resolutionStrategy {/,/^    }$/ {next} {print}' settings.gradle.kts > settings.gradle.kts.tmp
    mv settings.gradle.kts.tmp settings.gradle.kts
fi

if [ -f build.gradle ]; then
    # Create a temporary file
    sed '/id.*amazon/d' AnkiDroid/build.gradle > AnkiDroid/build.gradle.tmp
    mv AnkiDroid/build.gradle.tmp AnkiDroid/build.gradle
fi

if [ -f build.gradle ]; then
    sed -i '/app.brant:amazonappstorepublisher/d' build.gradle
fi

# Replace JavaVersion.VERSION_11 with JavaVersion.VERSION_17
if [ -f AnkiDroid/build.gradle ]; then
    sed -i 's/JavaVersion.VERSION_11/JavaVersion.VERSION_17/g' AnkiDroid/build.gradle
fi

# Replace wildcard SearchPreference dependency with specific version
if [ -f AnkiDroid/build.gradle ]; then
    sed -i "s/com.github.ByteHamster:SearchPreference:[v]*[0-9].[0-9].[0-9]/com.github.ByteHamster:SearchPreference:2.7.2/g" AnkiDroid/build.gradle
fi

if [ -f AnkiDroid/build.gradle ]; then
    # Create a temporary file
    touch temp_build.gradle
    # Process the file line by line
    IN_AMAZON_BLOCK=0
    while IFS= read -r line; do
        if echo "$line" | grep -q "^[[:space:]]*amazon[[:space:]]*{"; then
            IN_AMAZON_BLOCK=1
            continue
        fi
        if [ $IN_AMAZON_BLOCK -eq 1 ] && echo "$line" | grep -q "^[[:space:]]*}"; then
            IN_AMAZON_BLOCK=0
            continue
        fi
        if [ $IN_AMAZON_BLOCK -eq 0 ]; then
            echo "$line" >> temp_build.gradle
        fi
    done < AnkiDroid/build.gradle
    mv temp_build.gradle AnkiDroid/build.gradle
fi
"""

ANKI_INSTALL_SCRIPT_MAC = """
if [ -f gradle.properties ]; then sed -i '' 's|org.gradle.jvmargs=.*|org.gradle.jvmargs=-Xmx2048M -XX:MaxMetaspaceSize=512M -Dfile.encoding=UTF-8|' gradle.properties; fi

if [ -f settings.gradle.kts ]; then
    awk '/resolutionStrategy {/,/^    }$/ {next} {print}' settings.gradle.kts > settings.gradle.kts.tmp
    mv settings.gradle.kts.tmp settings.gradle.kts
fi

if [ -f build.gradle ]; then
    # Create a temporary file
    sed '/id.*amazon/d' AnkiDroid/build.gradle > AnkiDroid/build.gradle.tmp
    mv AnkiDroid/build.gradle.tmp AnkiDroid/build.gradle
fi

if [ -f build.gradle ]; then
    sed -i '' '/app.brant:amazonappstorepublisher/d' build.gradle
fi

if [ -f AnkiDroid/build.gradle ]; then
    sed -i '' '/app.brant.amazonappstorepublisher/d' AnkiDroid/build.gradle
fi

# Replace JavaVersion.VERSION_11 with JavaVersion.VERSION_17
if [ -f AnkiDroid/build.gradle ]; then
    sed -i '' 's/JavaVersion.VERSION_11/JavaVersion.VERSION_17/g' AnkiDroid/build.gradle
fi

# Replace ByteHamster dependency to a usable version
sed -i '' "s/com.github.ByteHamster:SearchPreference:[v]*[0-9].[0-9].[0-9]/com.github.ByteHamster:SearchPreference:2.7.2/g" AnkiDroid/build.gradle

if [ -f AnkiDroid/build.gradle ]; then
    # Create a temporary file
    touch temp_build.gradle
    # Process the file line by line
    IN_AMAZON_BLOCK=0
    while IFS= read -r line; do
        if echo "$line" | grep -q "^[[:space:]]*amazon[[:space:]]*{"; then
            IN_AMAZON_BLOCK=1
            continue
        fi
        if [ $IN_AMAZON_BLOCK -eq 1 ] && echo "$line" | grep -q "^[[:space:]]*}"; then
            IN_AMAZON_BLOCK=0
            continue
        fi
        if [ $IN_AMAZON_BLOCK -eq 0 ]; then
            echo "$line" >> temp_build.gradle
        fi
    done < AnkiDroid/build.gradle
    mv temp_build.gradle AnkiDroid/build.gradle
fi
"""

# # Replace wildcard SearchPreference dependency with specific version
# if [ -f AnkiDroid/build.gradle ]; then
    # sed -i '' "s/com.github.ByteHamster:SearchPreference:[v]*[0-9].[0-9].[0-9]/com.github.ByteHamster:SearchPreference:2.7.2/g" AnkiDroid/build.gradle
# fi

MAP_VERSION_TO_INSTALL_ANKI = {
    k: {
        "jdk_version": "17.0.9-tem",
        "install": ANKI_INSTALL_SCRIPT,
    }
    for k in [
    "2.16",
    "2.171",
    "2.1710",
    "2.1713",
    "2.1714",
    "2.1715",
    "2.1716",
    "2.1717",
    "2.172",
    "2.173",
    "2.174",
    "2.175",
    "2.176",
    "2.178",
    "2.179",
    "2.182",
    "2.183",
    "2.184",
    "2.185",
    "2.186",
    "2.187",
    "2.188",
    "2.189",
    "2.190",
    "2.191",
    "2.1910",
    "2.1911",
    "2.1912",
    "2.192",
    "2.193",
    "2.194",
    "2.196",
    "2.197",
    "2.199",
    "2.20",
    "2.201",
    "2.202",
    "2.203",
    "2.211",
    "2.2111",
    "2.2112",
    "2.2113",
    "2.214",
    "2.215",
    "2.217",
    "2.218",
    "2.219"
    ]
}

MAP_VERSION_TO_INSTALL_KTLINT = {
    k: {
        "jdk_version": "17.0.9-tem",
        "install": "",
    }
    for k in [
    "0.49",
    "0.50",
    "1.0",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5"
    ]
}

MAP_VERSION_TO_INSTALL_THUNDERBIRD = {
    k: {
        "jdk_version": "17.0.9-tem",
        "install": "",
    }
    for k in [
        "0.1",
        "8.0",
        "10.0",
        "11.0",
    ]
}

COROUTINE_INSTALL_SCRIPT = """
if [ -f kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt ]; then
    sed -i '/override fun checkPropertyAccess/,/^    }/d' kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt
fi        
"""

COROUTINE_INSTALL_SCRIPT_MAC = """
if [ -f kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt ]; then
    sed -i '' '/override fun checkPropertyAccess/,/^    }/d' kotlinx-coroutines-core/jvm/test/TestSecurityManager.kt
fi        
"""

MAP_VERSION_TO_INSTALL_COROUTINES = {
    k: {
        "jdk_version": "11.0.20-tem",
        "install": COROUTINE_INSTALL_SCRIPT,
    } for k in [
        "1.10",
        "1.9",
        "1.8",
        "1.6",
        "1.7"
    ]
}

MAP_VERSION_TO_INSTALL_KOTLINX_DATETIME = {
    k: {
        "jdk_version": "8.0.392-zulu",
        "install": "",
    } for k in [
        "0.4",
        "0.5",
        "0.6"
    ]
}

# Constants - Task Instance Installation Environment
MAP_VERSION_TO_INSTALL = {
    "wordpress-mobile/WordPress-Android": MAP_VERSION_TO_INSTALL_WORDPRESS,
    "ankidroid/Anki-Android": MAP_VERSION_TO_INSTALL_ANKI,
    "pinterest/ktlint": MAP_VERSION_TO_INSTALL_KTLINT,
    "Kotlin/kotlinx.coroutines": MAP_VERSION_TO_INSTALL_COROUTINES,
    "thunderbird/thunderbird-android": MAP_VERSION_TO_INSTALL_THUNDERBIRD,
    "Kotlin/kotlinx-datetime": MAP_VERSION_TO_INSTALL_KOTLINX_DATETIME
}

# Constants - Task Instance Test Frameworks
MAP_REPO_TO_TEST_FRAMEWORK_KT = {
    "wordpress-mobile/WordPress-Android": "./gradlew :WordPress:testWordPressVanillaDebugUnitTest",
    "ankidroid/Anki-Android": "./gradlew :AnkiDroid:testPlayDebugUnitTest",
    "pinterest/ktlint": "./gradlew :ktlint-ruleset-standard:test",
    "Kotlin/kotlinx.coroutines": "./gradlew :kotlinx-coroutines-core:jvmTest",
    "thunderbird/thunderbird-android": "./gradlew test",
    "Kotlin/kotlinx-datetime": "./gradlew :kotlinx-datetime:jvmTest"
}

MAP_REPO_TO_INSTALL = {}
MAP_REPO_TO_ENV_YML_PATHS = {} # Constants - Task Instance environment.yml File Paths
MAP_REPO_TO_REQS_PATHS = {} # Constants - Task Instance Requirements File Paths

# Constants - Evaluation Keys
KEY_INSTANCE_ID = "instance_id"
KEY_MODEL = "model_name_or_path"
KEY_PREDICTION = "model_patch"

# Constants - Logging
APPLY_PATCH_FAIL = ">>>>> Patch Apply Failed"
APPLY_PATCH_PASS = ">>>>> Applied Patch"
INSTALL_FAIL = ">>>>> Init Failed"
INSTALL_PASS = ">>>>> Init Succeeded"
INSTALL_TIMEOUT = ">>>>> Init Timed Out"
RESET_FAILED = ">>>>> Reset Failed"
TESTS_ERROR = ">>>>> Tests Errored"
TESTS_FAILED = ">>>>> Some Tests Failed"
TESTS_PASSED = ">>>>> All Tests Passed"
TESTS_TIMEOUT = ">>>>> Tests Timed Out"


# Constants - Patch Types
class PatchType(Enum):
    PATCH_GOLD = "gold"
    PATCH_PRED = "pred"
    PATCH_PRED_TRY = "pred_try"
    PATCH_PRED_MINIMAL = "pred_minimal"
    PATCH_PRED_MINIMAL_TRY = "pred_minimal_try"
    PATCH_TEST = "test"

    def __str__(self):
        return self.value


# Constants - Miscellaneous
NON_TEST_EXTS = [
    ".json",
    ".png",
    "csv",
    ".txt",
    ".md",
    ".jpg",
    ".jpeg",
    ".pkl",
    ".yml",
    ".yaml",
    ".toml",
]
SWE_BENCH_URL_RAW = "https://raw.githubusercontent.com/"
USE_X86 = {}