from collections.abc import Callable

import pytest

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
