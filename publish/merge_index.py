#!/usr/bin/env python3
"""Merge one built Flatpak image into the static OCI registry index (index/static)."""

import argparse
import json
import logging
import os
from typing import Any

log = logging.getLogger("merge_index")

#: An OCI registry index document (the ``index/static`` JSON), as loaded by :func:`json.load`.
Index = dict[str, Any]

# Flatpak architecture name -> OCI/Go architecture name.
ARCH_MAP = {
    "x86_64": "amd64",
    "aarch64": "arm64",
    "i386": "386",
    "i586": "386",
    "i686": "386",
    "arm": "arm",
    "armv7hl": "arm",
}


def map_arch(flatpak_arch: str) -> str:
    """Translate a Flatpak architecture name to its OCI/Go equivalent.

    :param flatpak_arch: Flatpak arch, e.g. ``x86_64`` (case-insensitive).
    :returns: the mapped OCI arch, or the lower-cased input if unknown.
    """
    key = flatpak_arch.lower()
    return ARCH_MAP.get(key, key)


def merge_index_data(
    index_data: Index,
    registry: str,
    name: str,
    digest: str,
    ref: str,
    tag: str,
    oci_arch: str,
    labels: dict[str, str] | None = None,
) -> Index:
    """Insert or replace one image in the index, returning it mutated in place.

    An image is keyed by ``(ref, oci_arch)``: a matching entry is overwritten,
    otherwise the image is appended (creating the ``Name`` result if needed).

    :param index_data: the index to update.
    :param registry: registry URL, stored as the index ``Registry``.
    :param name: OCI image name, e.g. ``owner/repo``.
    :param digest: OCI manifest digest, ``sha256:...``.
    :param ref: Flatpak ref, stored as the ``org.flatpak.ref`` label.
    :param tag: image tag, e.g. ``stable``.
    :param oci_arch: OCI architecture (see :func:`map_arch`).
    :param labels: full OCI label set to embed; ``org.flatpak.ref`` is added if
        absent so the entry stays resolvable from the ref alone.
    :returns: the same ``index_data`` object, mutated.
    """
    index_data["Registry"] = registry

    # flatpak resolves and installs a ref from the full org.flatpak.* label set
    # (commit, metadata, sizes), so carry it through; fall back to the ref alone.
    labels = dict(labels) if labels else {}
    labels.setdefault("org.flatpak.ref", ref)

    results: list[Any] = index_data.setdefault("Results", [])
    result: dict[str, Any] | None = next((r for r in results if r.get("Name") == name), None)
    if result is None:
        result = {"Name": name, "Images": []}
        results.append(result)

    new_image: dict[str, Any] = {
        "Digest": digest,
        "MediaType": "application/vnd.oci.image.manifest.v1+json",
        "OS": "linux",
        "Architecture": oci_arch,
        "Labels": labels,
        "Tags": [tag],
    }

    # One image per (ref, arch): replace in place if present, else append.
    images: list[Any] = result.setdefault("Images", [])
    for i, img in enumerate(images):
        if (
            img.get("Labels", {}).get("org.flatpak.ref") == ref
            and img.get("Architecture") == oci_arch
        ):
            images[i] = new_image
            break
    else:
        images.append(new_image)

    return index_data


def load_index(path: str, registry: str) -> Index:
    """Load an existing index, or return a fresh empty one.

    A missing or unparseable file yields a new ``{"Registry": ..., "Results": []}``
    so a corrupt index never aborts the run.

    :param path: path to the ``index/static`` file.
    :param registry: registry URL seeded into a freshly created index.
    :returns: the parsed or newly created index.
    """
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("could not parse %s, starting fresh: %s", path, e)
    return {"Registry": registry, "Results": []}


def main() -> None:
    """CLI entry point: merge one built image into the index file in place."""
    parser = argparse.ArgumentParser(
        description="Merge a Flatpak image into the OCI registry index."
    )
    parser.add_argument("--index-path", required=True, help="Path to the index/static file")
    parser.add_argument("--registry", required=True, help="Registry URL (e.g. https://ghcr.io)")
    parser.add_argument("--name", required=True, help="OCI image name (e.g. owner/repo)")
    parser.add_argument("--digest", required=True, help="OCI image digest (sha256:...)")
    parser.add_argument("--ref", required=True, help="Flatpak ref (org.flatpak.ref)")
    parser.add_argument("--labels-file", help="JSON file with the full OCI image label set")
    parser.add_argument("--tag", required=True, help="Image tag (e.g. stable)")
    parser.add_argument("--arch", required=True, help="Flatpak architecture (e.g. x86_64)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    labels = None
    if args.labels_file and os.path.exists(args.labels_file):
        with open(args.labels_file, encoding="utf-8") as f:
            labels = json.load(f)

    oci_arch = map_arch(args.arch)
    index = load_index(args.index_path, args.registry)
    index = merge_index_data(
        index, args.registry, args.name, args.digest, args.ref, args.tag, oci_arch, labels=labels
    )

    os.makedirs(os.path.dirname(args.index_path), exist_ok=True)
    with open(args.index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    log.info("updated %s: %s (%s) -> %s", args.index_path, args.ref, oci_arch, args.digest)


if __name__ == "__main__":
    main()
