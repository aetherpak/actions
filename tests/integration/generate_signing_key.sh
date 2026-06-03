#!/usr/bin/env bash
# Generate an ephemeral secret key for signing tests
set -euo pipefail

GNUPGHOME="$(mktemp -d)"
export GNUPGHOME

cat > "$GNUPGHOME/params" <<EOF
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: AetherPak CI
Name-Email: ci@aetherpak.local
Expire-Date: 0
%commit
EOF

echo "Generating ephemeral GPG key..."
gpg --batch --gen-key "$GNUPGHOME/params"

# If running inside a GitHub Action, export to GITHUB_ENV
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "Exporting GPG key to GITHUB_ENV..."
  {
    echo "AEP_GPG_KEY<<EOF"
    gpg --armor --export-secret-keys
    echo "EOF"
  } >> "$GITHUB_ENV"
else
  # Running locally, output to stdout
  gpg --armor --export-secret-keys
fi

# Cleanup GNUPGHOME
rm -rf "$GNUPGHOME"
echo "Done generating GPG key."
exit 0
