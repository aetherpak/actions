import io
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pytest

from publish import signing
from publish.signing import (
    index_signature_relpaths,
    registries_d_yaml,
    signature_relpath,
    signing_manifest,
)


def test_signature_relpath() -> None:
    assert (
        signature_relpath("aetherpak/mock-app", "sha256:abc123", "sigs")
        == "sigs/aetherpak/mock-app@sha256=abc123/signature-1"
    )


def test_signature_relpath_strips_slashes() -> None:
    assert (
        signature_relpath("/owner/repo/", "sha256:deadbeef", "/sigs/")
        == "sigs/owner/repo@sha256=deadbeef/signature-1"
    )


def test_signature_relpath_rejects_bare_digest() -> None:
    with pytest.raises(ValueError):
        signature_relpath("owner/repo", "deadbeef", "sigs")


def test_registries_d_yaml() -> None:
    assert (
        registries_d_yaml("ghcr.io", "/abs/_site/sigs")
        == "docker:\n  ghcr.io:\n    lookaside-staging: file:///abs/_site/sigs\n"
    )


def test_registries_d_yaml_requires_absolute() -> None:
    with pytest.raises(ValueError):
        registries_d_yaml("ghcr.io", "rel/path")


def test_signing_manifest() -> None:
    assert signing_manifest("sigs", "key.asc", "DEADBEEF", "aetherpak") == {
        "enabled": True,
        "lookaside": "sigs",
        "publicKey": "sigs/key.asc",
        "fingerprint": "DEADBEEF",
        "remoteName": "aetherpak",
    }


def test_index_signature_relpaths(make_image: Callable[..., dict]) -> None:
    index = {
        "Results": [
            {
                "Name": "owner/a",
                "Images": [
                    make_image("app/a/x/s", digest="sha256:aaa"),
                    make_image("app/a/x/s", digest="sha256:bbb"),
                ],
            },
            {"Name": "owner/b", "Images": [make_image("app/b/x/s", digest="sha256:ccc")]},
        ]
    }
    assert index_signature_relpaths(index, "sigs") == [
        "sigs/owner/a@sha256=aaa/signature-1",
        "sigs/owner/a@sha256=bbb/signature-1",
        "sigs/owner/b@sha256=ccc/signature-1",
    ]


def test_index_signature_relpaths_skips_incomplete() -> None:
    index = {
        "Results": [
            {"Name": "owner/a", "Images": [{"Digest": ""}, {}]},
            {"Name": "", "Images": [{"Digest": "sha256:x"}]},
        ]
    }
    assert index_signature_relpaths(index, "sigs") == []


def test_index_signature_relpaths_skips_noninstallable_stub() -> None:
    # An old pre-signing ref carries only org.flatpak.ref (no metadata): it is
    # not installable, so it must not be backfilled (and must not warn).
    index = {
        "Results": [
            {
                "Name": "owner/a",
                "Images": [
                    {"Digest": "sha256:real", "Labels": {"org.flatpak.metadata": "x"}},
                    {"Digest": "sha256:stub", "Labels": {"org.flatpak.ref": "app/x/x/master"}},
                ],
            },
        ]
    }
    assert index_signature_relpaths(index, "sigs") == ["sigs/owner/a@sha256=real/signature-1"]


def test_sigpaths_missing_index_is_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "index" / "static"
    monkeypatch.setattr(
        "sys.argv",
        ["signing.py", "sigpaths", "--index-path", str(missing), "--sig-dir", "sigs"],
    )

    assert signing.main() == 0
    assert capsys.readouterr().out == ""


def test_backfill_signatures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 1. Create a dummy index/static
    index_file = tmp_path / "static"
    index_data = {
        "Results": [
            {
                "Name": "owner/app",
                "Images": [
                    {
                        "Digest": "sha256:123456",
                        "Labels": {
                            "org.flatpak.ref": "app/org.example.App/x86_64/stable",
                            "org.flatpak.metadata": "metadata-stub",
                        },
                    }
                ],
            }
        ]
    }
    index_file.write_text(json.dumps(index_data))

    site_dir = tmp_path / "site"
    sig_relpath = "sigs/owner/app@sha256=123456/signature-1"
    target_sig_file = site_dir / sig_relpath

    # Mock urllib.request.urlopen to return dummy signature bytes
    dummy_sig_bytes = b"mock-signature-content"

    class MockResponse:
        def __init__(self, content: bytes) -> None:
            self.content = content

        def read(self) -> bytes:
            return self.content

        def __enter__(self) -> "MockResponse":
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            pass

    urls_fetched = []

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else req
        urls_fetched.append(url)
        return MockResponse(dummy_sig_bytes)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Call backfill
    signing.backfill_signatures(
        index_path=str(index_file),
        sig_dir="sigs",
        site_dir=str(site_dir),
        pages_url="https://pages.example.com",
    )

    # Verify download happened
    assert len(urls_fetched) == 1
    assert urls_fetched[0] == f"https://pages.example.com/{sig_relpath}"
    assert target_sig_file.is_file()
    assert target_sig_file.read_bytes() == dummy_sig_bytes
    assert "Backfilled signature" in capsys.readouterr().out

    # 2. Call backfill again when the file already exists - it should be skipped
    urls_fetched.clear()
    signing.backfill_signatures(
        index_path=str(index_file),
        sig_dir="sigs",
        site_dir=str(site_dir),
        pages_url="https://pages.example.com",
    )
    assert len(urls_fetched) == 0

    # 3. Test HTTPError behavior (e.g. 404 Not Found)
    target_sig_file.unlink()

    import email.message

    def mock_urlopen_error(req, *args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://pages.example.com/error",
            code=404,
            msg="Not Found",
            hdrs=email.message.Message(),
            fp=io.BytesIO(),
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_error)

    signing.backfill_signatures(
        index_path=str(index_file),
        sig_dir="sigs",
        site_dir=str(site_dir),
        pages_url="https://pages.example.com",
    )

    assert not target_sig_file.exists()
    assert not target_sig_file.parent.exists()
    assert not (site_dir / "sigs").exists()
    assert site_dir.exists()
    err_out = capsys.readouterr().err
    assert "::warning::No deployed signature" in err_out
    assert "HTTP 404" in err_out


def test_backfill_signatures_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Create a dummy index/static
    index_file = tmp_path / "static"
    index_data = {
        "Results": [
            {
                "Name": "owner/app",
                "Images": [
                    {
                        "Digest": "sha256:123456",
                        "Labels": {
                            "org.flatpak.ref": "app/org.example.App/x86_64/stable",
                            "org.flatpak.metadata": "metadata-stub",
                        },
                    }
                ],
            }
        ]
    }
    index_file.write_text(json.dumps(index_data))

    site_dir = tmp_path / "site"

    # Use a malicious sig_dir containing ".." to escape site_dir
    malicious_sig_dir = "../../../malicious"

    # Call backfill
    signing.backfill_signatures(
        index_path=str(index_file),
        sig_dir=malicious_sig_dir,
        site_dir=str(site_dir),
        pages_url="https://pages.example.com",
    )

    err_out = capsys.readouterr().err
    assert "::warning::Skipping invalid or unsafe path" in err_out
