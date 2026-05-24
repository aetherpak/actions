import pytest

from publish.merge_index import map_arch, merge_index_data


@pytest.mark.parametrize(
    ("flatpak_arch", "oci_arch"),
    [
        ("x86_64", "amd64"),
        ("aarch64", "arm64"),
        ("i386", "386"),
        ("arm", "arm"),
        ("UNKNOWN", "unknown"),
    ],
)
def test_map_arch(flatpak_arch: str, oci_arch: str) -> None:
    assert map_arch(flatpak_arch) == oci_arch


def test_adds_new_image() -> None:
    updated = merge_index_data(
        index_data={"Registry": "https://ghcr.io", "Results": []},
        registry="https://ghcr.io",
        name="owner/repo-one",
        digest="sha256:1111",
        ref="app/org.flatpak.AppOne/x86_64/stable",
        tag="stable",
        oci_arch="amd64",
    )
    assert updated["Registry"] == "https://ghcr.io"
    image = updated["Results"][0]["Images"][0]
    assert image["Digest"] == "sha256:1111"
    assert image["Architecture"] == "amd64"
    assert image["Labels"]["org.flatpak.ref"] == "app/org.flatpak.AppOne/x86_64/stable"
    assert image["Tags"] == ["stable"]


def test_merges_new_arch_and_new_app() -> None:
    index_data = {
        "Registry": "https://ghcr.io",
        "Results": [
            {
                "Name": "owner/repo-one",
                "Images": [
                    {
                        "Digest": "sha256:1111",
                        "Architecture": "amd64",
                        "Labels": {"org.flatpak.ref": "app/org.flatpak.AppOne/x86_64/stable"},
                        "Tags": ["stable"],
                    }
                ],
            }
        ],
    }
    # Same app, second architecture -> appended alongside the first.
    updated = merge_index_data(
        index_data=index_data,
        registry="https://ghcr.io",
        name="owner/repo-one",
        digest="sha256:2222",
        ref="app/org.flatpak.AppOne/aarch64/stable",
        tag="stable",
        oci_arch="arm64",
    )
    assert len(updated["Results"][0]["Images"]) == 2

    # Different app -> new result entry.
    updated = merge_index_data(
        index_data=updated,
        registry="https://ghcr.io",
        name="owner/repo-two",
        digest="sha256:3333",
        ref="app/org.flatpak.AppTwo/x86_64/beta",
        tag="beta",
        oci_arch="amd64",
    )
    assert len(updated["Results"]) == 2
    repo_two = next(r for r in updated["Results"] if r["Name"] == "owner/repo-two")
    assert repo_two["Images"][0]["Digest"] == "sha256:3333"


def test_overwrites_same_ref_and_arch() -> None:
    index_data = {
        "Registry": "https://ghcr.io",
        "Results": [
            {
                "Name": "owner/repo-one",
                "Images": [
                    {
                        "Digest": "sha256:old",
                        "Architecture": "amd64",
                        "Labels": {"org.flatpak.ref": "app/org.flatpak.AppOne/x86_64/stable"},
                        "Tags": ["stable"],
                    }
                ],
            }
        ],
    }
    updated = merge_index_data(
        index_data=index_data,
        registry="https://ghcr.io",
        name="owner/repo-one",
        digest="sha256:new",
        ref="app/org.flatpak.AppOne/x86_64/stable",
        tag="stable",
        oci_arch="amd64",
    )
    assert len(updated["Results"][0]["Images"]) == 1
    assert updated["Results"][0]["Images"][0]["Digest"] == "sha256:new"


def test_embeds_full_label_set() -> None:
    labels = {
        "org.flatpak.commit": "deadbeef",
        "org.flatpak.metadata": "[Application]\nname=org.flatpak.AppOne\n",
    }
    updated = merge_index_data(
        index_data={"Registry": "https://ghcr.io", "Results": []},
        registry="https://ghcr.io",
        name="owner/repo-one",
        digest="sha256:aaaa",
        ref="app/org.flatpak.AppOne/x86_64/stable",
        tag="stable",
        oci_arch="amd64",
        labels=labels,
    )
    embedded = updated["Results"][0]["Images"][0]["Labels"]
    assert embedded["org.flatpak.commit"] == "deadbeef"
    assert "org.flatpak.metadata" in embedded
    assert embedded["org.flatpak.ref"] == "app/org.flatpak.AppOne/x86_64/stable"


def test_defaults_to_ref_only_label() -> None:
    updated = merge_index_data(
        index_data={"Registry": "https://ghcr.io", "Results": []},
        registry="https://ghcr.io",
        name="owner/repo-one",
        digest="sha256:bbbb",
        ref="app/org.flatpak.AppOne/x86_64/stable",
        tag="stable",
        oci_arch="amd64",
    )
    embedded = updated["Results"][0]["Images"][0]["Labels"]
    assert embedded == {"org.flatpak.ref": "app/org.flatpak.AppOne/x86_64/stable"}
