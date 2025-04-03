import re

from swebench.metrics.constants import TestStatus

def parse_log_gradle(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with Gradle
    
    Args:
        log (str): log content
    Returns:
        dict: Returns a single-entry dictionary with overall test status
    """
    test_status_map = {}
    
    # Check for compilation errors (Kotlin/Java compilation errors start with "e: ")
    has_compilation_error = "Compilation error" in log
    if has_compilation_error:
        test_status_map["gradle_test_execution"] = TestStatus.ERROR.value
    elif "BUILD SUCCESSFUL" in log:
        test_status_map["gradle_test_execution"] = TestStatus.PASSED.value
    else:
        test_status_map["gradle_test_execution"] = TestStatus.FAILED.value
        
    return test_status_map

MAP_REPO_TO_PARSER = {
    "wordpress-mobile/WordPress-Android": parse_log_gradle,
    "ankidroid/Anki-Android": parse_log_gradle,
    "pinterest/ktlint": parse_log_gradle,
    "Kotlin/kotlinx.coroutines": parse_log_gradle,
    "Kotlin/kotlinx-datetime": parse_log_gradle,
    "thunderbird/thunderbird-android": parse_log_gradle,
}
