import json
from pathlib import Path

import pytest

from plan import plan as plan_mod


def test_validate_requires_id_and_source() -> None:
    with pytest.raises(SystemExit):
        plan_mod.validate({"manifest": "x"})  # no id
    with pytest.raises(SystemExit):
        plan_mod.validate({"id": "a", "manifest": "x", "bundles": {}})  # both
    with pytest.raises(SystemExit):
        plan_mod.validate({"id": "a"})  # neither


def test_validate_manifest_requires_runtime_and_known_arch() -> None:
    with pytest.raises(SystemExit):
        plan_mod.validate({"id": "a", "manifest": "x.yaml"})
    with pytest.raises(SystemExit):
        plan_mod.validate(
            {"id": "a", "manifest": "x.yaml", "runtime": "gnome-50", "arches": ["mips"]}
        )
    plan_mod.validate({"id": "a", "manifest": "x.yaml", "runtime": "gnome-50"})  # ok


def test_validate_bundles_need_url_and_sha() -> None:
    sha = "a" * 64
    url = "https://example.com/app.flatpak"
    with pytest.raises(SystemExit):
        plan_mod.validate({"id": "a", "bundles": {"x86_64": {"url": url}}})  # missing sha
    plan_mod.validate(
        {
            "id": "a",
            "bundles": {"x86_64": {"url": url, "sha256": sha}},
        }
    )  # ok


def test_validate_app_id_pattern() -> None:
    sha = "a" * 64
    url = "https://example.com/x.flatpak"
    # Reject reserved characters that could escape a path component or shell.
    for bad in ("../sneaky", "a/b", "a b", ".leading-dot", "-leading-dash"):
        with pytest.raises(SystemExit):
            plan_mod.validate({"id": bad, "bundles": {"x86_64": {"url": url, "sha256": sha}}})
    # Accept Flatpak reverse-DNS form.
    plan_mod.validate(
        {"id": "org.example.App", "manifest": "apps/org.example.App/m.yaml", "runtime": "gnome-50"}
    )


def test_validate_branch_pattern() -> None:
    with pytest.raises(SystemExit):
        plan_mod.validate(
            {"id": "a", "branch": "stable;rm -rf /", "manifest": "m.yaml", "runtime": "gnome-50"}
        )
    plan_mod.validate({"id": "a", "branch": "beta.1", "manifest": "m.yaml", "runtime": "gnome-50"})


def test_validate_manifest_path_must_be_relative() -> None:
    for bad in ("/abs/m.yaml", "../escape.yaml", "apps/../escape.yaml"):
        with pytest.raises(SystemExit):
            plan_mod.validate({"id": "a", "manifest": bad, "runtime": "gnome-50"})


def test_validate_bundle_url_must_be_http() -> None:
    sha = "a" * 64
    with pytest.raises(SystemExit):
        plan_mod.validate(
            {"id": "a", "bundles": {"x86_64": {"url": "file:///etc/passwd", "sha256": sha}}}
        )
    plan_mod.validate(
        {"id": "a", "bundles": {"x86_64": {"url": "http://example.com/x.flatpak", "sha256": sha}}}
    )


def test_validate_bundle_sha256_must_be_hex() -> None:
    url = "https://example.com/x.flatpak"
    for bad in ("short", "G" * 64, "a" * 63, "A" * 64):
        with pytest.raises(SystemExit):
            plan_mod.validate({"id": "a", "bundles": {"x86_64": {"url": url, "sha256": bad}}})


def test_expand_matrix_manifest_and_bundles() -> None:
    apps = [
        {
            "id": "a.one",
            "manifest": "apps/a.one/a.one.yaml",
            "runtime": "gnome-50",
            "arches": ["x86_64"],
            "branch": "stable",
        },
        {
            "id": "a.two",
            "bundles": {
                "x86_64": {"url": "u1", "sha256": "s1"},
                "aarch64": {"url": "u2", "sha256": "s2"},
            },
            "branch": "beta",
        },
    ]
    matrix = plan_mod.expand_matrix(apps, ["a.one", "a.two"])
    manifest_rows = [r for r in matrix if r["source"] == "manifest"]
    bundle_rows = [r for r in matrix if r["source"] == "bundle"]
    assert manifest_rows[0]["app-id"] == "a.one"
    assert manifest_rows[0]["runtime"] == "gnome-50"
    assert {r["arch"] for r in bundle_rows} == {"x86_64", "aarch64"}
    assert bundle_rows[0]["branch"] == "beta"


def test_manifest_dir_touched() -> None:
    entry = {"manifest": "apps/org.x/manifest.yaml"}
    assert plan_mod.manifest_dir_touched(entry, ["apps/org.x/manifest.yaml"])
    assert plan_mod.manifest_dir_touched(entry, ["apps/org.x/sub/file"])
    assert not plan_mod.manifest_dir_touched(entry, ["apps/other.app/manifest.yaml"])
    assert not plan_mod.manifest_dir_touched(
        {"bundles": {"x86_64": {"url": "u", "sha256": "s"}}}, ["x"]
    )


def test_force_all_returns_every_id() -> None:
    apps = [
        {"id": "a", "manifest": "x.yaml", "runtime": "r"},
        {"id": "b", "manifest": "y.yaml", "runtime": "r"},
    ]
    ids = plan_mod.select_ids(apps, None, force="all", changed=None)
    assert ids == ["a", "b"]


def test_force_specific_returns_single_id() -> None:
    apps = [
        {"id": "a", "manifest": "x.yaml", "runtime": "r"},
        {"id": "b", "manifest": "y.yaml", "runtime": "r"},
    ]
    ids = plan_mod.select_ids(apps, None, force="b", changed=None)
    assert ids == ["b"]


def test_force_unknown_id_dies() -> None:
    apps = [{"id": "a", "manifest": "x.yaml", "runtime": "r"}]
    with pytest.raises(SystemExit):
        plan_mod.select_ids(apps, None, force="c", changed=None)


def test_select_ids_diff_picks_only_touched() -> None:
    apps = [
        {"id": "a", "manifest": "apps/a/a.yaml", "runtime": "r"},
        {"id": "b", "manifest": "apps/b/b.yaml", "runtime": "r"},
    ]
    ids = plan_mod.select_ids(apps, apps, force="", changed=["apps/a/foo"])
    assert ids == ["a"]


def test_select_ids_diff_picks_bundle_sha_bumps() -> None:
    prev = [{"id": "x", "bundles": {"x86_64": {"url": "u", "sha256": "old"}}}]
    curr = [{"id": "x", "bundles": {"x86_64": {"url": "u", "sha256": "new"}}}]
    ids = plan_mod.select_ids(curr, prev, force="", changed=["apps.yaml"])
    assert ids == ["x"]


def test_expand_matrix_bundle_branch_defaults_to_stable() -> None:
    # Bundle source: branch is load-bearing (drives the published channel via
    # prep-bundle's re-tag). plan.py's default of 'stable' is the fallback when
    # apps.yaml omits the field.
    apps = [{"id": "x", "bundles": {"x86_64": {"url": "u", "sha256": "s"}}}]
    rows = plan_mod.expand_matrix(apps, ["x"])
    assert rows[0]["source"] == "bundle"
    assert rows[0]["branch"] == "stable"


def test_select_ids_config_paths_forces_rebuild_all() -> None:
    apps = [
        {"id": "a", "manifest": "apps/a/a.yaml", "runtime": "r"},
        {"id": "b", "manifest": "apps/b/b.yaml", "runtime": "r"},
    ]
    ids = plan_mod.select_ids(
        apps,
        apps,
        force="",
        changed=["wf.yml"],
        config_paths={"wf.yml"},
    )
    assert ids == ["a", "b"]


def test_previous_and_diff_handle_empty_base_sha() -> None:
    # Both helpers must return None on missing / zero base sha, so plan.py
    # treats first runs and force-pushes as "no reliable previous state" and
    # rebuilds everything.
    from pathlib import Path

    assert plan_mod.previous_apps("", Path("apps.yaml")) is None
    assert plan_mod.previous_apps("0" * 40, Path("apps.yaml")) is None
    assert plan_mod.diff_files("") is None
    assert plan_mod.diff_files("0" * 40) is None


def test_plan_py_emits_matrix(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "apps.yaml"
    config.write_text(
        "apps:\n"
        "  - id: a.one\n"
        "    manifest: apps/a.one/a.one.yaml\n"
        "    runtime: gnome-50\n"
        "    arches: [x86_64]\n"
        "    branch: stable\n"
    )
    out = tmp_path / "out"
    out.write_text("")
    monkeypatch.setenv("CONFIG", str(config))
    monkeypatch.setenv("FORCE", "all")
    monkeypatch.setenv("BASE_SHA", "")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    plan_mod.main()
    lines = out.read_text().splitlines()
    payload = {k: v for k, v in (line.split("=", 1) for line in lines)}
    matrix = json.loads(payload["matrix"])
    assert matrix["include"][0]["app-id"] == "a.one"
    assert payload["count"] == "1"
    assert payload["count-manifest"] == "1"
    assert payload["count-bundle"] == "0"
