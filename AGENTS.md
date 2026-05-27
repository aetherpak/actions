# AGENTS.md

Notes for agents and developers working in this repo. For how the system works,
see [ARCHITECTURE.md](ARCHITECTURE.md); for the dev workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Layout

- `action.yml`: root composite action; chains `build` then `publish`. Suited to
  prebuilt inputs on a standard runner.
- `build/action.yml`: builds a manifest via
  `flatpak/flatpak-github-actions/flatpak-builder@v6` (inside the flathub
  container), or imports a `.flatpak` bundle or OSTree repo. Resolves
  `app-id`/`arch`/`branch` from the built repo.
- `publish/action.yml`: thin one-shot wrapper around `publish-oci` then
  `publish-site` (one cell, one site, in one job). Suited to single-cell
  consumers with their own runner.
- `publish-oci/action.yml`: parallel-safe push half — OSTree -> OCI image, sign,
  push, inspect, emit a per-cell record under `<records-dir>/<app-id>-<arch>/`.
- `publish-site/action.yml`: single-instance aggregator — reads a records tree,
  seeds `index/static` from the deployed Pages copy, merges every cell,
  reconciles, writes `<remote>.flatpakrepo`, per-app `.flatpakref` files,
  signing metadata, and the landing page; backfills signatures.
- `publish/records.py`: tiny library shared between publish-oci (writer) and
  publish-site (reader); defines the `Record` shape and the `<records-dir>/
  <app-id>-<arch>/{record.json,labels.json,sigs/...}` layout.
- `prep-bundle/action.yml`: fetch a `.flatpak` URL, verify SHA-256, import into
  an OSTree repo, and re-tag the imported `app/<id>/<arch>/<bundle_branch>` ref
  to the consumer-declared `branch`. Channel-normalizes bundle sources so
  publish-oci sees a ref matching the requested channel.
- `plan/action.yml` + `plan/plan.py`: expand `apps.yaml` into a build matrix,
  narrowed by `git diff` since `BASE_SHA`. Consumed by `publish-multi.yml`.
- `.github/workflows/publish-multi.yml`: multi-app reusable workflow. Calls
  `plan` once, runs `build-manifest` / `prep-bundle` matrix jobs in parallel
  (both producing a uniform `repo-<app-id>-<arch>` artifact), then
  `publish-oci` (parallel push) feeding `publish-site` (single,
  concurrency-locked) and one Pages deploy.
- `publish/merge_index.py`: merges one image into `index/static` (one entry per
  ref+arch), carrying the full `org.flatpak.*` label set.
- `publish/reconcile.py`: drops index entries whose image is gone from the
  registry (definitive not-found only; transient/auth errors keep the entry).
- `publish/signing.py`: GPG signing helpers — registries.d YAML, `signing.json`,
  and the signature lookaside paths used to backfill prior runs' signatures.
- `publish/gen_flatpakrefs.py`: generates one one-click `.flatpakref` per
  installable `(app, channel)`, carrying the GPG key + lookaside when signed.
- `shared/resolve-channel.sh`: maps the git ref to the default channel (tag ->
  stable, default branch -> beta, else ref name). Shared by `build` and `publish`
  via `${{ github.action_path }}/../shared/resolve-channel.sh` (the whole repo is
  checked out for either action).
- `publish/index.html`: static landing page; reads `index/static` at runtime.
- `.github/workflows/publish.yml`: reusable `workflow_call` workflow (prep, build
  matrix in the container, then one serialized publish+deploy job). Single-app;
  host many apps via one path-filtered caller workflow each.
- `.github/workflows/site.yml`: deploys this project's own marketing landing page
  (`docs/site/`) to Pages on push to `main` — unrelated to a published app's
  generated `index.html`.
- `.github/workflows/test.yml`: CI (unit tests, pre-commit incl. ty, mock build/
  publish/reconcile integration, and signing auto-activation + gate tests).
- `tests/`: pytest unit tests, one file per script (`merge_index`, `reconcile`,
  `signing`, `gen_flatpakrefs`, and the channel resolver), with shared fixtures in
  `tests/conftest.py`. Run with `make test` (pytest on Python 3.14 via `uvx`).
  The publish action pins Python 3.14 (`setup-python`), so tests match runtime.

## Invariants

Keep these intact when changing the code:

1. `build` and `publish` stay independently usable; `publish` works with a
   bring-your-own `repo-path` or `bundle-path`.
2. `build`/`publish` resolve `app-id`/`arch`/`branch` from the repo's OSTree ref;
   inputs are only a fallback. With no `branch` input, the channel defaults to
   `stable` on tag pushes, `beta` on the default branch, otherwise the git ref
   name (see `shared/resolve-channel.sh`).
3. Never overwrite `index/static` directly; always merge through
   `merge_index.py`, so matrix runs (arch/branch/app) accumulate.
4. Index entries carry the full `org.flatpak.*` label set (commit, metadata,
   sizes), not only `org.flatpak.ref`. Flatpak needs them to install.
5. The index `Registry` is a plain URL (`https://ghcr.io`), never `oci+https://`.
6. `index.html` stays static and reads `index/static` at runtime.
7. In the reusable workflow, publish and deploy stay in one `concurrency`-locked
   job. The index is a read-modify-write seeded from the deployed copy, so
   splitting deploy out or dropping the lock reopens the cross-run merge race.
8. `publish-oci` and `publish-site` share their record shape via
   `publish/records.py`. Any field added to a record is added once, used in both
   places, and covered by a `tests/test_records.py` case.
9. `apps.yaml`'s `branch` field is load-bearing for both source kinds:
   manifest entries build at it; bundle entries are re-tagged to it by
   `prep-bundle`. plan.py's default of `'stable'` is the consumer-facing
   fallback when `branch` is omitted.

## Testing

- `make test`: unit tests.
- `make lint`: pre-commit via `uvx` — ruff lint+format, ty type check
  (`uv run ty check`), and the YAML/whitespace file checks.
- `make check`: both.

End-to-end coverage and the CI jobs are described in CONTRIBUTING.md.
