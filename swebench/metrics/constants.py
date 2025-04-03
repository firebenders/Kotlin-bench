from enum import Enum

# Result Categories
FAIL_TO_PASS = "FAIL_TO_PASS"
FAIL_TO_FAIL = "FAIL_TO_FAIL"
PASS_TO_PASS = "PASS_TO_PASS"
PASS_TO_FAIL = "PASS_TO_FAIL"
# Add missing ERROR categories
ERROR_TO_PASS = "ERROR_TO_PASS"
ERROR_TO_FAIL = "ERROR_TO_FAIL"
ERROR_TO_ERROR = "ERROR_TO_ERROR"
PASS_TO_ERROR = "PASS_TO_ERROR"
FAIL_TO_ERROR = "FAIL_TO_ERROR"

# Test Status Enum
class TestStatus(Enum):
    FAILED = "FAILED"
    PASSED = "PASSED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

# Resolved Status Enum
class ResolvedStatus(Enum):
    NO = "RESOLVED_NO"
    PARTIAL = "RESOLVED_PARTIAL"
    FULL = "RESOLVED_FULL"
