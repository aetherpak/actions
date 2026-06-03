#!/usr/bin/env bash
# Verify unsigned publish outputs and index structures
set -euo pipefail

if [ "$#" -ne 13 ]; then
  echo "Usage: $0 <expected_app_id> <expected_branch> <expected_arch> <expected_repo_path> <actual_app_id> <actual_branch> <actual_arch> <actual_repo_path> <site_dir> <remote_name> <expected_registry> <expected_oci_repository> <actual_signing_path>" >&2
  exit 1
fi

EXPECTED_APP_ID="$1"
EXPECTED_BRANCH="$2"
EXPECTED_ARCH="$3"
EXPECTED_REPO_PATH="$4"
ACTUAL_APP_ID="$5"
ACTUAL_BRANCH="$6"
ACTUAL_ARCH="$7"
ACTUAL_REPO_PATH="$8"
SITE_DIR="$9"
REMOTE_NAME="${10}"
EXPECTED_REGISTRY="${11}"
EXPECTED_OCI_REPO="${12}"
ACTUAL_SIGNING_PATH="${13}"

# 1. Output variables checks
if [ "$ACTUAL_APP_ID" != "$EXPECTED_APP_ID" ]; then
  echo "Error: publish app-id mismatch ($ACTUAL_APP_ID != $EXPECTED_APP_ID)" >&2
  exit 1
fi
if [ "$ACTUAL_BRANCH" != "$EXPECTED_BRANCH" ]; then
  echo "Error: publish branch mismatch ($ACTUAL_BRANCH != $EXPECTED_BRANCH)" >&2
  exit 1
fi
if [ "$ACTUAL_ARCH" != "$EXPECTED_ARCH" ]; then
  echo "Error: publish arch mismatch ($ACTUAL_ARCH != $EXPECTED_ARCH)" >&2
  exit 1
fi
if [ "$ACTUAL_REPO_PATH" != "$EXPECTED_REPO_PATH" ]; then
  echo "Error: publish repo-path mismatch ($ACTUAL_REPO_PATH != $EXPECTED_REPO_PATH)" >&2
  exit 1
fi

# 2. File existence checks
STATIC_INDEX="$SITE_DIR/index/static"
if [ ! -f "$STATIC_INDEX" ]; then
  echo "Error: index/static not generated at $STATIC_INDEX" >&2
  exit 1
fi

REPO_FILE="$SITE_DIR/$REMOTE_NAME.flatpakrepo"
if [ ! -f "$REPO_FILE" ]; then
  echo "Error: flatpakrepo file not generated at $REPO_FILE" >&2
  exit 1
fi

# Unsigned: the repo file must NOT carry a key
if grep -q '^GPGKey=' "$REPO_FILE"; then
  echo "Error: unsigned .flatpakrepo unexpectedly contains GPGKey" >&2
  exit 1
fi

REF_FILE="$SITE_DIR/refs/$EXPECTED_APP_ID-$EXPECTED_BRANCH.flatpakref"
if [ ! -f "$REF_FILE" ]; then
  echo "Error: per-app .flatpakref not generated at $REF_FILE" >&2
  exit 1
fi

# 3. Check index contents via jq
REGISTRY_URL="$(jq -r '.Registry' "$STATIC_INDEX")"
if [ "$REGISTRY_URL" != "$EXPECTED_REGISTRY" ]; then
  echo "Error: Registry URL in index is wrong (Expected: $EXPECTED_REGISTRY, Got: $REGISTRY_URL)" >&2
  exit 1
fi

NAME="$(jq -r '.Results[0].Name' "$STATIC_INDEX")"
if [ "$NAME" != "$EXPECTED_OCI_REPO" ]; then
  echo "Error: Result Name in index is wrong (Expected: $EXPECTED_OCI_REPO, Got: $NAME)" >&2
  exit 1
fi

REF="$(jq -r '.Results[0].Images[0].Labels["org.flatpak.ref"]' "$STATIC_INDEX")"
EXPECTED_REF="app/$EXPECTED_APP_ID/$EXPECTED_ARCH/$EXPECTED_BRANCH"
if [ "$REF" != "$EXPECTED_REF" ]; then
  echo "Error: Image Ref Label in index is wrong (Expected: $EXPECTED_REF, Got: $REF)" >&2
  exit 1
fi

# Flatpak needs the full label set in the index, not just the ref
for label in org.flatpak.commit org.flatpak.metadata; do
  VAL="$(jq -r --arg l "$label" '.Results[0].Images[0].Labels[$l] // empty' "$STATIC_INDEX")"
  if [ -z "$VAL" ]; then
    echo "Error: required label $label missing from index" >&2
    exit 1
  fi
done

# 4. Assert signing is disabled
SIGNING_JSON="$SITE_DIR/sigs/signing.json"
if [ ! -f "$SIGNING_JSON" ]; then
  echo "Error: signing.json missing at $SIGNING_JSON" >&2
  exit 1
fi

ENABLED="$(jq -r '.enabled' "$SIGNING_JSON")"
if [ "$ENABLED" != "false" ]; then
  echo "Error: unsigned signing.json should report enabled=false (Got: $ENABLED)" >&2
  exit 1
fi

if [ -f "$SITE_DIR/sigs/key.asc" ]; then
  echo "Error: unsigned publish unexpectedly exported a public key to sigs/key.asc" >&2
  exit 1
fi

if find "$SITE_DIR/sigs" -type f -name 'signature-*' | grep -q .; then
  echo "Error: unsigned publish unexpectedly produced signatures" >&2
  exit 1
fi

if [ "$ACTUAL_SIGNING_PATH" != "off" ]; then
  echo "Error: unsigned publish should report signing-path=off (Got: $ACTUAL_SIGNING_PATH)" >&2
  exit 1
fi

echo "Unsigned publish verification successful!"
exit 0
