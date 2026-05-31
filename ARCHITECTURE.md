# Architecture

## Overview

AetherPak turns a Flatpak app into a hosted Flatpak repository backed by two
GitHub services:

- **GHCR** holds the application as OCI images (the large blobs).
- **GitHub Pages** serves a small JSON index (`index/static`), a landing page
  (`index.html`), a `.flatpakrepo` remote-config file, and per-app `.flatpakref`
  files under `refs/`.

A client adds the Pages URL as an `oci+https://` Flatpak remote, reads the index,
and pulls image layers from GHCR by digest.

## Pipeline

```
manifest --build--> OSTree repo --publish--> OCI image in GHCR
                                         \--> index/static + index.html on Pages
client:  Pages index --(digest)--> GHCR blobs
```

1. **build** runs `aetherpak build` (which wraps `flatpak-builder`) inside
   `ghcr.io/aetherpak/cli:<cli-version>-builder` and exports an OSTree
   repo. Alternatively `aetherpak import` ingests a prebuilt `.flatpak` bundle, or
   an existing OSTree repo is copied. It reads `app-id`/`arch`/`branch` from the
   repo ref `app/<id>/<arch>/<branch>`. The branch is the channel: with no
   `branch` input it defaults to `stable` on tag pushes, `beta` on the default
   branch, and the git ref name otherwise.
2. **publish** runs `aetherpak push-oci` to convert the OSTree repo to an OCI
   image and push it to `ghcr.io/<owner>/<repo>` (tag `<app-id>-<branch>-<arch>`,
   signing it when a GPG key is configured; see "Signing"), recording the digest
   and `org.flatpak.*` labels in a per-cell record. `aetherpak build-site` then
   merges an entry into `index/static`, reconciles the index (dropping entries
   whose image no longer exists in the registry), writes
   `<owner>-<repo>.flatpakrepo`, and generates a per-app
   `refs/<app>-<channel>.flatpakref` for each installable entry in the reconciled
   index, copies the static `index.html`, and optionally uploads and deploys the
   Pages artifact.
3. The **reusable workflow** (`publish.yml`) runs one pipeline for both single-
   and multi-app cases. The `plan` job either parses a single `manifest-path`
   (`aetherpak plan --manifest`) or expands an `aetherpak.yaml` (`aetherpak plan
   --config`); both emit the same `(app, arch)` matrix. `build-manifest` /
   `prep-bundle` produce per-cell OSTree repos, `publish-oci` pushes each in
   parallel, and a single concurrency-locked `publish-site` job merges every
   record into the shared index and deploys.

Deployment is optional. With `deploy: false` the reusable workflow uploads the
built site as a plain artifact instead of deploying it, so the files can be served
from a subpath of an existing Pages site or from external hosting. `pages-url`
sets the URL the index and `.flatpakrepo` are written against.

## The index (`index/static`)

A JSON document Flatpak reads directly:

```json
{
  "Registry": "https://ghcr.io",
  "Results": [
    {
      "Name": "owner/repo",
      "Images": [
        {
          "Digest": "sha256:...",
          "Architecture": "amd64",
          "Tags": ["stable"],
          "Labels": {
            "org.flatpak.ref": "app/org.example.App/x86_64/stable",
            "org.flatpak.commit": "...",
            "org.flatpak.metadata": "..."
          }
        }
      ]
    }
  ]
}
```

- `aetherpak build-site` adds or replaces one image per `(ref, arch)` and never
  rewrites the file destructively, so matrix runs across arches, branches, and
  apps accumulate into one index.
- Flatpak resolves an app from the labels and pulls the manifest by `Digest`. The
  GHCR tag is not used for resolution; it only keeps the digest referenced. Images
  are tagged `<app-id>-<branch>-<arch>`, with `.` in the app-id encoded as `_`
  (forced by Flatpak's signature tag-strip; see "Signing"), so several apps in
  the same meta-repo can share one OCI image path without overwriting each
  other's tags.
- The landing page hides entries without `org.flatpak.metadata` (ones a client
  could not install).

## Signing (optional)

Signing is opt-in and GPG-only (Flatpak's OCI verification uses the
`containers/image` simple-signing lookaside, which is GPG, not cosign/keyless).
When a key is configured, `aetherpak push-oci` signs the image manifest in
process and writes a detached signature into the per-cell record; `aetherpak
build-site` assembles the lookaside and supporting files into the site:

- `sigs/<repo>@sha256=<digest>/signature-1`: the detached signature per image.
- `sigs/key.asc`: the exported public key; `sigs/signing.json`: the manifest
  the landing page reads to show verified-install commands.
- Each `.flatpakref` carries `GPGKey` (base64 of the binary key) and
  `SignatureLookaside`, so installs from the ref are verified too (a key the
  `.flatpakrepo` format cannot hold).

`index/static` is cumulative (seeded from the deployed site) but the Pages deploy
replaces the whole site, so each run **backfills** any signature the final index
references but did not just write, fetching it from the deployed site. Rotation
therefore only fully takes effect once every still-listed image has been
re-signed. `mode` is `auto` (sign iff a key is set), `gpg` (require a key, fail
otherwise), or `off`.

**Tag constraint.** Flatpak's OCI verifier builds the expected identity as the
bare `<registry>/<repo>` and strips the tag from the signature's embedded
`docker-reference` with a `[0-9A-Za-z_-]`-only regex before comparing. A tag
containing characters outside that class (notably `.`) fails the strip, leaves
the identity tagged, and rejects every otherwise-good signature. The publish
action therefore encodes `.` in the app-id portion of the OCI tag as `_`; the
canonical app-id stays in `org.flatpak.ref`.

## Multiple apps and serialized publishing

Declare apps in `aetherpak.yaml` and call `publish.yml` with the `config` input:

```yaml
apps:
  - id: org.example.App
    manifest: apps/org.example.App/manifest.yaml
    runtime: gnome-50
    arches: [x86_64, aarch64]
    branch: stable
  - id: com.example.Other
    bundles:
      x86_64:
        url: https://...
        sha256: ...
      aarch64:
        url: https://...
        sha256: ...
```

The workflow runs in five stages:

1. **plan** — expand `aetherpak.yaml` into a matrix; narrow it to apps touched since
   `BASE_SHA` (gitlink/manifest-dir diffs for manifest sources; per-entry diff
   of `aetherpak.yaml` for everything else).
2. **build-manifest** (matrix) — `aetherpak/actions/build@v3` in the flathub
   container, one job per `(app, arch)`; uploads `repo-<app-id>-<arch>`.
3. **prep-bundle** (matrix) — `aetherpak/actions/prep-bundle@v3` per bundle
   cell: fetch URL, verify SHA-256, import into an OSTree repo, and **rebind**
   the imported `app/<id>/<arch>/<bundle_branch>` ref to
   `app/<id>/<arch>/<branch>`. Uploads the same `repo-<app-id>-<arch>`
   artifact shape build-manifest does.
4. **publish-oci** (matrix) — `aetherpak/actions/publish-oci@v3` per cell;
   source-agnostic: downloads `repo-<app-id>-<arch>` and pushes. Parallel-safe;
   writes one record artifact `aetherpak-record-<app-id>-<arch>` per cell.
5. **publish-site** (single, concurrency-locked) — downloads every record
   artifact, runs `aetherpak/actions/publish-site@v3` which merges them into
   `index/static`, reconciles, writes the `.flatpakrepo`, `.flatpakref` files,
   landing page, signing metadata, and Pages artifact; `deploy-pages` follows.

The concurrency lock lives on `publish-site` only — `publish-oci` cells stay
parallel because each pushes an independent OCI image, not the shared index.

### Job containers

Every job runs inside the pre-baked CLI image `ghcr.io/aetherpak/cli` and invokes
`aetherpak` directly, without `aetherpak/setup-cli`. The non-build jobs (`plan`,
`prep-bundle`, `publish-oci`, `publish-site`) use the base tag
`:<cli-version>`, which carries everything they touch — `flatpak`, `ostree`,
`git`, `jq`, and `gpg` (the OCI push/reconcile uses the CLI's embedded registry
client, so no `skopeo` is needed). `build-manifest` uses the `:<cli-version>-builder`
tag, which adds `flatpak-builder` and `flatpak-builder-lint`, and runs
`--privileged`: as root the runtime/SDK installs from the image's baked flathub
remote directly, without the polkit/dbus system helper. Any flathub runtime
works — there is no allowlist — at the cost of a per-build fetch (the image ships
no pre-installed runtime). `cli-version` must name a published image tag
(`v0.7.0` → `:v0.7.0` / `:v0.7.0-builder`); a pin without a matching container
falls back to `setup-cli`.

### Channel handling for bundle sources

Upstream `.flatpak` bundles typically carry `app/<id>/<arch>/master` (flatpak-
builder's default when the upstream manifest omits a branch). `prep-bundle`
rebinds this ref to `app/<id>/<arch>/<branch>` using the `aetherpak.yaml` entry's
`branch` (defaulting to `'stable'`) so the published channel matches what
`aetherpak.yaml` declares. The rebind goes through `flatpak build-commit-from`
so the commit's `xa.ref` binding is rewritten alongside the ref name — a
plain ref rename would leave the binding stale and `flatpak install` would
reject the deployed ref as mismatched.

`index/static` is one file shared by every app. A publish-site run seeds it
from the deployed Pages copy, merges every record in the current run,
reconciles, and deploys: a read-modify-write whose only synchronization channel
is the deployed index. The lock prevents two `publish-site` jobs from racing
the seed-merge-deploy window.

### Records contract

Each `publish-oci` cell writes:

```
<records-dir>/<app-id>-<arch>/
  record.json    { app-id, arch, branch, name, registry, digest, ref, tag }
  labels.json    full OCI label set read from the pushed image
  sigs/<repo>@sha256=<hex>/signature-1   # only when signed
```

`aetherpak build-site` walks the tree in any order, merging each record into the
index; any `sigs/` subtree under a record is copied into `_site/sigs/` (paths are
content-addressed by digest so cells never collide).

## Dependencies

- The `aetherpak` CLI plus `flatpak`/`ostree`/`gpg`/`flatpak-builder` — bundled in
  the CLI container the reusable workflow runs in, or installed by
  `aetherpak/setup-cli` for standalone composite-action use.
- GitHub Pages deployed from Actions (`upload-pages-artifact` + `deploy-pages`).
- GHCR with anonymous pull (public package) for unauthenticated installs.
- Flatpak's OCI remote support (`oci+https://`) and `flatpak-builder-lint`.
- The `ghcr.io/aetherpak/cli` images (base + `-builder`), published for amd64 and arm64.

## Assumptions

- The GHCR package is public; otherwise anonymous `flatpak install` fails.
- The manifest's `runtime`/`sdk` resolve on Flathub; the builder image installs
  them at build time.
- Architectures are a subset of `x86_64`/`aarch64`, since the builder image is
  published for amd64/arm64 only.
- One repository (`Name` is `<owner>/<repo>`) is the unit of the index.

## Limitations

- **Removal is reconcile-based.** Publish merges, then drops index entries whose
  image is gone from the registry (definitive not-found only; transient or auth
  errors keep the entry). To remove an app, channel, or arch, delete its image
  from the registry and re-run publish. There is no in-action delete; registry
  blob deletion is a manual step (see README Maintenance). The reusable
  workflow accepts `reconcile-only: true` to skip every build and just reconcile,
  for catching up the listing after a deletion.
- **Linter strictness.** `flatpak-builder-lint` enforces Flathub store policies,
  some of which fail for self-hosted apps. Screenshots are mirrored to cover the
  common case; set `run-linter: false` to skip the rest.
- **Architecture set.** Limited to what the builder image provides
  (amd64/arm64).
