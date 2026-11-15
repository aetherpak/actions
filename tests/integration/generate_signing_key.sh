#!/usr/bin/env bash
# Usage: generate_signing_key.sh [passphrase]
set -euo pipefail

PASSPHRASE="${1:-}"
VAR_NAME="AEP_GPG_KEY"
PROTECTION="%no-protection"
EXPORT_ARGS=()
if [ -n "$PASSPHRASE" ]; then
  VAR_NAME="AEP_GPG_KEY_PROTECTED"
  PROTECTION="Passphrase: $PASSPHRASE"
  EXPORT_ARGS=(--pinentry-mode loopback --passphrase "$PASSPHRASE")
fi

GNUPGHOME="$(mktemp -d)"
export GNUPGHOME

cat > "$GNUPGHOME/params" <<EOF
Key-Type: RSA
Key-Length: 2048
Name-Real: AetherPak CI
Name-Email: ci@aetherpak.local
Expire-Date: 0
$PROTECTION
%commit
EOF

echo "Generating ephemeral GPG key..."
gpg --batch --gen-key "$GNUPGHOME/params"

# If running inside a GitHub Action, export to GITHUB_ENV
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "Exporting GPG key to GITHUB_ENV..."
  {
    echo "${VAR_NAME}<<EOF"
    gpg --batch "${EXPORT_ARGS[@]}" --armor --export-secret-keys
    echo "EOF"
  } >> "$GITHUB_ENV"
else
  # Running locally, output to stdout
  gpg --batch "${EXPORT_ARGS[@]}" --armor --export-secret-keys
fi

# Cleanup GNUPGHOME
rm -rf "$GNUPGHOME"
echo "Done generating GPG key."
exit 0
