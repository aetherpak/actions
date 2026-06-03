#!/usr/bin/env bash
# Test reconcile behavior by injecting a ghost ref, serving, rebuilding, and asserting cleanup
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <site_dir> <records_dir> <reconciled_site_dir> <pages_port> <remote_name>" >&2
  exit 1
fi

SITE_DIR="$1"
RECORDS_DIR="$2"
REC_SITE_DIR="$3"
PORT="$4"
REMOTE_NAME="$5"

STATIC_INDEX="$SITE_DIR/index/static"

if [ ! -f "$STATIC_INDEX" ]; then
  echo "Error: Base index/static does not exist at $STATIC_INDEX" >&2
  exit 1
fi

echo "Injecting ghost registry entry to test reconciliation..."
ghost="sha256:$(printf '0%.0s' $(seq 64))"
jq --arg d "$ghost" '.Results += [{"Name":"aetherpak/ghost","Images":[{"Digest":$d,"Architecture":"amd64","Labels":{"org.flatpak.ref":"app/org.flatpak.Ghost/x86_64/stable"},"Tags":["stable"]}]}]' \
  "$STATIC_INDEX" > "$STATIC_INDEX.new"
mv "$STATIC_INDEX.new" "$STATIC_INDEX"

# Start local server to serve the page index
echo "Starting temporary web server on port $PORT to serve pages URL..."
python3 -m http.server "$PORT" --directory "$SITE_DIR" & srv=$!

# Ensure we kill the server on exit
cleanup() {
  echo "Stopping web server..."
  kill "$srv" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1

# Re-run build-site with reconcile
echo "Running aetherpak build-site with --reconcile..."
aetherpak build-site --records-dir "$RECORDS_DIR" --site-dir "$REC_SITE_DIR" \
  --pages-url "http://localhost:$PORT" --insecure --reconcile \
  --remote-name "$REMOTE_NAME" --allow-unsigned

REC_INDEX="$REC_SITE_DIR/index/static"
if [ ! -f "$REC_INDEX" ]; then
  echo "Error: Reconciled index/static not generated at $REC_INDEX" >&2
  exit 1
fi

names="$(jq -r '.Results[].Name' "$REC_INDEX")"
echo "Reconciled index entry names:"
echo "$names"

# Ensure mock-app remains
if ! echo "$names" | grep -qx 'aetherpak/mock-app'; then
  echo "Error: 'aetherpak/mock-app' should remain in the index!" >&2
  exit 1
fi

# Ensure ghost is removed
if echo "$names" | grep -qx 'aetherpak/ghost'; then
  echo "Error: 'aetherpak/ghost' should have been reconciled away!" >&2
  exit 1
fi

echo "Reconcile integration check completed successfully!"
exit 0
