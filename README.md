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
    uses: aetherpak/actions/.github/workflows/publish.yml@v3
    with:
      manifest-path: org.example.App.json
```

By default the app is built for `x86_64` and `aarch64` and deployed to Pages.

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
| `arches` | `x86_64 aarch64` | architectures to build |
| `branch` | `stable` on tags, `beta` on the default branch, else the ref name | Flatpak branch (channel). In config mode, this overrides the branch of all planned apps. |
| `deploy` | `true` | deploy to Pages; `false` builds and uploads the site for you to host |
| `pages-url` | project Pages URL | set this for a custom domain |
| `run-linter` | `true` | run `flatpak-builder-lint` |
| `cache` | `true` | cache flatpak runtimes and builder files |
| `cache-key` | _(empty)_ | Custom cache key prefix for caching build state |
| `cache-state` | `true` | Cache flatpak-builder state (downloads and built modules) |
| `cache-ccache` | `true` | Cache ccache compiler artifacts |
| `cache-build-dir` | `false` | Cache flatpak-builder build directories (requires `--keep-build-dirs` in `builder-args`) |
| `builder-args` | _(empty)_ | extra `flatpak-builder` flags, one per line (note: dependency remotes configured in `aetherpak.yaml` are auto-injected by the CLI now) |
| `registry` | `ghcr.io` | OCI registry host for the image blobs |
| `oci-repository` | this repository | image repository path within the registry |
| `remote-name` | _(empty)_ | Flatpak remote name and `.flatpakrepo` filename. Resolution priority: input value > `AETHERPAK_REMOTE_NAME` env var > `remote_name` in `aetherpak.yaml` > sanitized repo slug `<owner>-<repo>` |
| `signing` | `auto` | sign images: `auto` (sign when a key is set), `gpg`, or `off` (see [Signing](#signing-optional)) |
| `runtime-repo` | Flathub `.flatpakrepo` | `RuntimeRepo` in each generated `.flatpakref`; empty omits it |
| `landing-page` | `true` | write the static `index.html`; `false` to render your own page from `index/static` |
| `index-template` | `aetherpak.yaml` branding | path to a custom HTML index template; overrides `branding.index_template` |
| `artifact-name` | `aetherpak-site` | name of the uploaded site artifact when `deploy: false` |
| `concurrency-group` | per repository | override the publish lock; set only if a repo publishes to several independent sites |
| `site-subpath` | _(empty)_ | Optional subdirectory under site-dir/pages-url to structure the repository files (e.g. `flatpak`) |
| `upload-bundle` | `false` | Export the built application as a single `.flatpak` bundle and upload it as a workflow artifact |
| `prebuilt-bundle-artifact` | _(empty)_ | Name or pattern of prebuilt bundle workflow artifacts to download and ingest. Supports `{arch}`, `{app-id}`, and `{branch}` placeholders |
| `bundle-path` | _(empty)_ | Path to local prebuilt `.flatpak` bundle file(s). Supports multiple comma- or newline-separated paths and globs |
| `dry-run` | `false` | dry run mode: build and verify everything, but skip pushing to the registry and publishing the site |

Secrets `gpg-private-key` and `gpg-private-key-passphrase` enable image signing.
See [Signing](#signing-optional).

## Publishing multiple apps

One repository can host many apps in a single index. Declare them in
`aetherpak.yaml` and call the same workflow with `config` instead of
`manifest-path`:

```yaml
# .github/workflows/publish.yml
name: Publish Flatpaks
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write, pages: write, id-token: write }
jobs:
  publish:
    uses: aetherpak/actions/.github/workflows/publish.yml@v3
    with:
      config: aetherpak.yaml
```

`aetherpak.yaml` lists each app (manifest or prebuilt bundle), its runtime, and
its architectures; the workflow plans the changed apps, builds them in parallel,
and merges them into one shared index. See [ARCHITECTURE.md](ARCHITECTURE.md) for
the schema. Change detection rebuilds only apps whose manifest directory or
config entry changed since the previous commit.

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
       uses: aetherpak/actions/.github/workflows/publish.yml@v3
       with:
         manifest-path: org.example.App.json
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

To brand the generated landing page rather than replace it, point `index-template`
(or `branding.index_template` in `aetherpak.yaml`) at a custom HTML template; the
other `branding` keys (`logo_url`, `favicon_url`, `accent_color`, `footer_text`)
tune the default page.

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

The pipeline is also available as composite actions for custom workflows. These
delegate to the [`aetherpak` CLI](https://github.com/aetherpak/cli).

If the `aetherpak` CLI is not found on the runner's `PATH`, the composite
actions will automatically invoke `aetherpak/setup-cli@v1` to install it.
For non-build actions (`plan` and `publish-site`), the automatic fallback
disables system dependency installation (like `flatpak` and `ostree`) to save
runner setup time.

You can still manually configure `aetherpak/setup-cli` if you need to pin to a
specific CLI version or customize installations:

- `aetherpak/actions`: the root composite that chains `build` then `publish` in a
  single step. Best for prebuilt inputs (a `.flatpak` bundle or OSTree repo) on a
  standard runner; manifest builds should use the reusable workflow, which
  supplies the builder container.
- `aetherpak/actions/build`: build a manifest with `flatpak-builder`, or import
  a prebuilt `.flatpak` bundle or OSTree repository.
- `aetherpak/actions/publish`: push an OSTree repo to GHCR, merge the index, and
  write the site. It works on its own with a `repo-path` (your own OSTree repo)
  or `bundle-path` (a `.flatpak`), so you can publish output from any toolchain
  (for example a Rust/Tauri build) without the `build` action.

### Publishing a pre-built Flatpak bundle (.flatpak)

You can publish a pre-built flatpak bundle using a workflow like:

```yaml
name: Publish Pre-built Flatpak
on: { push: { branches: [main] } }
permissions:
  contents: read
  packages: write
  pages: write
  id-token: write
jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v6
      # Download or fetch your pre-built app.flatpak here
      - uses: aetherpak/actions/publish@v3
        with:
          bundle-path: app.flatpak
          pages-url: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}
      - id: deploy
        uses: actions/deploy-pages@v5
```

You can also publish multiple pre-built bundles simultaneously (e.g., for different architectures or applications) by specifying a multiline block (newline-separated) or comma-separated list of paths/wildcard patterns to `bundle-path`. Since coordinates are auto-detected from each bundle's internal metadata, you must **not** provide `app-id` or `arch` inputs when publishing multiple bundles:

```yaml
      - uses: aetherpak/actions/publish@v3
        with:
          bundle-path: |
            build/*.flatpak
            build/org.flatpak.AppA.flatpak
            build/org.flatpak.AppB.flatpak
          pages-url: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}
```

The reusable workflow pushes blobs to GHCR. To target another registry, call
`publish` directly with `registry`, `oci-repository`, and `registry-token` (add
`insecure-registry: true` for a local or HTTP registry):

```yaml
- uses: aetherpak/setup-cli@v1   # installs the aetherpak CLI on PATH
- uses: aetherpak/actions/publish@v3
  with:
    repo-path: _repo            # or bundle-path: app.flatpak
    registry: registry.example.com
    oci-repository: my-org/my-app
    registry-token: ${{ secrets.REGISTRY_TOKEN }}
    pages-url: https://flatpak.example.com
```

### Ingesting pre-built bundle artifacts in the reusable workflow

If you package your application dynamically in a previous job on a runner (for example, via Electron Forge) and upload it as a workflow artifact, you can pass the artifact name/pattern to the reusable workflow using the `prebuilt-bundle-artifact` input:

```yaml
name: Publish Pre-built Artifact
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write, pages: write, id-token: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      # ... build your .flatpak here ...
      - uses: actions/upload-artifact@v7
        with:
          name: flatpak-bundle-${{ matrix.arch }}
          path: out/make/*.flatpak

  publish:
    needs: build
    uses: aetherpak/actions/.github/workflows/publish.yml@v3
    with:
      config: aetherpak.yaml
      prebuilt-bundle-artifact: "flatpak-bundle-{arch}"
```

The workflow will download the artifact, resolve any `{arch}`, `{app-id}`, or `{branch}` placeholders in the name, and find the matching `.flatpak` bundle inside it. If the downloaded artifact contains multiple `.flatpak` files, the workflow will use `flatpak info --show-ref` to automatically identify and select the one matching the current matrix cell's `app-id` and `arch`.

### Ingesting local pre-built bundles in the reusable workflow

If you have prebuilt `.flatpak` bundle files locally in the checked-out repository (or built in a previous job on a self-hosted runner where the workspace is shared), you can pass them directly using the `bundle-path` input. The reusable workflow will publish them in a single job without compiling or running a matrix:

```yaml
name: Publish Local Pre-built Bundles
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write, pages: write, id-token: write }
jobs:
  publish:
    uses: aetherpak/actions/.github/workflows/publish.yml@v3
    with:
      bundle-path: |
        build/*.flatpak
        build/org.flatpak.AppA.flatpak
```

## More

- [ARCHITECTURE.md](ARCHITECTURE.md): how the pieces fit together, what it relies
  on, and its limitations.
- [CONTRIBUTING.md](CONTRIBUTING.md): developing and testing the actions.

## License

MIT. See [LICENSE](LICENSE).
