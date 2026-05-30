#!/usr/bin/env bash
# Unit test for plan/runtime-tag.jq: runtime -> flathub container tag.
set -uo pipefail
cd "$(dirname "$0")/.."

FILTER="plan/runtime-tag.jq"
fail=0

check() {
  local name="$1" input="$2" expected="$3"
  local got
  got="$(jq -c -f "$FILTER" <<<"$input" 2>/dev/null)"
  if [ "$got" != "$expected" ]; then
    echo "FAIL: $name"
    echo "  input:    $input"
    echo "  expected: $expected"
    echo "  got:      $got"
    fail=1
  else
    echo "ok: $name"
  fi
}

check_err() {
  local name="$1" input="$2"
  if jq -c -f "$FILTER" <<<"$input" >/dev/null 2>&1; then
    echo "FAIL: $name (expected non-zero exit)"
    fail=1
  else
    echo "ok: $name (errored as expected)"
  fi
}

# Manifest-mode rows: reverse-DNS runtime + runtime-version -> <prefix>-<version>.
check "gnome manifest" \
  '[{"runtime":"org.gnome.Platform","runtime-version":"50"}]' \
  '[{"runtime":"org.gnome.Platform","runtime-version":"50","runtime-tag":"gnome-50"}]'
check "freedesktop manifest (dotted version stays a string)" \
  '[{"runtime":"org.freedesktop.Platform","runtime-version":"24.08"}]' \
  '[{"runtime":"org.freedesktop.Platform","runtime-version":"24.08","runtime-tag":"freedesktop-24.08"}]'
check "kde compound version" \
  '[{"runtime":"org.kde.Platform","runtime-version":"5.15-24.08"}]' \
  '[{"runtime":"org.kde.Platform","runtime-version":"5.15-24.08","runtime-tag":"kde-5.15-24.08"}]'

# Config-mode row: runtime is already a flathub tag, no runtime-version -> passthrough.
check "config passthrough" \
  '[{"runtime":"gnome-50"}]' \
  '[{"runtime":"gnome-50","runtime-tag":"gnome-50"}]'

# Empty matrix.
check "empty" '[]' '[]'

# Unsupported runtime fails fast.
check_err "elementary unsupported" \
  '[{"runtime":"io.elementary.Platform","runtime-version":"8"}]'
# Manifest runtime missing its version fails fast.
check_err "manifest missing runtime-version" \
  '[{"runtime":"org.gnome.Platform"}]'

if [ "$fail" -ne 0 ]; then echo "TESTS FAILED"; exit 1; fi
echo "ALL PASS"
