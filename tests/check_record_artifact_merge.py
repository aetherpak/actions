#!/usr/bin/env python3
"""Guard the publish-site records download against issue #142.

One publish-oci matrix cell can upload several record cells (an app plus its
.Debug/.Locale companions). actions/download-artifact extracts a lone pattern
match directly into `path`, so the job must merge artifacts into `_records`
with `merge-multiple: true`. A step that copies the contents of each downloaded
directory collapses those cells into one record.
"""

import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/publish.yml")
STEP_HEADER = "      - name: Download records\n"


def main() -> int:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines(keepends=True)
    try:
        start = lines.index(STEP_HEADER)
    except ValueError:
        print(f"{WORKFLOW}: no 'Download records' step", file=sys.stderr)
        return 1

    block = []
    for line in lines[start + 1 :]:
        if line.startswith("      - "):
            break
        block.append(line)
    step = "".join(block)

    errors = []
    if "merge-multiple: true" not in step:
        errors.append("the record download must set merge-multiple: true")
    if "path: _records" not in step:
        errors.append("the record download must extract into _records")
    if any("_records_in" in line for line in lines):
        errors.append("record cells must not be flattened (_records_in)")

    if errors:
        for error in errors:
            print(f"{WORKFLOW}: {error}", file=sys.stderr)
        return 1

    print("Record artifact download verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
