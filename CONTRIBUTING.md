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

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/). The release
version is derived from commit types (see Releasing), so the prefix is not
cosmetic:

```
<type>(<optional scope>): <imperative summary>
```

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`.
- **Scopes** are optional but encouraged where they sharpen intent —
  `publish`, `build`, `site`, `ci` (e.g. `feat(publish): …`, `fix(ci): …`).
- Summary: short, imperative, lower-case, no trailing period.
- **Breaking change:** add `!` (`feat(publish)!: …`) or a `BREAKING CHANGE:`
  footer.
- Prefer summary-only; add a body only to explain non-obvious *why*.

A `commit-msg` hook (`conventional-pre-commit`) enforces this locally once
`make setup` has run.

## Releasing

Consumers pin actions via `aetherpak/actions/<action>@v1`, so the floating tags
must always track the latest patch. `.github/workflows/semver.yml` enforces this
and **auto-fixes** the floating tags after every release.

1. **Pick the version** from the commits since the last tag: `fix`/`chore` →
   patch, `feat` → minor, a breaking change → major.
2. **Tag the release commit** (annotated) and push it:

   ```bash
   git tag -a v1.2.0 -m v1.2.0
   git push origin v1.2.0
   ```

3. **Publish the GitHub Release** (newest is Latest):

   ```bash
   gh release create v1.2.0 --title v1.2.0 --generate-notes --verify-tag --latest
   ```

4. **The floating tags move themselves.** Publishing the Release triggers
   *Check SemVer Tags*, which repoints `v1.2` and `v1` to the new patch using the
   `AETHERPAK_ACTION_BOT` GitHub App. The run is green once the tags line up. If
   it ever isn't (normal case — releasing the newest version), the equivalent
   manual fix is:

   ```bash
   git tag -f v1.2 v1.2.0 && git tag -f v1 v1.2.0
   git push -f origin v1.2 v1
   ```

Notes:

- Releases are **immutable** (repo setting). A mistake means a new patch — you
  cannot edit or re-point a published version in place.
- Every patch tag needs its own published Release, and the root `action.yml`
  must keep its `branding` block; the checker errors otherwise.
