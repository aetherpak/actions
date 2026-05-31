#!/usr/bin/env bash
# Shared fixture: the mock app/org.flatpak.MockApp/x86_64/stable OSTree repo the
# integration jobs import. Pass a target path; defaults to tests/mock_repo.
set -euo pipefail
repo="${1:-tests/mock_repo}"
ostree init --mode=archive --repo="$repo"
mkdir -p tests/mock_contents
cat > tests/mock_contents/metadata <<EOF
[Application]
name=org.flatpak.MockApp
runtime=org.freedesktop.Platform/x86_64/23.08
sdk=org.freedesktop.Sdk/x86_64/23.08
EOF
ostree commit --repo="$repo" --branch=app/org.flatpak.MockApp/x86_64/stable -m "mock app commit" tests/mock_contents
