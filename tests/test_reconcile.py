from pathlib import Path

import pytest

from publish import reconcile
from publish.reconcile import registry_host, remove_digests


@pytest.fixture
def index() -> dict:
    return {
        "Registry": "https://ghcr.io",
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    {
                        "Digest": "sha256:keep",
                        "Architecture": "amd64",
                        "Labels": {"org.flatpak.ref": "app/org.flatpak.AppOne/x86_64/stable"},
                        "Tags": ["stable"],
                    },
                    {
                        "Digest": "sha256:gone",
                        "Architecture": "arm64",
                        "Labels": {"org.flatpak.ref": "app/org.flatpak.AppOne/aarch64/stable"},
                        "Tags": ["stable"],
                    },
                ],
            }
        ],
    }


def test_removes_matching_digest(index: dict) -> None:
    removed = remove_digests(index, {"sha256:gone"})
    assert len(removed) == 1
    assert removed[0]["Digest"] == "sha256:gone"
    digests = [img["Digest"] for img in index["Results"][0]["Images"]]
    assert digests == ["sha256:keep"]


def test_keeps_non_matching(index: dict) -> None:
    removed = remove_digests(index, {"sha256:absent"})
    assert removed == []
    assert len(index["Results"][0]["Images"]) == 2


def test_drops_emptied_result(index: dict) -> None:
    remove_digests(index, {"sha256:keep", "sha256:gone"})
    assert index["Results"] == []


def test_last_entry_leaves_valid_empty_index() -> None:
    index = {
        "Registry": "https://ghcr.io",
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [{"Digest": "sha256:only", "Labels": {}, "Tags": []}],
            }
        ],
    }
    remove_digests(index, {"sha256:only"})
    assert index == {"Registry": "https://ghcr.io", "Results": []}


def test_removes_from_one_result_only() -> None:
    index = {
        "Registry": "https://ghcr.io",
        "Results": [
            {
                "Name": "owner/repo-one",
                "Images": [{"Digest": "sha256:a", "Labels": {}, "Tags": []}],
            },
            {
                "Name": "owner/repo-two",
                "Images": [{"Digest": "sha256:b", "Labels": {}, "Tags": []}],
            },
        ],
    }
    removed = remove_digests(index, {"sha256:a"})
    assert len(removed) == 1
    assert [r["Name"] for r in index["Results"]] == ["owner/repo-two"]


@pytest.mark.parametrize(
    ("registry", "host"),
    [
        ("https://ghcr.io", "ghcr.io"),
        ("https://localhost:5001", "localhost:5001"),
        ("ghcr.io", "ghcr.io"),
    ],
)
def test_registry_host_strips_scheme(registry: str, host: str) -> None:
    assert registry_host(registry) == host


def test_main_missing_index_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    missing = tmp_path / "index" / "static"
    monkeypatch.setattr(
        "sys.argv",
        ["reconcile.py", "--index-path", str(missing), "--registry", "https://ghcr.io"],
    )

    # Safeguard: if the early-return path breaks, the test must fail loudly rather
    # than silently shelling out to skopeo.
    def _fail(*_args, **_kwargs):
        raise AssertionError("subprocess.run should not be called when index is absent")

    monkeypatch.setattr("publish.reconcile.subprocess.run", _fail)

    with caplog.at_level("INFO"):
        reconcile.main()

    assert not missing.exists()
    assert any("nothing to reconcile" in r.message for r in caplog.records)
