import json, os

from swebench.metrics.constants import (
    FAIL_TO_PASS,
    FAIL_TO_FAIL,
    FAIL_TO_ERROR,
    PASS_TO_PASS,
    PASS_TO_FAIL,
    PASS_TO_ERROR,
    ERROR_TO_PASS,
    ERROR_TO_FAIL,
    ERROR_TO_ERROR,
    TestStatus,
)
from swebench.metrics.getters import (
    get_file_name_from_lp,
    get_repo_from_lp,
    log_path_to_sms,
    test_failed,
    test_passed,
    test_errored,
)
from swebench.metrics.log_parsers import MAP_REPO_TO_PARSER


def convert_log_to_ground_truth(
    log_fp: list, repo: str = None, save_dir: str = None, verbose: bool = False
) -> dict:
    print("Converting log to ground truth")
    """
    Convert log file generated from check instances into ground truth dict

    Args:
        log_dir (str): path to log files
        save_dir (str): path to save results
        verbose (bool): whether or not to show logs
    Returns:
        dict: test case to test status mapping
    """
    inst_file_name = get_file_name_from_lp(log_fp)
    repo = repo or get_repo_from_lp(log_fp)
    log_parser = MAP_REPO_TO_PARSER[repo]

    sms, found = log_path_to_sms(log_fp, log_parser)
    if not found:
        raise ValueError(
            "Log file could not be parsed properly (Before, After Logs not found)"
        )
    sm_before, sm_after = sms[0], sms[1]

    status_ground_truth = {
        FAIL_TO_PASS: [],
        FAIL_TO_FAIL: [],
        FAIL_TO_ERROR: [],
        PASS_TO_PASS: [],
        PASS_TO_FAIL: [],
        PASS_TO_ERROR: [],
        ERROR_TO_PASS: [],
        ERROR_TO_FAIL: [],
        ERROR_TO_ERROR: [],
    }

    for test, status in sm_after.items():
        if status == TestStatus.PASSED.value:
            if test_passed(test, sm_before):
                status_ground_truth[PASS_TO_PASS].append(test)
            elif test_failed(test, sm_before):
                status_ground_truth[FAIL_TO_PASS].append(test)
            elif test_errored(test, sm_before):
                status_ground_truth[ERROR_TO_PASS].append(test)
        if status == TestStatus.FAILED.value:
            if test_passed(test, sm_before):
                status_ground_truth[PASS_TO_FAIL].append(test)
            elif test_failed(test, sm_before):
                status_ground_truth[FAIL_TO_FAIL].append(test)
            elif test_errored(test, sm_before):
                status_ground_truth[ERROR_TO_FAIL].append(test)
        if status == TestStatus.ERROR.value:
            if test_passed(test, sm_before):
                status_ground_truth[PASS_TO_ERROR].append(test)
            elif test_failed(test, sm_before):
                status_ground_truth[FAIL_TO_ERROR].append(test)
            elif test_errored(test, sm_before):
                status_ground_truth[ERROR_TO_ERROR].append(test)

    if save_dir is not None:
        results_file = f"{inst_file_name.split('.')[0]}.json"
        if verbose:
            print(f"Saving results to {os.path.join(save_dir, results_file)}")
        with open(os.path.join(save_dir, results_file), "w") as f:
            json.dump(status_ground_truth, f, indent=4)

    return status_ground_truth
