#!/usr/bin/env bash
# Verify that each expected record cell exists under a records directory.
# A cell is only complete when both record.json and labels.json are present;
# the CLI skips a cell missing either file.
# Usage: verify_record_cells.sh <records-dir> <cell>...
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <records-dir> <cell>..." >&2
  exit 1
fi

RECORDS_DIR="$1"
shift

missing=0
for cell in "$@"; do
  for file in record.json labels.json; do
    if [ ! -f "$RECORDS_DIR/$cell/$file" ]; then
      echo "Error: missing $file in record cell $cell" >&2
      missing=1
    fi
  done
done

if [ "$missing" -ne 0 ]; then
  echo "Records tree:" >&2
  find "$RECORDS_DIR" -maxdepth 3 -type f | sort >&2 || true
  exit 1
fi

echo "Record cells verified successfully."
