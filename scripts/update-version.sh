#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <new_version>"
  exit 1
fi

NEW_VER="$1"

# Read path relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Ensure we run from root directory
cd "$ROOT_DIR"

OLD_VER=$(tr -d '[:space:]' < cli-version.txt)

if [ "$OLD_VER" = "$NEW_VER" ]; then
  echo "Version is already $NEW_VER"
  exit 0
fi

echo "Updating version from $OLD_VER to $NEW_VER..."

# 1. Update cli-version.txt
echo "$NEW_VER" > cli-version.txt

# 2. Update .github/workflows/publish.yml
sed -i "s/default: \"$OLD_VER\"/default: \"$NEW_VER\"/g" .github/workflows/publish.yml

# 3. Update .github/workflows/test.yml
sed -i "s/version: $OLD_VER/version: $NEW_VER/g" .github/workflows/test.yml
sed -i "s/cli:$OLD_VER/cli:$NEW_VER/g" .github/workflows/test.yml

# 4. Update docs/site/index.html
sed -i "s/Default <code>$OLD_VER<\/code>/Default <code>$NEW_VER<\/code>/g" docs/site/index.html

# 5. Update README.md
sed -i "s/Default <code>$OLD_VER<\/code>/Default <code>$NEW_VER<\/code>/g" README.md || true

# 6. Update ARCHITECTURE.md
sed -i "s/\`$OLD_VER\`/\`$NEW_VER\`/g" ARCHITECTURE.md
sed -i "s/:\`$OLD_VER\`/:\`$NEW_VER\`/g" ARCHITECTURE.md
sed -i "s/:$OLD_VER/:$NEW_VER/g" ARCHITECTURE.md

# 7. Update composite actions
for f in action.yml build/action.yml plan/action.yml prep-bundle/action.yml publish-oci/action.yml publish-site/action.yml publish/action.yml; do
  sed -i "s/default: \"$OLD_VER\"/default: \"$NEW_VER\"/g" "$f"
done

echo "Done!"
