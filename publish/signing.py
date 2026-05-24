#!/usr/bin/env python3
"""Helpers for GPG image signing in the publish action.

The pure functions are unit-tested; ``main()`` exposes two subcommands the
composite action shells out to: ``registries-d`` (print the skopeo registries.d
YAML) and ``manifest`` (write ``signing.json`` for the landing page).
"""

import argparse
import json
import sys
from typing import Any

#: An OCI registry index document (the ``index/static`` JSON).
Index = dict[str, Any]


def signature_relpath(repo: str, digest: str, sig_dir: str = "sigs") -> str:
    """Site-relative path skopeo writes a detached signature to.

    skopeo's containers/image lookaside layout is
    ``<sig-dir>/<repo>@sha256=<hex>/signature-1`` — the repo namespace is
    preserved as directories and the digest is joined as ``@sha256=<hex>``.

    :param repo: OCI repo name, e.g. ``owner/app``; surrounding ``/`` stripped.
    :param digest: image digest as ``sha256:<hex>``.
    :param sig_dir: lookaside root directory; surrounding ``/`` stripped.
    :returns: the lookaside-relative path of the detached signature.
    :raises ValueError: if ``digest`` is not of the form ``<algo>:<hex>``.
    """
    if ":" not in digest:
        raise ValueError(f"digest must be 'sha256:<hex>', got {digest!r}")
    algo, hexd = digest.split(":", 1)
    sig_dir = sig_dir.strip("/")
    repo = repo.strip("/")
    return f"{sig_dir}/{repo}@{algo}={hexd}/signature-1"


def index_signature_relpaths(index_data: Index, sig_dir: str = "sigs") -> list[str]:
    """Signature relpaths for the installable images in a merged index.

    Used to backfill signatures a prior run wrote (the index is cumulative, but
    the site is replaced on deploy). Skips entries missing a Name or Digest, and
    entries without ``org.flatpak.metadata`` — those are non-installable stubs
    (e.g. old pre-signing refs) that no client can pull, so they need no
    signature and must not trigger backfill warnings.

    :param index_data: a merged OCI index.
    :param sig_dir: lookaside root directory.
    :returns: one :func:`signature_relpath` per installable image, in index order.
    """
    paths = []
    for result in index_data.get("Results", []):
        name = result.get("Name", "")
        for image in result.get("Images", []):
            digest = image.get("Digest", "")
            metadata = (image.get("Labels") or {}).get("org.flatpak.metadata")
            if name and digest and metadata:
                paths.append(signature_relpath(name, digest, sig_dir))
    return paths


def registries_d_yaml(registry: str, lookaside_abs: str) -> str:
    """registries.d YAML mapping a registry host to a file:// staging lookaside.

    :param registry: registry host the mapping applies to, e.g. ``ghcr.io``.
    :param lookaside_abs: absolute path of the staging lookaside dir; ``file://``
        requires an absolute path.
    :returns: the registries.d document as a YAML string.
    :raises ValueError: if ``lookaside_abs`` is not absolute.
    """
    if not lookaside_abs.startswith("/"):
        raise ValueError(f"lookaside path must be absolute, got {lookaside_abs!r}")
    return f"docker:\n  {registry}:\n    lookaside-staging: file://{lookaside_abs}\n"


def signing_manifest(
    sig_dir: str, key_filename: str, fingerprint: str, remote_name: str
) -> dict[str, object]:
    """Body of ``signing.json`` consumed by the landing page.

    :param sig_dir: lookaside root directory; surrounding ``/`` stripped.
    :param key_filename: public key filename within ``sig_dir``.
    :param fingerprint: signing key fingerprint.
    :param remote_name: flatpak remote name the signature applies to.
    :returns: the ``signing.json`` payload.
    """
    sig_dir = sig_dir.strip("/")
    return {
        "enabled": True,
        "lookaside": sig_dir,
        "publicKey": f"{sig_dir}/{key_filename}",
        "fingerprint": fingerprint,
        "remoteName": remote_name,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the ``registries-d``, ``manifest`` and ``sigpaths`` subcommands.

    :param argv: argument vector; defaults to :data:`sys.argv` when ``None``.
    :returns: process exit code (always ``0``; errors raise).
    """
    ap = argparse.ArgumentParser(description="GPG signing helpers for publish.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_reg = sub.add_parser("registries-d", help="print registries.d YAML")
    p_reg.add_argument("--registry", required=True)
    p_reg.add_argument("--lookaside", required=True)

    p_man = sub.add_parser("manifest", help="write signing.json")
    p_man.add_argument("--out", required=True)
    p_man.add_argument("--sig-dir", default="sigs")
    p_man.add_argument("--key-filename", default="key.asc")
    p_man.add_argument("--fingerprint", required=True)
    p_man.add_argument("--remote-name", default="aetherpak")

    p_paths = sub.add_parser("sigpaths", help="print signature relpaths for an index")
    p_paths.add_argument("--index-path", required=True)
    p_paths.add_argument("--sig-dir", default="sigs")

    args = ap.parse_args(argv)
    if args.cmd == "registries-d":
        sys.stdout.write(registries_d_yaml(args.registry, args.lookaside))
    elif args.cmd == "manifest":
        data = signing_manifest(args.sig_dir, args.key_filename, args.fingerprint, args.remote_name)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    elif args.cmd == "sigpaths":
        with open(args.index_path, encoding="utf-8") as fh:
            index_data = json.load(fh)
        for rel in index_signature_relpaths(index_data, args.sig_dir):
            sys.stdout.write(rel + "\n")
    return 0


if __name__ == "__main__":
    main()
