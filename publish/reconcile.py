#!/usr/bin/env python3
"""Drop index entries whose OCI image no longer exists in the registry."""

import argparse
import json
import logging
import os
import subprocess
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("reconcile")

#: An OCI registry index document and one of its image entries.
Index = dict[str, Any]
Image = dict[str, Any]

# skopeo stderr fragments that mean the manifest is definitively gone, as opposed
# to a transient or auth failure, where the entry must be kept.
NOT_FOUND_SIGNATURES = ("manifest unknown", "name unknown", "404")


def remove_digests(index: Index, digests: Iterable[str]) -> list[Image]:
    """Remove images whose ``Digest`` is in ``digests``, mutating ``index``.

    Results left with no images are dropped, so an emptied index stays valid.

    :param index: the index to prune in place.
    :param digests: digests to remove.
    :returns: the removed image dicts.
    """
    digests = set(digests)
    removed = []
    results = index.get("Results", [])
    for result in results:
        kept = []
        for img in result.get("Images", []):
            if img.get("Digest") in digests:
                removed.append(img)
            else:
                kept.append(img)
        result["Images"] = kept
    index["Results"] = [r for r in results if r.get("Images")]
    return removed


def registry_host(registry: str) -> str:
    """Strip the scheme from the index ``Registry`` URL for skopeo.

    :param registry: registry URL or bare host, e.g. ``https://ghcr.io``.
    :returns: the ``host[:port]`` skopeo expects.
    """
    parsed = urlparse(registry)
    return parsed.netloc or parsed.path


def image_present(host: str, name: str, digest: str, insecure: bool) -> bool:
    """Check whether an image manifest still exists in the registry.

    Any failure other than a definitive not-found (auth, 5xx, timeout, DNS) is
    treated as present, so a transient problem never drops a valid entry.

    :param host: registry host, e.g. ``ghcr.io`` (see :func:`registry_host`).
    :param name: OCI image name, e.g. ``owner/repo``.
    :param digest: manifest digest, ``sha256:...``.
    :param insecure: pass ``--tls-verify=false`` to skopeo.
    :returns: ``True`` if present or on any non-definitive error; ``False`` only
        when skopeo reports the manifest is gone.
    """
    cmd = ["skopeo", "inspect"]
    if insecure:
        cmd.append("--tls-verify=false")
    cmd.append(f"docker://{host}/{name}@{digest}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True
    if any(sig in proc.stderr.lower() for sig in NOT_FOUND_SIGNATURES):
        return False
    log.warning(
        "keeping %s@%s: inspect failed, not a definitive not-found: %s",
        name,
        digest,
        proc.stderr.strip(),
    )
    return True


def main() -> None:
    """CLI entry point: drop index entries whose image is gone, in place."""
    parser = argparse.ArgumentParser(description="Reconcile the index against the registry.")
    parser.add_argument("--index-path", required=True, help="Path to index/static")
    parser.add_argument(
        "--registry", required=True, help="Index Registry URL (e.g. https://ghcr.io)"
    )
    parser.add_argument("--insecure", action="store_true", help="skopeo --tls-verify=false")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # A missing index is a valid no-op: first publish before any cell has merged,
    # or reconcile-only against a fresh repo with no deployed index yet.
    if not os.path.exists(args.index_path):
        log.info("no index at %s — nothing to reconcile", args.index_path)
        return

    with open(args.index_path, encoding="utf-8") as f:
        index = json.load(f)

    host = registry_host(args.registry)
    gone = []
    for result in index.get("Results", []):
        name = result.get("Name")
        for img in result.get("Images", []):
            digest = img.get("Digest")
            if name and digest and not image_present(host, name, digest, args.insecure):
                log.info("dropping %s@%s (not found in registry)", name, digest)
                gone.append(digest)

    removed = remove_digests(index, gone)

    with open(args.index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    log.info("reconciled %s: removed %d image(s)", args.index_path, len(removed))


if __name__ == "__main__":
    main()
