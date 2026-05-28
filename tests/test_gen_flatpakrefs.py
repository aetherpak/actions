from collections.abc import Callable
from pathlib import Path

import pytest

from publish import gen_flatpakrefs
from publish.gen_flatpakrefs import app_title, flatpakref_files, ref_filename

URL = "oci+https://owner.github.io/repo"

APPDATA = (
    '<component type="desktop-application">'
    "<id>org.example.App</id>"
    '<name xml:lang="de">Beispiel</name>'
    "<name>Example App</name>"
    "<summary>Does things</summary>"
    "</component>"
)


def _parse(content: str) -> dict[str, str]:
    """Flatten a .flatpakref body to key->value, dropping section headers."""
    body: dict[str, str] = {}
    for line in content.splitlines():
        if line.startswith("[") or not line.strip():
            continue
        k, _, v = line.partition("=")
        body[k] = v
    return body


def test_app_title_prefers_unlocalized_name() -> None:
    assert app_title(APPDATA, "org.example.App") == "Example App"


@pytest.mark.parametrize("appdata", ["", "<not xml", "<component></component>"])
def test_app_title_falls_back_to_app_id_leaf(appdata: str) -> None:
    assert app_title(appdata, "org.example.App") == "App"


def test_ref_filename_basic() -> None:
    assert ref_filename("org.example.App", "stable") == "org.example.App-stable.flatpakref"


def test_ref_filename_sanitizes_slash_in_branch() -> None:
    # A feature-branch channel must not produce nested dirs in the filename.
    assert ref_filename("org.example.App", "feature/x") == "org.example.App-feature-x.flatpakref"


def test_unsigned_fields(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64", appdata=APPDATA),
                ],
            }
        ]
    }
    files = flatpakref_files(
        index,
        url=URL,
        remote_name="aetherpak",
        runtime_repo="https://dl.flathub.org/repo/flathub.flatpakrepo",
    )
    assert list(files) == ["org.example.App-stable.flatpakref"]
    body = _parse(files["org.example.App-stable.flatpakref"])
    assert body["Title"] == "Example App"
    assert body["Name"] == "org.example.App"
    assert body["Branch"] == "stable"
    assert body["Url"] == URL
    assert body["SuggestRemoteName"] == "aetherpak"
    assert body["RuntimeRepo"] == "https://dl.flathub.org/repo/flathub.flatpakrepo"
    assert "GPGKey" not in body
    assert "SignatureLookaside" not in body


def test_empty_runtime_repo_omits_line(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64"),
                ],
            }
        ]
    }
    files = flatpakref_files(index, url=URL, remote_name="aetherpak", runtime_repo="")
    assert "RuntimeRepo" not in _parse(files["org.example.App-stable.flatpakref"])


def test_skips_noninstallable_stub(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64"),
                    make_image("app/org.stub.App/x86_64/stable", "amd64", metadata=False),
                ],
            }
        ]
    }
    files = flatpakref_files(index, url=URL, remote_name="aetherpak", runtime_repo="")
    assert list(files) == ["org.example.App-stable.flatpakref"]


def test_signed_fields(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64"),
                ],
            }
        ]
    }
    files = flatpakref_files(
        index,
        url=URL,
        remote_name="aetherpak",
        runtime_repo="",
        gpg_key_b64="QUJD",
        signature_lookaside="https://owner.github.io/repo/sigs",
    )
    body = _parse(files["org.example.App-stable.flatpakref"])
    assert body["GPGKey"] == "QUJD"
    assert body["SignatureLookaside"] == "https://owner.github.io/repo/sigs"


def test_signed_requires_both_key_and_lookaside(make_image: Callable[..., dict]) -> None:
    # A key with no lookaside (or vice versa) must not emit a half-configured
    # verified remote; fall back to the unverified ref.
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64"),
                ],
            }
        ]
    }
    body = _parse(
        flatpakref_files(
            index, url=URL, remote_name="aetherpak", runtime_repo="", gpg_key_b64="QUJD"
        )["org.example.App-stable.flatpakref"]
    )
    assert "GPGKey" not in body
    assert "SignatureLookaside" not in body


def test_branch_with_slash(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/feature/x", "amd64"),
                ],
            }
        ]
    }
    files = flatpakref_files(index, url=URL, remote_name="aetherpak", runtime_repo="")
    # ref has 5 parts when the branch contains '/', so it is skipped.
    assert files == {}


def test_multi_arch_dedup(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64", appdata=APPDATA),
                    make_image("app/org.example.App/aarch64/stable", "arm64"),
                ],
            }
        ]
    }
    files = flatpakref_files(index, url=URL, remote_name="aetherpak", runtime_repo="")
    assert list(files) == ["org.example.App-stable.flatpakref"]
    # Title is picked up from whichever arch carries appdata.
    assert _parse(files["org.example.App-stable.flatpakref"])["Title"] == "Example App"


def test_multiple_channels(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/repo",
                "Images": [
                    make_image("app/org.example.App/x86_64/stable", "amd64"),
                    make_image("app/org.example.App/x86_64/beta", "amd64b"),
                ],
            }
        ]
    }
    files = flatpakref_files(index, url=URL, remote_name="aetherpak", runtime_repo="")
    assert sorted(files) == ["org.example.App-beta.flatpakref", "org.example.App-stable.flatpakref"]


def test_main_missing_index_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "index" / "static"
    out_dir = tmp_path / "refs"
    monkeypatch.setattr(
        "sys.argv",
        [
            "gen_flatpakrefs.py",
            "--index-path",
            str(missing),
            "--out-dir",
            str(out_dir),
            "--url",
            "oci+https://example.invalid/repo",
            "--remote-name",
            "example",
        ],
    )

    gen_flatpakrefs.main()

    assert not missing.exists()
    assert not out_dir.exists()
