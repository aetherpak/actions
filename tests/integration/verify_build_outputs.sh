#!/usr/bin/env bash
# Verify that build outputs match expectations
set -euo pipefail

if [ "$#" -ne 6 ]; then
  echo "Usage: $0 <expected_app_id> <expected_branch> <expected_arch> <actual_app_id> <actual_branch> <actual_arch>" >&2
  exit 1
fi

EXPECTED_APP_ID="$1"
EXPECTED_BRANCH="$2"
EXPECTED_ARCH="$3"
ACTUAL_APP_ID="$4"
ACTUAL_BRANCH="$5"
ACTUAL_ARCH="$6"

if [ "$ACTUAL_APP_ID" != "$EXPECTED_APP_ID" ]; then
  echo "Error: app-id output is wrong (Expected: $EXPECTED_APP_ID, Got: $ACTUAL_APP_ID)" >&2
  exit 1
fi

if [ "$ACTUAL_BRANCH" != "$EXPECTED_BRANCH" ]; then
  echo "Error: branch output is wrong (Expected: $EXPECTED_BRANCH, Got: $ACTUAL_BRANCH)" >&2
  exit 1
fi

if [ "$ACTUAL_ARCH" != "$EXPECTED_ARCH" ]; then
  echo "Error: arch output is wrong (Expected: $EXPECTED_ARCH, Got: $ACTUAL_ARCH)" >&2
  exit 1
fi

echo "Build outputs verified successfully."
exit 0
