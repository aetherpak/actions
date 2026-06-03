#!/usr/bin/env bash
# Verify signed publish outputs, GPG keys, and OCI image signatures
set -euo pipefail

if [ "$#" -ne 8 ]; then
  echo "Usage: $0 <actual_signing_path> <registry_host_port> <oci_repository> <app_id> <branch> <arch> <site_dir> <remote_name>" >&2
  exit 1
fi

ACTUAL_SIGNING_PATH="$1"
REGISTRY="$2"
OCI_REPO="$3"
APP_ID="$4"
BRANCH="$5"
ARCH="$6"
SITE_DIR="$7"
REMOTE_NAME="$8"

STATIC_INDEX="$SITE_DIR/index/static"

# 1. Verify signing path output is gpg
if [ "$ACTUAL_SIGNING_PATH" != "gpg" ]; then
  echo "Error: auto mode with a key should report signing-path=gpg (Got: $ACTUAL_SIGNING_PATH)" >&2
  exit 1
fi

# 2. Extract digest and verify signature paths
DIGEST="$(jq -r '.Results[0].Images[0].Digest' "$STATIC_INDEX")"
# Replace ':' with '=' for signature directory names
SIG_DIR_NAME="${DIGEST/:/=}"
SIG_FILE="$SITE_DIR/sigs/$OCI_REPO@$SIG_DIR_NAME/signature-1"
KEY_FILE="$SITE_DIR/sigs/key.asc"
SIGNING_JSON="$SITE_DIR/sigs/signing.json"

if [ ! -f "$SIG_FILE" ]; then
  echo "Error: missing signature file at $SIG_FILE" >&2
  exit 1
fi

if [ ! -f "$KEY_FILE" ]; then
  echo "Error: missing key.asc at $KEY_FILE" >&2
  exit 1
fi

if [ ! -f "$SIGNING_JSON" ]; then
  echo "Error: missing signing.json at $SIGNING_JSON" >&2
  exit 1
fi

ENABLED="$(jq -r '.enabled' "$SIGNING_JSON")"
if [ "$ENABLED" != "true" ]; then
  echo "Error: signing.json should report enabled=true (Got: $ENABLED)" >&2
  exit 1
fi

# 3. Verify .flatpakrepo carries GPGKey and it matches key.asc
REPO_FILE="$SITE_DIR/$REMOTE_NAME.flatpakrepo"
if [ ! -f "$REPO_FILE" ]; then
  echo "Error: missing .flatpakrepo file at $REPO_FILE" >&2
  exit 1
fi

if ! grep -q '^GPGKey=' "$REPO_FILE"; then
  echo "Error: signed .flatpakrepo at $REPO_FILE missing GPGKey" >&2
  exit 1
fi

# Compare embedded GPG key to exported key.asc
EMBEDDED_TMP=$(mktemp)
KEYASC_TMP=$(mktemp)
grep '^GPGKey=' "$REPO_FILE" | sed 's/^GPGKey=//' | base64 -d > "$EMBEDDED_TMP"
gpg --dearmor < "$KEY_FILE" > "$KEYASC_TMP"

if ! cmp -s "$EMBEDDED_TMP" "$KEYASC_TMP"; then
  echo "Error: embedded GPGKey does not match key.asc" >&2
  rm -f "$EMBEDDED_TMP" "$KEYASC_TMP"
  exit 1
fi
rm -f "$EMBEDDED_TMP" "$KEYASC_TMP"

# 4. Verify OCI signature using skopeo standalone-verify
REF="$REGISTRY/$OCI_REPO:${APP_ID//./_}-$BRANCH-$ARCH"
echo "Inspecting manifest for $REGISTRY/$OCI_REPO@$DIGEST..."
skopeo inspect --raw --tls-verify=false "docker://$REGISTRY/$OCI_REPO@$DIGEST" > manifest.json

echo "Running skopeo standalone-verify..."
skopeo standalone-verify manifest.json "$REF" any "$SIG_FILE" --public-key-file "$KEY_FILE"

echo "Signing verification successful!"
exit 0
