# Contributing

## Requirements

- [`uv`](https://docs.astral.sh/uv/): runs the tests and pre-commit via `uvx`,
  fetching Python 3.14 and pytest on demand; no system Python needed. (The
  scripts are pure-stdlib and the publish action pins Python 3.14 via
  `setup-python`, so 3.14 is what they run on in CI and production.)
- For local end-to-end work: `flatpak`, `ostree`, `skopeo`, `jq`.

## Setup

```bash
make setup     # install the pre-commit git hook
```

## Checks

```bash
make test      # unit tests (uvx pytest on Python 3.14)
make lint      # pre-commit: ruff lint + format, ty type check, file checks
make check     # test + lint
```

Tests are pytest function-based, one file per script under `tests/`, with
shared fixtures in `tests/conftest.py`. No dependencies to install: `uvx`
fetches pytest on demand, and the ty hook runs `uv run ty check`, which syncs
the dev dependencies (`ty`, `pre-commit`, `pytest`) on its own.

Pre-commit runs on commit once `make setup` is done, and again in CI.
Configuration lives in `pyproject.toml` (pytest, ruff, and the uv project's dev
dependencies) and `.pre-commit-config.yaml`. ty has no upstream pre-commit
mirror yet ([astral-sh/ty#269](https://github.com/astral-sh/ty/issues/269)), so
it runs as a `local` hook via `uv run`.

## CI

`.github/workflows/test.yml` runs on push and PR:

- **unit tests**: every script (`merge_index`, `reconcile`, `signing`,
  `gen_flatpakrefs`, and the channel resolver).
- **pre-commit**: ruff lint + format, ty type check, and file checks.
- **mock integration**: starts a local OCI registry and runs `build` then
  `publish` against a mock OSTree repo, then asserts reconcile drops a missing
  entry, all with no external services.
- **signing integration / gate**: signs against the local registry and verifies
  the signature with `skopeo`, and asserts `signing: gpg` fails without a key.

## End-to-end testing

The mock integration test covers the scripts and the OCI/index flow without GHCR
or Pages. To verify the full path (a real GHCR push, a Pages deploy, and a real
`flatpak install`), run the actions from a throwaway repo: add a sample manifest,
enable Pages (Source: GitHub Actions), push, then install from the deployed
remote.

## Code style

- Small, focused files; follow the surrounding style.
- Comments explain *why*, not *what*; skip ones that restate the code.
- Python is linted and formatted by ruff and type-checked by ty (`pyproject.toml`).
  Public functions carry type hints and terse Sphinx/RST docstrings
  (`:param:`/`:returns:`).
- Keep commit messages short and imperative.
