"""resolve-channel.sh maps the triggering git ref to a default channel."""

from collections.abc import Callable


def test_tag_maps_to_stable(resolve_channel: Callable[..., str]) -> None:
    assert resolve_channel(GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="v1.2.3") == "stable"


def test_tag_beats_default_branch(resolve_channel: Callable[..., str]) -> None:
    # A tag whose name happens to equal the default branch still -> stable.
    assert (
        resolve_channel(GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="main", DEFAULT_BRANCH="main")
        == "stable"
    )


def test_main_maps_to_beta_when_default_branch_unset(resolve_channel: Callable[..., str]) -> None:
    assert resolve_channel(GITHUB_REF_TYPE="branch", GITHUB_REF_NAME="main") == "beta"


def test_configured_default_branch_maps_to_beta(resolve_channel: Callable[..., str]) -> None:
    assert (
        resolve_channel(
            GITHUB_REF_TYPE="branch", GITHUB_REF_NAME="develop", DEFAULT_BRANCH="develop"
        )
        == "beta"
    )
    assert (
        resolve_channel(GITHUB_REF_TYPE="branch", GITHUB_REF_NAME="master", DEFAULT_BRANCH="master")
        == "beta"
    )


def test_other_branch_uses_ref_name(resolve_channel: Callable[..., str]) -> None:
    assert (
        resolve_channel(
            GITHUB_REF_TYPE="branch", GITHUB_REF_NAME="feature/x", DEFAULT_BRANCH="main"
        )
        == "feature/x"
    )
