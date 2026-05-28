#!/usr/bin/env python3
"""Helpers for GPG image signing in the publish action.

The pure functions are unit-tested; ``main()`` exposes two subcommands the
composite action shells out to: ``registries-d`` (print the skopeo registries.d
YAML) and ``manifest`` (write ``signing.json`` for the landing page).
"""

import argparse
import concurrent.futures
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
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


def backfill_signatures(
    index_path: str,
    sig_dir: str,
    site_dir: str,
    pages_url: str,
) -> None:
    """Download missing signatures referenced by the index from pages_url.

    :param index_path: path to the index/static file.
    :param sig_dir: lookaside root directory.
    :param site_dir: output directory for site files.
    :param pages_url: public URL where the signatures are hosted.
    """
    if not os.path.exists(index_path):
        return

    with open(index_path, encoding="utf-8") as fh:
        index_data = json.load(fh)

    paths = index_signature_relpaths(index_data, sig_dir)
    site_path = pathlib.Path(site_dir)
    site_path.mkdir(parents=True, exist_ok=True)
    resolved_site = site_path.resolve()
    pages_url = pages_url.rstrip("/")
    if not pages_url:
        return

    def clean_empty_parents(start_dir: pathlib.Path) -> None:
        curr = start_dir
        while curr != resolved_site and curr.is_dir():
            try:
                if not any(curr.iterdir()):
                    curr.rmdir()
                    curr = curr.parent
                else:
                    break
            except OSError:
                break

    def download_one(rel: str) -> None:
        try:
            local_file = (resolved_site / rel).resolve()
            local_file.relative_to(resolved_site)
        except (ValueError, RuntimeError):
            sys.stderr.write(f"::warning::Skipping invalid or unsafe path: {rel}\n")
            return

        if local_file.is_file():
            return

        local_file.parent.mkdir(parents=True, exist_ok=True)
        url = f"{pages_url}/{rel}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AetherPak-Signing-Backfill"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                local_file.write_bytes(resp.read())
            sys.stdout.write(f"Backfilled signature: {rel}\n")
        except urllib.error.HTTPError as e:
            if local_file.exists():
                local_file.unlink()
            clean_empty_parents(local_file.parent)
            sys.stderr.write(f"::warning::No deployed signature for {rel} (HTTP {e.code})\n")
        except Exception as e:
            if local_file.exists():
                local_file.unlink()
            clean_empty_parents(local_file.parent)
            sys.stderr.write(f"::warning::Failed to backfill signature {rel}: {e}\n")

    if paths:
        max_workers = min(10, len(paths))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(download_one, paths))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the ``registries-d``, ``manifest``, ``sigpaths`` and
    ``backfill`` subcommands.

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

    p_bf = sub.add_parser("backfill", help="download missing signatures from pages-url")
    p_bf.add_argument("--index-path", required=True)
    p_bf.add_argument("--sig-dir", default="sigs")
    p_bf.add_argument("--site-dir", required=True)
    p_bf.add_argument("--pages-url", required=True)

    args = ap.parse_args(argv)
    if args.cmd == "registries-d":
        sys.stdout.write(registries_d_yaml(args.registry, args.lookaside))
    elif args.cmd == "manifest":
        data = signing_manifest(args.sig_dir, args.key_filename, args.fingerprint, args.remote_name)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    elif args.cmd == "sigpaths":
        # No index means no signatures to backfill: stay silent rather than crash.
        if not os.path.exists(args.index_path):
            return 0
        with open(args.index_path, encoding="utf-8") as fh:
            index_data = json.load(fh)
        for rel in index_signature_relpaths(index_data, args.sig_dir):
            sys.stdout.write(rel + "\n")
    elif args.cmd == "backfill":
        backfill_signatures(args.index_path, args.sig_dir, args.site_dir, args.pages_url)
    return 0


if __name__ == "__main__":
    main()
