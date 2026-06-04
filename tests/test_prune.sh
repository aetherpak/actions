#!/usr/bin/env bash
# Unit test for prune-github-container-registry jq filtering logic
set -euo pipefail

echo "============================================="
echo "Running Container Registry Pruning Logic Tests"
echo "============================================="

# Create temporary files for active tags, digests, index, and versions
tags_file=$(mktemp)
digests_file=$(mktemp)
versions_file=$(mktemp)
index_file=$(mktemp)

cleanup() {
  rm -f "$tags_file" "$digests_file" "$versions_file" "$index_file"
}
trap cleanup EXIT

# 1. Mock Index JSON (showing active apps)
cat << 'EOF' > "$index_file"
{
  "Registry": "https://ghcr.io",
  "Results": [
    {
      "Name": "aetherpak/actions-demo",
      "Images": [
        {
          "Digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
          "MediaType": "application/vnd.oci.image.manifest.v1+json",
          "OS": "linux",
          "Architecture": "amd64",
          "Tags": ["stable"],
          "Labels": {
            "org.flatpak.ref": "app/org.example.App/x86_64/stable"
          }
        },
        {
          "Digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
          "MediaType": "application/vnd.oci.image.manifest.v1+json",
          "OS": "linux",
          "Architecture": "arm64",
          "Tags": ["beta"],
          "Labels": {
            "org.flatpak.ref": "app/org.example.Other/aarch64/beta"
          }
        }
      ]
    }
  ]
}
EOF

# 2. Extract active digests and tags (mimics workflow run)
ACTIVE_DIGESTS=$(jq -r '.Results[].Images[].Digest' "$index_file" | sort -u)
ACTIVE_TAGS=$(jq -r '
  .Results[].Images[] |
  select(.Labels["org.flatpak.ref"] != null) |
  .Labels["org.flatpak.ref"] |
  split("/") |
  if length >= 4 then
    "\(.[1] | gsub("\\."; "_"))-\(.[3])-\(.[2])"
  else
    empty
  end
' "$index_file" | sort -u)

echo "$ACTIVE_TAGS" > "$tags_file"
echo "$ACTIVE_DIGESTS" > "$digests_file"

echo "Reconstructed Active Tags:"
cat "$tags_file"
echo "Active Digests:"
cat "$digests_file"
echo ""

# 3. Mock Container registry versions
cat << 'EOF' > "$versions_file"
[
  {
    "id": 101,
    "name": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "metadata": {
      "container": {
        "tags": ["org_example_App-stable-x86_64"]
      }
    }
  },
  {
    "id": 102,
    "name": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
    "metadata": {
      "container": {
        "tags": ["org_example_App-beta-x86_64"]
      }
    }
  },
  {
    "id": 103,
    "name": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
    "metadata": {
      "container": {
        "tags": []
      }
    }
  },
  {
    "id": 104,
    "name": "sha256:5555555555555555555555555555555555555555555555555555555555555555",
    "metadata": {
      "container": {
        "tags": ["manual-tag"]
      }
    }
  },
  {
    "id": 105,
    "name": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
    "metadata": {
      "container": {
        "tags": ["org_example_Other-beta-aarch64"]
      }
    }
  },
  {
    "id": 106,
    "name": "sha256:7777777777777777777777777777777777777777777777777777777777777777",
    "metadata": {
      "container": {
        "tags": ["org_example_Other-stable-aarch64"]
      }
    }
  }
]
EOF

run_jq_test() {
  local safe_app_id="$1"
  jq \
    --rawfile tags_raw "$tags_file" \
    --rawfile digests_raw "$digests_file" \
    --arg safe_app_id "$safe_app_id" '
    ($tags_raw | split("\n") | map(select(length > 0))) as $active_tags |
    ($digests_raw | split("\n") | map(select(length > 0))) as $active_digests |

    def is_aetherpak_tag: test("^[a-zA-Z0-9_]+-[a-zA-Z0-9_.-]+-[a-zA-Z0-9_]+$");
    def is_app_tag(safe_id): startswith(safe_id + "-") and is_aetherpak_tag;

    .[] |
    .id as $id |
    .name as $digest |
    (.metadata?.container?.tags // []) as $tags |

    # Check active status
    ($active_digests | index($digest) != null) as $is_digest_active |
    (any($tags[]; . as $t | $active_tags | index($t) != null)) as $has_active_tag |
    ($is_digest_active or $has_active_tag) as $is_active |

    if $is_active then
      empty
    else
      if $safe_app_id != "" then
        if any($tags[]; is_app_tag($safe_app_id)) then
          {id: $id, digest: $digest, tags: $tags, reason: "Inactive version for app \($safe_app_id)"}
        else
          empty
        end
      else
        if ($tags | length) == 0 then
          {id: $id, digest: $digest, tags: $tags, reason: "Untagged and inactive version"}
        else
          if any($tags[]; is_aetherpak_tag) and all($tags[]; is_aetherpak_tag) then
            {id: $id, digest: $digest, tags: $tags, reason: "All tags are inactive aetherpak tags"}
          else
            empty
          end
        end
      end
    end
  ' "$versions_file" | jq -s '.'
}

# --- TEST 1: Global Prune (safe_app_id = "") ---
echo "TEST 1: Global Prune..."
results_global=$(run_jq_test "")
echo "$results_global" | jq -c '.[]'

# Assertions for Global Prune:
# - Version 101: stable image, MUST NOT be pruned (active).
# - Version 102: obsolete tag of org.example.App, MUST be pruned.
# - Version 103: untagged, MUST be pruned.
# - Version 104: manually tagged, MUST NOT be pruned.
# - Version 105: active tag of org.example.Other, MUST NOT be pruned.
# - Version 106: obsolete tag of org.example.Other, MUST be pruned.

pruned_ids=$(echo "$results_global" | jq -r '.[].id' | sort -n | tr '\n' ' ')
expected_pruned="102 103 106 "
if [ "$pruned_ids" != "$expected_pruned" ]; then
  echo "TEST 1 FAILED! Expected pruned IDs: $expected_pruned, got: $pruned_ids" >&2
  exit 1
fi
echo "TEST 1 PASSED: Successfully pruned 102 (obsolete app tag), 103 (untagged), and 106 (obsolete other tag)."
echo ""

# --- TEST 2: Specific App Prune (safe_app_id = "org_example_App") ---
echo "TEST 2: Prune for app 'org.example.App'..."
results_app=$(run_jq_test "org_example_App")
echo "$results_app" | jq -c '.[]'

# Assertions for App Prune:
# - Version 102: obsolete tag of org.example.App, MUST be pruned.
# - All other versions MUST NOT be pruned (even untagged 103, manual-tag 104, and other app 106).

pruned_app_ids=$(echo "$results_app" | jq -r '.[].id' | sort -n | tr '\n' ' ')
expected_app_pruned="102 "
if [ "$pruned_app_ids" != "$expected_app_pruned" ]; then
  echo "TEST 2 FAILED! Expected pruned IDs: $expected_app_pruned, got: $pruned_app_ids" >&2
  exit 1
fi
echo "TEST 2 PASSED: Successfully pruned only 102 (obsolete app tag)."
echo ""

echo "All tests passed successfully!"
exit 0
