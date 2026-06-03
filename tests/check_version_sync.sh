#!/bin/bash
set -euo pipefail

# Read path relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Ensure we run from root directory
cd "$ROOT_DIR"

if [ ! -f cli-version.txt ]; then
  echo "Error: cli-version.txt not found!" >&2
  exit 1
fi

VERSION=$(tr -d '[:space:]' < cli-version.txt)
echo "Checking that all version references match $VERSION..."

ERRORS=0

# 1. Check .github/workflows/publish.yml
if ! grep -q "default: \"$VERSION\"" .github/workflows/publish.yml; then
  echo "Error: .github/workflows/publish.yml default version is not synced with cli-version.txt!" >&2
  ERRORS=$((ERRORS + 1))
fi

# 2. Check all test workflows
for f in .github/workflows/test-*.yml; do
  [ -f "$f" ] || continue
  if grep -q "uses: aetherpak/setup-cli" "$f" && ! grep -q "version: $VERSION" "$f"; then
    echo "Error: $f has mismatched version for setup-cli!" >&2
    ERRORS=$((ERRORS + 1))
  fi
  if grep -q "ghcr.io/aetherpak/cli:" "$f" && ! grep -q "cli:$VERSION" "$f"; then
    echo "Error: $f has mismatched container image versions!" >&2
    ERRORS=$((ERRORS + 1))
  fi
done

# 3. Check docs/site/index.html
if ! grep -q "Default <code>$VERSION</code>" docs/site/index.html; then
  echo "Error: docs/site/index.html default version is not synced!" >&2
  ERRORS=$((ERRORS + 1))
fi

# 4. Check ARCHITECTURE.md
if ! grep -q "\`$VERSION\`" ARCHITECTURE.md || ! grep -q ":$VERSION" ARCHITECTURE.md; then
  echo "Error: ARCHITECTURE.md is not synced!" >&2
  ERRORS=$((ERRORS + 1))
fi

# 5. Check composite actions
for f in action.yml build/action.yml plan/action.yml prep-bundle/action.yml publish-oci/action.yml publish-site/action.yml publish/action.yml; do
  if ! grep -q "default: \"$VERSION\"" "$f"; then
    echo "Error: $f default version is not synced with cli-version.txt!" >&2
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $ERRORS -gt 0 ]; then
  echo "Found $ERRORS mismatching version references!" >&2
  echo "Please run './scripts/update-version.sh <version>' to synchronize them." >&2
  exit 1
fi

echo "All version references are in sync!"
exit 0
