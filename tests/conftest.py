"""Shared fixtures for the script unit tests."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

Image = dict[str, object]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def make_image() -> Callable[..., Image]:
    """Factory for an OCI index image entry keyed by its flatpak ref.

    Digest defaults to ``sha256:<arch>`` so distinct arches stay distinct.
    """

    def _make(
        ref: str,
        arch: str = "amd64",
        *,
        digest: str | None = None,
        metadata: bool = True,
        appdata: str | None = None,
    ) -> Image:
        labels: dict[str, str] = {"org.flatpak.ref": ref}
        if metadata:
            labels["org.flatpak.metadata"] = "[Application]\nname=x\n"
        if appdata is not None:
            labels["org.freedesktop.appstream.appdata"] = appdata
        return {"Digest": digest or f"sha256:{arch}", "Architecture": arch, "Labels": labels}

    return _make


@pytest.fixture
def resolve_channel(repo_root: Path) -> Callable[..., str]:
    """Run resolve-channel.sh in a clean env (PATH + given vars), returning stdout.

    A clean env keeps a real CI run's GITHUB_REF_* from leaking into assertions.
    """
    script = repo_root / "shared" / "resolve-channel.sh"

    def _run(**env: str) -> str:
        result = subprocess.run(
            ["bash", str(script)],
            env={"PATH": os.environ.get("PATH", ""), **env},
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    return _run
