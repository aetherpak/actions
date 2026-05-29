# Contributing

## Requirements

These actions are thin wrappers over the [`aetherpak` CLI](https://github.com/aetherpak/cli);
all the build, publish, signing, and index logic lives there. Working on the
actions themselves needs little:

- [`pre-commit`](https://pre-commit.com/) for the lint hooks (actionlint and the
  YAML/whitespace checks). `make setup` installs the git hook.
- For running the end-to-end jobs locally: the `aetherpak` CLI on `PATH`
  (download a release or `go build` the CLI repo), plus `flatpak`, `ostree`,
  `skopeo`, `jq`, and a container runtime.

## Setup

```bash
make setup     # install the pre-commit git hook
```

## Checks

```bash
make lint      # pre-commit: actionlint + YAML/whitespace checks
```

Pre-commit runs on commit once `make setup` is done, and again in CI. The hook
configuration lives in `.pre-commit-config.yaml`.

## Testing

The actions carry no unit tests of their own; the logic they wrap is unit- and
integration-tested in the `aetherpak/cli` repository. Action-level behaviour is
covered by the end-to-end jobs in `.github/workflows/test.yml`, which install
the released CLI via `aetherpak/setup-cli` and run the actions against a local
OCI registry and mock OSTree repos. Those jobs assert the wiring around each CLI
call: source validation, the signing-mode gate, remote-name sanitization, plan
matrix expansion, reconcile, and signature verification.

To verify the full production path (a real GHCR push, a Pages deploy, and a real
`flatpak install`), run the actions from a throwaway repo: add a sample manifest
(or an `aetherpak.yaml`), enable Pages (Source: GitHub Actions), push, then
install from the deployed remote.

## Code style

- Small, focused files; follow the surrounding style.
- Comments explain *why*, not *what*; skip ones that restate the code.
- Action YAML stays thin: validate inputs, map them to a single `aetherpak`
  command, surface its outputs. Keep substantive logic in the CLI, not in bash.

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

Releases are automated by [release-please](https://github.com/googleapis/release-please)
(`.github/workflows/release.yml`), driven by the Conventional Commits above.

1. **Land `feat`/`fix` commits on `main`.** release-please maintains a standing
   *"chore(main): release X.Y.Z"* PR with the computed version and `CHANGELOG.md`
   (`feat` → minor, `fix` → patch, breaking → major; `chore`/`ci`/`docs`-only
   changes don't trigger a release). You can also refresh it from the *Release*
   workflow's run button.
2. **Merge that PR** when ready — release-please tags `vX.Y.Z` and publishes the
   GitHub Release.
3. Publishing fires *Check SemVer Tags* (`semver.yml`), which moves the floating
   `vX.Y`/`vX` tags to the new patch. (Both run as the `AETHERPAK_ACTION_BOT`
   GitHub App, so release-please's release actually triggers the checker — a
   `GITHUB_TOKEN` release would not.)

Notes:

- Releases are **immutable** (repo setting). A mistake means a new patch — you
  cannot edit or re-point a published version in place.
- The root `action.yml` must keep its `branding` block or the checker errors.
- To release by hand if ever needed: tag `vX.Y.Z`, `gh release create vX.Y.Z
  --generate-notes --verify-tag --latest`; the checker then moves the floating
  tags.
