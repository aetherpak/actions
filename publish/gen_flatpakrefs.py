#!/usr/bin/env python3
"""Generate one-click ``.flatpakref`` files from the static OCI registry index.

A ``.flatpakrepo`` only adds the remote; a ``.flatpakref`` adds the remote *and*
installs a specific app in one step. We emit one ref per installable
``(app-id, channel)`` found in ``index/static``. When signing is on, the ref
carries ``GPGKey`` (base64 of the binary public key, the trust enforcer) and
``SignatureLookaside`` (OCI signature URL) so the one-click install is verified;
unlike ``.flatpakrepo``, the ref format supports the lookaside key.

The pure functions are unit-tested; ``main()`` is what the composite action
shells out to.
"""

import argparse
import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

log = logging.getLogger("gen_flatpakrefs")

#: An OCI registry index document (the ``index/static`` JSON).
Index = dict[str, Any]


def app_title(appdata_xml: str, app_id: str) -> str:
    """Human title from AppStream appdata, falling back to the app-id's leaf.

    Mirrors the landing page's ``appMeta``: prefer the ``<component><name>``
    without an ``xml:lang`` attribute (the C locale), else the first one. Any
    parse failure falls back to the leaf.

    :param appdata_xml: AppStream appdata XML, or empty if none is available.
    :param app_id: the app-id, used for the leaf fallback (e.g. ``org.x.App`` -> ``App``).
    :returns: the chosen display title.
    """
    fallback = app_id.rsplit(".", 1)[-1]
    if not appdata_xml:
        return fallback
    try:
        root = ET.fromstring(appdata_xml)
        # appdata root is <component>; a catalog wraps it in <components>.
        comp = root if root.tag.rsplit("}", 1)[-1] == "component" else root.find(".//component")
        if comp is None:
            return fallback
        names = comp.findall("name")
        if not names:
            return fallback
        XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
        chosen = next((n for n in names if not n.get(XML_LANG)), names[0])
        text = (chosen.text or "").strip()
        return text or fallback
    except Exception:
        return fallback


def ref_filename(app_id: str, branch: str) -> str:
    """Filename for an app/channel ref.

    A valid flatpak ref is ``app/<id>/<arch>/<branch>`` (a branch has no ``/``),
    but replace ``/`` defensively to keep filenames path-safe. This scheme is
    mirrored verbatim by the landing page JS (``publish/index.html``) — keep the
    two in sync.

    :param app_id: the app-id, e.g. ``org.example.App``.
    :param branch: the channel/branch, e.g. ``stable``.
    :returns: the ``.flatpakref`` filename.
    """
    safe_branch = branch.replace("/", "-")
    return f"{app_id}-{safe_branch}.flatpakref"


def _render(
    title: str,
    app_id: str,
    branch: str,
    url: str,
    remote_name: str,
    runtime_repo: str,
    gpg_key_b64: str | None = None,
    signature_lookaside: str | None = None,
) -> str:
    """Render one ``.flatpakref`` body; emits signing keys only if both are given."""
    lines = [
        "[Flatpak Ref]",
        f"Title={title}",
        f"Name={app_id}",
        f"Branch={branch}",
        f"Url={url}",
        f"SuggestRemoteName={remote_name}",
    ]
    if runtime_repo:
        lines.append(f"RuntimeRepo={runtime_repo}")
    if gpg_key_b64 and signature_lookaside:
        lines.append(f"GPGKey={gpg_key_b64}")
        lines.append(f"SignatureLookaside={signature_lookaside}")
    return "\n".join(lines) + "\n"


def flatpakref_files(
    index_data: Index,
    url: str,
    remote_name: str,
    runtime_repo: str,
    gpg_key_b64: str | None = None,
    signature_lookaside: str | None = None,
) -> dict[str, str]:
    """Map ``filename -> .flatpakref content`` for every installable app/channel.

    Skips images without ``org.flatpak.metadata`` — non-installable stubs (e.g.
    old pre-signing refs) that no client can pull, matching the filter used by
    the landing page and ``signing.index_signature_relpaths``. Images are grouped
    by ``(app-id, branch)`` so multiple arches collapse to one ref; the title is
    taken from whichever image carries appdata.

    :param index_data: a merged OCI index.
    :param url: remote URL, e.g. ``oci+https://owner.github.io/repo``.
    :param remote_name: suggested flatpak remote name.
    :param runtime_repo: ``.flatpakrepo`` URL for the runtime; omitted if empty.
    :param gpg_key_b64: base64 of the binary GPG public key; signing keys are
        emitted only when this and ``signature_lookaside`` are both set.
    :param signature_lookaside: OCI signature lookaside URL (see above).
    :returns: filename -> ``.flatpakref`` body for each installable app/channel.
    """
    apps: dict[tuple[str, str], dict[str, str]] = {}  # (id, branch) -> {"appdata": str}
    for result in index_data.get("Results", []):
        for image in result.get("Images", []):
            labels = image.get("Labels") or {}
            ref = labels.get("org.flatpak.ref")
            if not ref or not labels.get("org.flatpak.metadata"):
                continue
            # Only well-formed app refs: app/<id>/<arch>/<branch>. This skips
            # runtime/* refs (no app flatpakref for those) and anything malformed.
            parts = ref.split("/")
            if len(parts) != 4 or parts[0] != "app":
                continue
            _, app_id, _arch, branch = parts
            if not app_id or not branch:
                continue
            entry = apps.setdefault((app_id, branch), {"appdata": ""})
            if not entry["appdata"]:
                entry["appdata"] = labels.get("org.freedesktop.appstream.appdata", "")

    files: dict[str, str] = {}
    for (app_id, branch), entry in apps.items():
        content = _render(
            title=app_title(entry["appdata"], app_id),
            app_id=app_id,
            branch=branch,
            url=url,
            remote_name=remote_name,
            runtime_repo=runtime_repo,
            gpg_key_b64=gpg_key_b64,
            signature_lookaside=signature_lookaside,
        )
        files[ref_filename(app_id, branch)] = content
    return files


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: write a ``.flatpakref`` per installable app/channel into ``--out-dir``.

    :param argv: argument vector; defaults to :data:`sys.argv` when ``None``.
    """
    parser = argparse.ArgumentParser(
        description="Generate per-app .flatpakref files from the OCI index."
    )
    parser.add_argument("--index-path", required=True, help="Path to index/static")
    parser.add_argument(
        "--out-dir", required=True, help="Directory to write .flatpakref files into"
    )
    parser.add_argument(
        "--url", required=True, help="Remote URL (e.g. oci+https://owner.github.io/repo)"
    )
    parser.add_argument("--remote-name", required=True, help="Suggested remote name")
    parser.add_argument(
        "--runtime-repo", default="", help=".flatpakrepo URL for the runtime (empty to omit)"
    )
    parser.add_argument(
        "--gpg-key-base64-file", help="File with base64 of the binary GPG public key (signed only)"
    )
    parser.add_argument("--signature-lookaside", help="OCI signature lookaside URL (signed only)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with open(args.index_path, encoding="utf-8") as f:
        index_data = json.load(f)

    gpg_key_b64 = None
    if args.gpg_key_base64_file:
        with open(args.gpg_key_base64_file, encoding="utf-8") as f:
            gpg_key_b64 = f.read().strip()

    files = flatpakref_files(
        index_data,
        url=args.url,
        remote_name=args.remote_name,
        runtime_repo=args.runtime_repo,
        gpg_key_b64=gpg_key_b64,
        signature_lookaside=args.signature_lookaside,
    )

    os.makedirs(args.out_dir, exist_ok=True)
    for name, content in sorted(files.items()):
        path = os.path.join(args.out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log.info("wrote %s", path)

    log.info("generated %d .flatpakref file(s) in %s", len(files), args.out_dir)


if __name__ == "__main__":
    main()
