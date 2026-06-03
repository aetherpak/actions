#!/usr/bin/env bash
# Start a local OCI registry container on port 5001
set -euo pipefail

PORT="${1:-5001}"
CONTAINER_NAME="registry"

# Clean up any existing container
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Start registry
docker run -d -p "$PORT:5000" --name "$CONTAINER_NAME" registry:2

# Wait for registry to be ready
echo "Waiting for registry to start on port $PORT..."
for _ in {1..10}; do
  if curl -s "http://localhost:$PORT/v2/" >/dev/null; then
    echo "Registry is ready!"
    exit 0
  fi
  sleep 1
done

echo "Error: Registry failed to start in time." >&2
exit 1
