# AGENTS.md

Notes for agents and developers working in this repo. For how the system works,
see [ARCHITECTURE.md](ARCHITECTURE.md); for the dev workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

Every action is a thin wrapper over the [`aetherpak` CLI](https://github.com/aetherpak/cli):
it validates inputs, invokes one `aetherpak` command, and surfaces its outputs.
The CLI owns all the real logic (build, import, OCI push, signing, index merge,
reconcile, `.flatpakref`/`.flatpakrepo` generation, channel resolution). It must
be on `PATH`; the reusable workflow's jobs run in the pre-baked CLI container,
and standalone composite-action users install it with `aetherpak/setup-cli`.

- `action.yml`: root composite action; chains `build` then `publish`. Suited to
  prebuilt inputs on a standard runner.
- `build/action.yml`: resolves the channel (`aetherpak resolve-channel`), then by
  source: a manifest builds via `aetherpak build` (inside the builder container),
  a `.flatpak` bundle imports via `aetherpak import`, an OSTree repo is copied;
  coordinates are resolved with `aetherpak inspect-repo`.
- `publish/action.yml`: thin one-shot wrapper around `publish-oci` then
  `publish-site` (one cell, one site, in one job). Suited to single-cell
  consumers with their own runner.
- `publish-oci/action.yml`: parallel-safe push half. A thin signing-mode gate
  decides whether to pass a key, then `aetherpak push-oci` exports OSTree -> OCI,
  signs, pushes, and writes a per-cell record under `<records-dir>/<app-id>-<arch>/`.
- `publish-site/action.yml`: single-instance aggregator. `aetherpak build-site`
  seeds `index/static` from the deployed Pages copy, merges every cell record,
  reconciles against the registry, writes `<remote>.flatpakrepo`, per-app
  `.flatpakref` files, `sigs/signing.json`, and the landing page, and backfills
  signatures. The record contract is `<records-dir>/<app-id>-<arch>/{record.json,labels.json,sigs/...}`.
- `prep-bundle/action.yml`: `aetherpak import` fetches a `.flatpak` URL, verifies
  SHA-256, imports it, and rebinds the `app/<id>/<arch>/<bundle_branch>` ref to
  the consumer-declared `branch` (rewriting the commit's `xa.ref` binding, so
  flatpak does not warn about a deployed-ref mismatch).
- `plan/action.yml`: `aetherpak plan` expands `aetherpak.yaml` into a build
  matrix, narrowed by `git diff` since `base-sha`. Consumed by `publish.yml`.
- `.github/workflows/publish.yml`: the one reusable `workflow_call` workflow.
  Mode is implicit: `manifest-path` selects single-app (`aetherpak plan
  --manifest`), `config` selects multi-app (`aetherpak plan --config`); both
  feed one `plan → build-manifest / prep-bundle → publish-oci → publish-site`
  pipeline. Every job runs inside the pre-baked CLI container and calls
  `aetherpak` directly, without `setup-cli`: the non-build jobs (`plan`,
  `prep-bundle`, `publish-oci`, `publish-site`) use `ghcr.io/aetherpak/cli:<cli-version>`;
  `build-manifest` uses the `-builder` tag (adds `flatpak-builder` + lint) and runs
  `--privileged`, installing the runtime from the image's baked flathub remote.
  `cli-version` must name a published container tag.
- `.github/workflows/site.yml`: deploys this project's own marketing landing page
  (`docs/site/`) to Pages on push to `main`, unrelated to a published app's index.
- `.github/workflows/test.yml`: CI. A `lint` job (pre-commit: actionlint + file
  checks) plus end-to-end jobs that install the released CLI and drive the
  actions against a local OCI registry: build/publish integration, reconcile,
  signing auto-activation, the `gpg`-without-key gate, bundle source, multi-cell
  split, and per-action glue (source validation, plan matrix, prep-bundle,
  signing off + remote-name sanitization).
- `docs/specs/`: architectural design and RFC specifications, named with a CalVer
  sequence prefix `YYYY-MM-NN`. Living documents that should reflect the status quo.

## Invariants

Keep these intact when changing the code:

1. `build` and `publish` stay independently usable; `publish` works with a
   bring-your-own `repo-path` or `bundle-path`.
2. `build`/`publish` resolve `app-id`/`arch`/`branch` from the repo's OSTree ref;
   inputs are only a fallback. With no `branch` input, the channel defaults to
   `stable` on tag pushes, `beta` on the default branch, otherwise the git ref
   name (via `aetherpak resolve-channel`).
3. Never overwrite `index/static` directly; always merge through
   `aetherpak build-site`, so matrix runs (arch/branch/app) accumulate.
4. Index entries carry the full `org.flatpak.*` label set (commit, metadata,
   sizes), not only `org.flatpak.ref`. Flatpak needs them to install.
5. The index `Registry` is a plain URL (`https://ghcr.io`), never `oci+https://`.
6. `index.html` stays static and reads `index/static` at runtime.
7. In the reusable workflow, publish and deploy stay in one `concurrency`-locked
   job. The index is a read-modify-write seeded from the deployed copy, so
   splitting deploy out or dropping the lock reopens the cross-run merge race.
8. `publish-oci` and `publish-site` share the record contract
   `<records-dir>/<app-id>-<arch>/{record.json,labels.json,sigs/...}`, owned by
   the CLI. The actions only pass `--records-dir`; they never read or write the
   record shape themselves.
9. `aetherpak.yaml`'s `branch` field is load-bearing for both source kinds:
   manifest entries build at it; bundle entries are rebound to it by
   `prep-bundle`. The CLI's default of `'stable'` is the consumer-facing
   fallback when `branch` is omitted.
10. `build-manifest` builds in the `:<cli-version>-builder` image under
    `--privileged`; as root the runtime installs from the image's baked flathub
    remote via the default `--system` path, with no polkit/dbus helper. The CLI
    stays environment-agnostic — it emits raw `runtime` + `runtime-version` and
    leaves container choice to the workflow.

## Testing

- `make lint`: pre-commit (actionlint + YAML/whitespace file checks).
- End-to-end coverage runs in `.github/workflows/test.yml`, which installs the
  released CLI via `aetherpak/setup-cli` and exercises the actions against a
  local OCI registry. The CLI's own logic is unit- and integration-tested in the
  `aetherpak/cli` repo.

End-to-end coverage and the CI jobs are described in CONTRIBUTING.md.
