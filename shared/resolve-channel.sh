#!/usr/bin/env bash
# Default channel for the git ref: tag -> stable, default branch -> beta, else
# the ref name. Ignores the explicit `branch` input so callers can rank it ahead
# of the repo's own ref branch. Shared by the build and publish actions.
set -euo pipefail

if [ "${GITHUB_REF_TYPE:-}" = "tag" ]; then
  echo "stable"
elif [ "${GITHUB_REF_NAME:-}" = "${DEFAULT_BRANCH:-main}" ]; then
  echo "beta"
else
  echo "${GITHUB_REF_NAME:-}"
fi
