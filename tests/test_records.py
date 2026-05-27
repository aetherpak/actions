import json
from pathlib import Path

import pytest

from publish.records import Record, iter_records, write_record


def test_write_record_round_trips(tmp_path: Path) -> None:
    rec = Record(
        app_id="org.example.App",
        arch="x86_64",
        branch="stable",
        name="owner/app",
        registry="https://ghcr.io",
        digest="sha256:abc",
        ref="app/org.example.App/x86_64/stable",
        tag="stable-x86_64",
    )
    labels = {"org.flatpak.ref": rec.ref, "org.flatpak.commit": "deadbeef"}
    cell = write_record(tmp_path, rec, labels=labels)

    assert cell == tmp_path / "org.example.App-x86_64"
    assert json.loads((cell / "record.json").read_text())["digest"] == "sha256:abc"
    assert json.loads((cell / "labels.json").read_text())["org.flatpak.commit"] == "deadbeef"


def test_iter_records_yields_each_cell(tmp_path: Path) -> None:
    write_record(
        tmp_path,
        Record(
            app_id="a.b.C",
            arch="x86_64",
            branch="stable",
            name="o/r",
            registry="https://ghcr.io",
            digest="sha256:11",
            ref="app/a.b.C/x86_64/stable",
            tag="stable-x86_64",
        ),
        labels={"org.flatpak.ref": "app/a.b.C/x86_64/stable"},
    )
    write_record(
        tmp_path,
        Record(
            app_id="a.b.C",
            arch="aarch64",
            branch="stable",
            name="o/r",
            registry="https://ghcr.io",
            digest="sha256:22",
            ref="app/a.b.C/aarch64/stable",
            tag="stable-aarch64",
        ),
        labels={"org.flatpak.ref": "app/a.b.C/aarch64/stable"},
    )

    rows = sorted(iter_records(tmp_path), key=lambda r: r[0].arch)
    assert [r[0].arch for r in rows] == ["aarch64", "x86_64"]
    assert all(isinstance(r[1], dict) for r in rows)
    assert rows[0][1]["org.flatpak.ref"] == "app/a.b.C/aarch64/stable"
    assert rows[1][1]["org.flatpak.ref"] == "app/a.b.C/x86_64/stable"


def test_write_record_rejects_bad_app_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_record(
            tmp_path,
            Record(
                "",
                "x86_64",
                "stable",
                "o/r",
                "https://ghcr.io",
                "sha256:x",
                "app/x/x86_64/stable",
                "stable-x86_64",
            ),
            labels={},
        )


def test_iter_records_empty_on_missing_root(tmp_path: Path) -> None:
    assert list(iter_records(tmp_path / "missing")) == []


def test_iter_records_skips_incomplete_cells(tmp_path: Path) -> None:
    # Cell with only record.json (no labels.json) must be skipped silently —
    # partial/interrupted publish-oci runs shouldn't break publish-site.
    good = tmp_path / "good.app-x86_64"
    good.mkdir()
    (good / "record.json").write_text(
        '{"app-id":"good.app","arch":"x86_64","branch":"stable","name":"o/r","registry":"https://ghcr.io","digest":"sha256:1","ref":"app/good.app/x86_64/stable","tag":"stable-x86_64"}\n'
    )
    (good / "labels.json").write_text('{"org.flatpak.ref":"app/good.app/x86_64/stable"}\n')

    partial = tmp_path / "bad.app-x86_64"
    partial.mkdir()
    (partial / "record.json").write_text("{}\n")
    # labels.json deliberately absent

    apps = [rec.app_id for rec, _ in iter_records(tmp_path)]
    assert apps == ["good.app"]
