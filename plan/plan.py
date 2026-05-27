#!/usr/bin/env python3
"""Expand apps.yaml into a build matrix, narrowed to the touched apps.

Used by the `plan` composite action and the publish-multi.yml reusable workflow.

Schema (apps.yaml entry):
    id          required; reverse-DNS app id.
    branch      optional; default 'stable'. Load-bearing for BOTH source kinds:
                manifest entries build at this channel; bundle entries are
                re-tagged to it by the prep-bundle composite. Drives the
                published OCI tag <branch>-<arch> and the .flatpakref Branch=.
    arches      optional; default ['x86_64']. Manifest sources only.
    manifest    path; mutually exclusive with `bundles`. Requires `runtime`.
    runtime     required when `manifest` is set; flathub-infra container tag.
    run-linter  optional; default False. Manifest sources only.
    bundles     map of arch -> {url, sha256}; mutually exclusive with `manifest`.

Inputs (env):
    CONFIG         path to apps.yaml (default: apps.yaml)
    FORCE          '' | 'all' | '<app-id>'
    BASE_SHA       commit to diff against; empty / all-zeros -> rebuild all
    WORKFLOW_PATH  optional caller workflow file path; touching it forces rebuild-all

Outputs (GITHUB_OUTPUT):
    apps              JSON list of selected app ids
    matrix            full matrix: {include: [<row>, ...]}
    matrix-manifest   subset where source == 'manifest'
    matrix-bundle     subset where source == 'bundle'
    count             total selected apps
    count-manifest    number of manifest entries
    count-bundle      number of bundle entries
"""

import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

import yaml

log = logging.getLogger("plan")

RUNNER_BY_ARCH = {
    "x86_64": "ubuntu-latest",
    "aarch64": "ubuntu-24.04-arm",
}
ZERO_SHA = "0" * 40

# Reject anything that could escape a path component or inject into a shell:
# Flatpak reverse-DNS app ids are letters/digits/`.`/`_`/`-`; branches are the
# same minus the leading-char restriction. Manifest paths must stay within the
# repo. Bundle URLs must be HTTP(S). sha256 must be 64 lowercase hex.
APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
URL_RE = re.compile(r"^https?://")


def die(msg: str) -> None:
    """Print a GitHub Actions error annotation and exit non-zero.

    :param msg: human-readable error message.
    :raises SystemExit: always.
    """
    # `::error::` is parsed by the runner; emit directly so logging config
    # never breaks the wire format.
    print(f"::error::{msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def load_apps_yaml(text: str) -> list[dict[str, Any]]:
    """Parse apps.yaml text and return the ``apps`` list (empty list if absent).

    :param text: raw YAML document text.
    :returns: list of app entry dicts.
    """
    raw = yaml.safe_load(text) or {}
    return raw.get("apps") or []


def load_apps(path: pathlib.Path) -> list[dict[str, Any]]:
    """Read, parse, and validate every entry in the apps.yaml at *path*.

    :param path: filesystem path to apps.yaml.
    :returns: validated list of app entry dicts.
    :raises SystemExit: if the file is missing or any entry fails validation.
    """
    if not path.is_file():
        die(f"{path} not found")
    apps = load_apps_yaml(path.read_text())
    for entry in apps:
        validate(entry)
    return apps


def validate(entry: dict[str, Any]) -> None:
    """Assert that one apps.yaml entry is structurally valid.

    Field shapes are enforced so values reach downstream actions, shell
    commands, and filesystem paths only in well-known forms.

    :param entry: raw app entry dict from apps.yaml.
    :raises SystemExit: on any schema violation.
    """
    app_id = entry.get("id")
    if not app_id:
        die(f"app entry missing 'id': {entry!r}")
    if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
        die(f"'{app_id}': 'id' must match {APP_ID_RE.pattern}")
    branch = entry.get("branch", "stable")
    if not isinstance(branch, str) or not BRANCH_RE.match(branch):
        die(f"'{app_id}': 'branch' must match {BRANCH_RE.pattern}")
    has_manifest = "manifest" in entry
    has_bundles = "bundles" in entry
    if has_manifest == has_bundles:
        die(f"'{app_id}': exactly one of 'manifest' or 'bundles' is required")
    if has_manifest:
        manifest = entry["manifest"]
        if not isinstance(manifest, str) or not manifest:
            die(f"'{app_id}': 'manifest' must be a non-empty path")
        # Manifest paths are relative to the caller repo root and feed
        # `flatpak-builder` directly; reject escapes and absolute paths.
        parts = pathlib.PurePosixPath(manifest).parts
        if manifest.startswith("/") or ".." in parts:
            die(f"'{app_id}': 'manifest' must be a relative path with no '..' segments")
        if not entry.get("runtime"):
            die(f"'{app_id}': 'runtime' is required when 'manifest' is set")
        for arch in entry.get("arches", ["x86_64"]):
            if arch not in RUNNER_BY_ARCH:
                die(f"'{app_id}': unsupported arch '{arch}'")
    else:
        bundles = entry["bundles"] or {}
        if not bundles:
            die(f"'{app_id}': 'bundles' must contain at least one architecture")
        for arch, b in bundles.items():
            if arch not in RUNNER_BY_ARCH:
                die(f"'{app_id}': unsupported bundle arch '{arch}'")
            if not isinstance(b, dict) or not b.get("url") or not b.get("sha256"):
                die(f"'{app_id}' bundle '{arch}': 'url' and 'sha256' are required")
            if not URL_RE.match(b["url"]):
                die(f"'{app_id}' bundle '{arch}': 'url' must be http(s)://...")
            if not SHA256_RE.match(b["sha256"]):
                die(f"'{app_id}' bundle '{arch}': 'sha256' must be 64 lowercase hex chars")


def previous_apps(base_sha: str, config_path: pathlib.Path) -> list[dict[str, Any]] | None:
    """Return the apps list from *config_path* at *base_sha*, or ``None``.

    Returns ``None`` when *base_sha* is empty or all-zeros (first push /
    force-push), when the file did not exist at that commit, or when git
    cannot parse it — all cases where the caller should treat every app as new.

    :param base_sha: git commit SHA to read the file from.
    :param config_path: path to apps.yaml relative to the repo root.
    :returns: parsed app list, or ``None`` if unavailable.
    """
    if not base_sha or base_sha == ZERO_SHA:
        return None
    r = subprocess.run(
        ["git", "show", f"{base_sha}:{config_path}"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    try:
        return load_apps_yaml(r.stdout)
    except yaml.YAMLError:
        return None


def diff_files(base_sha: str) -> list[str] | None:
    """Return files changed between *base_sha* and HEAD, or ``None``.

    Returns ``None`` when *base_sha* is empty, all-zeros, or not reachable in
    the local repo — all cases where the caller must assume everything changed.

    :param base_sha: git commit SHA to diff against HEAD.
    :returns: list of changed file paths, or ``None`` if the diff is unavailable.
    """
    if not base_sha or base_sha == ZERO_SHA:
        return None
    if subprocess.run(["git", "cat-file", "-e", base_sha], capture_output=True).returncode != 0:
        return None
    r = subprocess.run(
        ["git", "diff", "--name-only", base_sha, "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.splitlines()


def manifest_dir_touched(entry: dict[str, Any], changed: list[str]) -> bool:
    """Return True if any path in *changed* is inside the manifest's directory.

    Bundle entries have no manifest directory and always return False.

    :param entry: app entry dict (may be manifest or bundle source).
    :param changed: list of changed file paths from :func:`diff_files`.
    :returns: whether the manifest directory was touched.
    """
    manifest = entry.get("manifest")
    if not manifest:
        return False
    app_dir = str(pathlib.PurePosixPath(manifest).parent)
    if app_dir in (".", ""):
        return False
    prefix = app_dir.rstrip("/") + "/"
    return any(p == app_dir or p.startswith(prefix) for p in changed)


def select_ids(
    apps_current: list[dict[str, Any]],
    apps_previous: list[dict[str, Any]] | None,
    *,
    force: str,
    changed: list[str] | None,
    config_paths: set[str] | None = None,
) -> list[str]:
    """Return app ids that should be (re)built for this push.

    Selection priority (highest first):

    1. ``force="all"`` → every id.
    2. ``force=<id>`` → that one id only.
    3. ``changed=None`` (no reliable diff) → every id.
    4. Any path in *changed* matches *config_paths* → every id (config-level
       change forces a full rebuild).
    5. Otherwise: ids whose manifest dir was touched, or whose entry changed
       relative to *apps_previous*; new apps (absent from previous) are always
       included.

    :param apps_current: current app list from apps.yaml.
    :param apps_previous: app list at the base commit, or ``None`` if unavailable.
    :param force: ``"all"``, a specific app id, or ``""`` to skip forced selection.
    :param changed: list of changed files, or ``None`` when diff is unavailable.
    :param config_paths: paths (e.g. the caller workflow) that trigger a full rebuild.
    :returns: list of selected app ids (may contain duplicates; caller deduplicates).
    :raises SystemExit: if *force* names an id not present in *apps_current*.
    """
    all_ids = [a["id"] for a in apps_current]
    if force == "all":
        return all_ids
    if force:
        if force not in all_ids:
            die(f"Requested app '{force}' is not in the config")
        return [force]
    if changed is None:
        return all_ids
    if config_paths and any(p in config_paths for p in changed):
        return all_ids
    by_id_prev = {a["id"]: a for a in (apps_previous or [])}
    selected = []
    for app in apps_current:
        if manifest_dir_touched(app, changed):
            selected.append(app["id"])
            continue
        if apps_previous is None or by_id_prev.get(app["id"]) != app:
            selected.append(app["id"])
    return selected


def expand_matrix(apps: list[dict[str, Any]], selected: list[str]) -> list[dict[str, Any]]:
    """Expand selected app ids into a flat list of runner matrix rows.

    Each manifest app produces one row per architecture; each bundle app
    produces one row per arch key in its ``bundles`` map.

    :param apps: full current app list (used as a lookup table).
    :param selected: ordered list of app ids to include.
    :returns: list of matrix row dicts ready for ``{"include": ...}``.
    """
    by_id = {a["id"]: a for a in apps}
    include = []
    for app_id in selected:
        app = by_id[app_id]
        branch = app.get("branch", "stable")
        if "manifest" in app:
            arches = app.get("arches", ["x86_64"])
            run_linter = bool(app.get("run-linter", False))
            for arch in arches:
                include.append(
                    {
                        "source": "manifest",
                        "app-id": app_id,
                        "manifest": app["manifest"],
                        "runtime": app["runtime"],
                        "branch": branch,
                        "arch": arch,
                        "runner": RUNNER_BY_ARCH[arch],
                        "run-linter": run_linter,
                    }
                )
        else:
            for arch, b in app["bundles"].items():
                include.append(
                    {
                        "source": "bundle",
                        "app-id": app_id,
                        "branch": branch,
                        "arch": arch,
                        "runner": RUNNER_BY_ARCH[arch],
                        "bundle-url": b["url"],
                        "bundle-sha256": b["sha256"],
                    }
                )
    return include


def emit_outputs(values: dict[str, str]) -> None:
    """Append key=value pairs to GITHUB_OUTPUT; no-op when the var is unset.

    :param values: output name → value mapping to write.
    """
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        for k, v in values.items():
            fh.write(f"{k}={v}\n")


def main() -> None:
    """CLI entry point: read env, compute the build matrix, emit GitHub outputs."""
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    config = pathlib.Path(os.environ.get("CONFIG", "apps.yaml"))
    force = os.environ.get("FORCE", "").strip()
    base_sha = os.environ.get("BASE_SHA", "").strip()
    workflow_path = os.environ.get("WORKFLOW_PATH", "").strip()
    config_paths = {workflow_path} if workflow_path else set()

    apps_current = load_apps(config)
    apps_prev = previous_apps(base_sha, config) if not force else None
    changed = diff_files(base_sha) if not force else []

    selected = sorted(
        set(
            select_ids(
                apps_current,
                apps_prev,
                force=force,
                changed=changed,
                config_paths=config_paths,
            )
        )
    )
    include = expand_matrix(apps_current, selected)
    manifest_rows = [r for r in include if r["source"] == "manifest"]
    bundle_rows = [r for r in include if r["source"] == "bundle"]

    emit_outputs(
        {
            "apps": json.dumps(selected),
            "matrix": json.dumps({"include": include}, separators=(",", ":")),
            "matrix-manifest": json.dumps({"include": manifest_rows}, separators=(",", ":")),
            "matrix-bundle": json.dumps({"include": bundle_rows}, separators=(",", ":")),
            "count": str(len(selected)),
            "count-manifest": str(len(manifest_rows)),
            "count-bundle": str(len(bundle_rows)),
        }
    )

    log.info("Changed files: %r", changed)
    log.info("Selected apps: %s", selected)


if __name__ == "__main__":
    main()
