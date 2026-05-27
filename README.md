# AetherPak Actions

GitHub Actions that build Flatpak applications and host them as a Flatpak
repository, using GitHub Container Registry (GHCR) for the package blobs and
GitHub Pages for a small registry index and a landing page.

<p align="center">
  <a href="https://aetherpak.github.io/actions-demo/">
    <img src="https://raw.githubusercontent.com/aetherpak/actions/main/docs/site/preview.png" alt="AetherPak registry landing page with one-click Flatpak install" width="480">
  </a>
  <br>
  <em>The page AetherPak deploys. Single-app: <a href="https://aetherpak.github.io/actions-demo/">live demo</a> · <a href="https://github.com/aetherpak/actions-demo">repo</a>. Multi-app: <a href="https://abn.github.io/flatpakrepo/">live demo</a> · <a href="https://github.com/abn/flatpakrepo">repo</a></em>
</p>

## Why OCI + Pages

A static-HTTP OSTree repository serves an app as many small objects, so clients
make hundreds of requests. That is slow, and it trips GitHub Pages rate limits.
AetherPak uses Flatpak's native OCI support instead:

- Application layers (blobs) live in GHCR as OCI images.
- A small JSON index (`index/static`) and a landing page are served from Pages.
- Clients read the index from Pages and pull layers from GHCR in large chunks.

## Quick start

1. Enable Pages: repository Settings, then Pages, then Source: **GitHub Actions**.
2. Add `.github/workflows/publish.yml`:

```yaml
name: Publish Flatpak
on: { push: { branches: [main] } }
permissions:
  contents: read
  packages: write
  pages: write
  id-token: write
jobs:
  publish:
    uses: aetherpak/actions/.github/workflows/publish.yml@v1
    with:
      manifest-path: org.example.App.json
      runtime: gnome-50            # flathub container tag matching your runtime
```

`runtime` is the tag of `ghcr.io/flathub-infra/flatpak-github-actions` for your
app's runtime (`gnome-50`, `freedesktop-24.08`, `kde-6.7`, and so on). By default
the app is built for `x86_64` and `aarch64` and deployed to Pages.

After the first run, make the GHCR package public so users can install without
authenticating: the package's page, then **Package settings**, then **Change
visibility**, then **Public**.

For an organization repository, an owner must first allow public packages,
otherwise the image is created private and can't be switched. Do this **before**
the first publish: **Organization → Settings → Packages → Package creation**,
then enable **Public**.

### Options

| Input | Default | Purpose |
|---|---|---|
| `manifest-path` | _(required)_ | Flatpak manifest to build |
| `runtime` | _(required)_ | flathub builder container tag |
| `arches` | `x86_64 aarch64` | architectures to build |
| `branch` | `stable` on tags, `beta` on the default branch, else the ref name | Flatpak branch (channel) |
| `deploy` | `true` | deploy to Pages; `false` builds and uploads the site for you to host |
| `pages-url` | project Pages URL | set this for a custom domain |
| `run-linter` | `true` | run `flatpak-builder-lint` |
| `cache` | `true` | cache flatpak runtimes and builder files |
| `registry` | `ghcr.io` | OCI registry host for the image blobs |
| `oci-repository` | this repository | image repository path within the registry |
| `remote-name` | repo slug `<owner>-<repo>` | Flatpak remote name and `.flatpakrepo` filename; override for a friendlier name |
| `signing` | `auto` | sign images: `auto` (sign when a key is set), `gpg`, or `off` (see [Signing](#signing-optional)) |
| `runtime-repo` | Flathub `.flatpakrepo` | `RuntimeRepo` in each generated `.flatpakref`; empty omits it |
| `landing-page` | `true` | write the static `index.html`; `false` to render your own page from `index/static` |
| `artifact-name` | `aetherpak-site` | name of the uploaded site artifact when `deploy: false` |
| `concurrency-group` | per repository | override the publish lock; set only if a repo publishes to several independent sites |

Secrets `gpg-private-key` and `gpg-private-key-passphrase` enable image signing.
See [Signing](#signing-optional).

## Publishing multiple apps

One repository can host many apps in a single index. Give each app its own
path-filtered workflow so only the changed app rebuilds:

```yaml
# .github/workflows/publish-foo.yml
name: Publish Foo
on: { push: { branches: [main], paths: ['org.example.Foo.json'] } }
permissions: { contents: read, packages: write, pages: write, id-token: write }
jobs:
  publish:
    uses: aetherpak/actions/.github/workflows/publish.yml@v1
    with:
      manifest-path: org.example.Foo.json
      runtime: gnome-50
```

Add a `publish-bar.yml` for the next app, and so on. Each run merges its app into
the shared index, so the listing accumulates. Publishing is serialized per
repository, so concurrent runs apply one at a time instead of overwriting the
index; if several apps change at the same instant, re-push any that did not
publish. Tag pushes use the `stable` channel, the default branch uses `beta`.

## Installing published apps

The landing page lists each app with its channels. Each release has an **Install**
button that downloads a per-app `.flatpakref` (`refs/<app>-<channel>.flatpakref`);
opening it adds the remote and installs the app in one step. When signing is
enabled the ref is verified (it embeds the key and signature lookaside), so the
install is verified too.

To add the whole repository from the command line instead (the remote is named
`<owner>-<repo>` by default; override with `remote-name`):

```bash
# unsigned, or older clients (< 1.17):
flatpak remote-add --if-not-exists --user --no-gpg-verify \
  <owner>-<repo> oci+https://<owner>.github.io/<repo>

# signed (flatpak >= 1.17): verified, no key fetch needed
flatpak remote-add --user \
  --signature-lookaside=https://<owner>.github.io/<repo>/sigs \
  <owner>-<repo> https://<owner>.github.io/<repo>/<owner>-<repo>.flatpakrepo

flatpak install --user <owner>-<repo> org.example.App
```

A `<owner>-<repo>.flatpakrepo` (linked from the landing page) configures the remote
for every app and channel. When signing is on it embeds the public key, but a
`.flatpakrepo` cannot carry the signature lookaside, so adding it through a GUI
installer leaves verification incomplete until you run the `remote-modify` command
the landing page shows after download:

```bash
flatpak remote-modify --user \
  --signature-lookaside=https://<owner>.github.io/<repo>/sigs <owner>-<repo>
```

Each `.flatpakref` defaults its `RuntimeRepo` to Flathub so installing from it can
pull the app's runtime; set the `runtime-repo` input to change or empty it.

## Signing (optional)

Signing is optional. With no key configured, repositories behave as above
(`--no-gpg-verify`). Configure a GPG key and each pushed OCI image is signed; the
signature, public key, and `sigs/signing.json` are published alongside the index,
and clients can install with verification.

1. Generate a key (CI keys are typically passphrase-less):

   ```bash
   gpg --batch --gen-key <<EOF
   %no-protection
   Key-Type: RSA
   Key-Length: 4096
   Name-Real: Example Releases
   Name-Email: releases@example.org
   Expire-Date: 0
   %commit
   EOF
   gpg --armor --export-secret-keys releases@example.org
   ```

2. Store the armored private key as the repository **secret**
   `gpg-private-key` (and `gpg-private-key-passphrase` if protected), then pass
   it to the workflow:

   ```yaml
   jobs:
     publish:
       uses: aetherpak/actions/.github/workflows/publish.yml@v1
       with:
         manifest-path: org.example.App.json
         runtime: gnome-50
         signing: gpg
       secrets:
         gpg-private-key: ${{ secrets.GPG_PRIVATE_KEY }}
   ```

3. Install with verification. With a key set, the landing page shows the verified
   `remote-add` for your repository (the signed commands under
   [Installing published apps](#installing-published-apps)). Clients on flatpak
   < 1.17 cannot read the lookaside and fall back to the `--no-gpg-verify`
   command, also shown on the landing page.

**Rotation:** generate a new key, replace the secret, and re-publish **every
channel**. Each publish re-signs the image it pushes, and rotation only fully
takes effect once every image still listed in the index has been re-signed with
the new key. The new public key replaces the old one on the next deploy.

## Host it yourself

Set `deploy: false` to keep AetherPak off your Pages site. The workflow then
uploads the built site as an `aetherpak-site` artifact and skips deployment. Serve
that artifact yourself (under a subpath of an existing Pages site, or on external
hosting) and set `pages-url` to the final URL so the index and `.flatpakrepo`
reference it. Use `landing-page: false` to skip `index.html` and render your own
page from `index/static`.

## Maintaining the repository

To remove an app, channel, or architecture, delete its image from the registry
and re-run the publish workflow. Every publish reconciles `index/static` against
the registry and drops entries whose image no longer exists, so the listing
disappears on the next run.

Delete the image with whatever your registry supports:

- GHCR (web UI): your profile or org, then Packages, the package, the version
  (tagged `<branch>-<arch>` or by digest), then Delete version. No token needed.
- GHCR (CLI): `gh api -X DELETE /orgs/OWNER/packages/container/PKG/versions/ID`
  with a token that has `delete:packages`.
- Registries that support the OCI delete API: `skopeo login REGISTRY` then
  `skopeo delete docker://REGISTRY/NAME@DIGEST`.

The index serves the latest image per channel, so reconcile only removes entries
whose image is genuinely gone.

Pass `reconcile-only: true` (workflow dispatch) to skip every build and just
reconcile against the registry — useful when an image is deleted and you only
need the listing to catch up.

## Standalone actions

The pipeline is also available as composite actions for custom workflows:

- `aetherpak/actions`: the root composite that chains `build` then `publish` in a
  single step. Best for prebuilt inputs (a `.flatpak` bundle or OSTree repo) on a
  standard runner; manifest builds should use the reusable workflow, which
  supplies the flathub builder container.
- `aetherpak/actions/build`: build a manifest in the flathub container, or import
  a prebuilt `.flatpak` bundle or OSTree repository.
- `aetherpak/actions/publish`: push an OSTree repo to GHCR, merge the index, and
  write the site. It works on its own with a `repo-path` (your own OSTree repo)
  or `bundle-path` (a `.flatpak`), so you can publish output from any toolchain
  (for example a Rust/Tauri build) without the `build` action.

The reusable workflow pushes blobs to GHCR. To target another registry, call
`publish` directly with `registry`, `oci-repository`, and `registry-token` (add
`insecure-registry: true` for a local or HTTP registry):

```yaml
- uses: aetherpak/actions/publish@v1
  with:
    repo-path: _repo            # or bundle-path: app.flatpak
    registry: registry.example.com
    oci-repository: my-org/my-app
    registry-token: ${{ secrets.REGISTRY_TOKEN }}
    pages-url: https://flatpak.example.com
```

## More

- [ARCHITECTURE.md](ARCHITECTURE.md): how the pieces fit together, what it relies
  on, and its limitations.
- [CONTRIBUTING.md](CONTRIBUTING.md): developing and testing the actions.

## License

MIT. See [LICENSE](LICENSE).
