#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
RESET='\033[0m'

AT_LEAST_ONE_ERROR=0

function capture_stdout_and_stderr_if_successful {
    set +e
    COMMAND=$*
    printf "Running %s ... " "${COMMAND}"

    if ! OUTPUT=$($COMMAND 2>&1); then
        AT_LEAST_ONE_ERROR=1
        printf "%bFailed%b\n" "${RED}" "${RESET}"
        printf "%s\n\n" "${OUTPUT}"
    else
        printf "%bSuccess!%b\n" "${GREEN}" "${RESET}"
    fi
    set -e
}

capture_stdout_and_stderr_if_successful black --check py_ts_interfaces
capture_stdout_and_stderr_if_successful flake8 --count py_ts_interfaces
capture_stdout_and_stderr_if_successful mypy py_ts_interfaces
capture_stdout_and_stderr_if_successful isort -c py_ts_interfaces
capture_stdout_and_stderr_if_successful pytest

exit $AT_LEAST_ONE_ERROR
