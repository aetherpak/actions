# Integration Test Harness Specification for AetherPak Actions

This document specifies the design and implementation of the local and CI-compatible end-to-end (E2E) integration test harness for aetherpak/actions.

The goal of this harness is to verify the entire pipeline—from manifest building or bundle importing, through registry pushing and static site indexing, up to a real `flatpak` client installation and verification—without polluting the developer's system or external servers.

---

## 1. Goal & Requirements

### The Gap
The prior test suite only included:
- **Unit Tests:** Standalone scripts (`reconcile.py`, `signing.py`, etc.) using mocks and in-memory fixtures.
- **Mock Integration Tests:** Runner-level checks that verify output files with `jq` and `skopeo standalone-verify`, but never installed apps.

**What was missing:** The harness did not run the actual `flatpak` client to perform `flatpak remote-add` and `flatpak install`. The new harness validates:
1. Compatibility of generated index, refs, and signatures with Flatpak's native OCI engine.
2. Multi-app change detection, matrix mapping, and reconciliation lifecycles from the client's perspective.
3. Signing verification failure paths (e.g., tampered signatures, key mismatches) on a real client.

### Requirements
The E2E test harness must:
1. **Be Isolated & Safe:** Do not mutate the developer's global flatpak environment or system-level configurations.
2. **Be Mock-Backed:** Run entirely locally, pulling from a local containerized OCI registry and serving Pages artifacts via a local HTTP server.
3. **Be Automated & Portable:** Run locally under a single `make` target and run seamlessly in GitHub Actions.
4. **Test Real Scenarios:** Include single-app, GPG-signed, bundle-imported, multi-app, and reconciliation (delisting) workflows.
5. **Ensure Robust Cleanup:** Guaranteed cleanup of all local servers, containers, temporary flatpak registries, and local files even in the event of test failures.

---

## 2. Prerequisites & Production Changes

To enable the test harness to run successfully, transport and configuration constraints were addressed in the production codebase.

### A. HTTP Transport Scheme for Insecure Registries
A local test `registry:2` instance operates over plain HTTP. While `insecure-registry: true` relaxes `skopeo`'s TLS verification during pushes, the registry scheme written into the index must match.
- Modified [publish-oci/action.yml](../../publish-oci/action.yml) and [publish-site/action.yml](../../publish-site/action.yml) to write `http://{REGISTRY}` (instead of `https://`) for the index `Registry` URL when `insecure-registry: true` is passed.

### B. Index Image Fields
Flatpak requires specific OCI index metadata fields. Each image entry in the built index contains:
- `Digest`
- `OS` (e.g. `linux`)
- `Architecture` (e.g. `amd64`, `arm64`)
- `MediaType` (set to `application/vnd.oci.image.manifest.v1+json`)
- `Labels` (carrying `org.flatpak.ref`, `org.flatpak.commit`, and `org.flatpak.metadata`)
- `Tags`

### C. Dynamic Reusable Workflows Checkout
To ensure workflows under test run the active in-branch/PR versions of actions, the reusable workflows [.github/workflows/publish.yml](../../.github/workflows/publish.yml) and [.github/workflows/publish-multi.yml](../../.github/workflows/publish-multi.yml) checkout the repo dynamically by parsing `github.job_workflow_ref`:
```yaml
- name: Resolve actions ref
  id: aref
  env:
    JWR: ${{ github.job_workflow_ref }}
  run: echo "ref=${JWR##*@}" >> "$GITHUB_OUTPUT"
- name: Check out actions repo
  uses: actions/checkout@v6
  with:
    repository: aetherpak/actions
    ref: ${{ steps.aref.outputs.ref }}
    path: .github/actions/aetherpak
```
Subsequent jobs reference local composite paths, e.g. `uses: ./.github/actions/aetherpak/build`.

---

## 3. Architecture & Components

```
                                      +---------------------------------------------+
                                      |          Test Sandbox Environment           |
                                      |                                             |
  +------------------+                |  +------------------+                       |
  |                  |   Runs build   |  |   Local _repo    |                       |
  |  Build Action /  | -------------> |  |   (OSTree)       |                       |
  |  prep-bundle     |                |  +------------------+                       |
  |                  |                |           |                                 |
  +------------------+                |           | Runs publish-oci                |
                                      |           v                                 |
                                      |  +------------------+                       |
                                      |  |  _oci-image /    |                       |
                                      |  |  Local Records   |                       |
                                      |  +------------------+                       |
                                      |           |                                 |
                                      |           | Pushes to                       |
                                      |           v                                 |
  +------------------+                |  +------------------+                       |
  |  Local Registry  | <============= |  |                  |                       |
  |   (Container)    |                |  |  Publish Site /  |                       |
  |  localhost:PORT  | <------------- |  |  reconcile.py    |                       |
  |                  |   Pulls blobs  |  |                  |                       |
  +------------------+                |  +------------------+                       |
                                      |           |                                 |
                                      |           | Generates                       |
                                      |           v                                 |
  +------------------+                |  +------------------+                       |
  | Local Web Server | <============= |  |                  |                       |
  |  localhost:PORT  |                |  |    _site Dir     |                       |
  |                  |   Serves index |  +------------------+                       |
  +------------------+                |                                             |
           ^                          +---------------------------------------------+
           |
           | Queries index
           v
  +------------------+
  | Isolated Client  |
  |  flatpak CLI     |
  | (FLATPAK_USER_DIR|
  |  sandboxed)      |
  +------------------+
```

### A. Local Services Mocks
- **Registry Container:** A standard Docker/Podman container running the `registry:2` image on an ephemeral, randomly assigned port. To avoid collisions during parallel tests, the name of the container is uniquely port-suffixed: `aep-test-registry-{port}`.
- **Pages Web Server:** A background Python HTTP server (`http.server` running in a separate thread) serving the generated `site/` directory on an ephemeral port.

### B. Isolated Flatpak Client Sandbox
- **`FLATPAK_USER_DIR`**: Pointed to a temporary directory inside the test workspace root (`tests/tmp_integration/flatpak_user`).
- **Isolation Enforcement**: Always execute flatpak client CLI commands using the `--user` flag. GHA workflows install flatpak via `sudo apt-get install -y flatpak ostree` in the setup job.

---

## 4. Test Scenarios

To install applications, the `flatpak` client requires valid OSTree commits with metadata. The test suite builds a minimal real flatpak application structure using `flatpak build-commit-from` (with root ownership and canonical permissions) to create a valid OCI representation.

### Scenario 1: Single-App Manifest-Based Flow
- **Input:** A dynamically constructed Flatpak application file tree and metadata.
- **Workflow:**
  1. Initialize local OSTree repo and commit files with metadata via `flatpak build-commit-from`.
  2. Push the built commit to the local container registry using `skopeo copy`.
  3. Index and generate the static Pages site directory using `publish/merge_index.py`.
  4. Generate `.flatpakref` files using `publish/gen_flatpakrefs.py`.
  5. Add the mock remote and install via flatpak:
     `flatpak remote-add --user --no-gpg-verify mock-remote oci+http://localhost:PORT`
     `flatpak install --user -y mock-remote <app-id>`
  6. Assert installation success and clean up.

### Scenario 2: Single-App Bundle Import Flow
- **Input:** A pre-built `.flatpak` bundle of the minimal test application.
- **Workflow:**
  1. Export the built test app into a `.flatpak` bundle using `flatpak build-bundle`.
  2. Import the bundle into a clean repo using `flatpak build-import-bundle`.
  3. Push and index the imported repo.
  4. Verify the remote-add and installation on the client.
  5. Clean up.

### Scenario 3: GPG-Signed Deployment Flow & Enforcement
- **Input:** An ephemeral GPG key pair.
- **Workflow:**
  1. Generate a temporary GPG key pair during test setup.
  2. Push to the registry using `skopeo copy --sign-by=<fpr>`, staging lookaside signatures into `site/sigs/`.
  3. Export the ASCII-armored public key to `key.asc` (for flatpak client import) and a binary base64-encoded file `key.b64` (for `publish/gen_flatpakrefs.py`).
  4. Write `signing.json` manifest via `publish/signing.py` and run the indexer.
  5. Generate refs, add the remote (specifying the GPG key and the lookaside URL), and verify the GPG-verified installation.
  6. **Enforcement Failure Path Verification:** Write random bytes to the lookaside signature file in `site/sigs/` to tamper with it. Flush client cache, attempt to re-install, and assert that installation fails with a signature verification error.
  7. Clean up.

### Scenario 4: Multi-App Matrix Deployment Flow
- **Input:** Multiple applications built or imported concurrently.
- **Workflow:**
  1. Build/push `app-a` and `app-b` to the local registry.
  2. Run `publish/merge_index.py` for both apps to aggregate them into the shared index directory.
  3. Add the remote and verify that both `app-a` and `app-b` are successfully listed and installable.
  4. Clean up.

### Scenario 5: Reconciliation & De-listing Flow
- **Input:** Index populated with both `app-a` and `app-b`.
- **Workflow:**
  1. Delete `app-b` from the containerized registry using `skopeo delete`.
  2. Run `publish/reconcile.py` against the static index.
  3. Verify `app-b` is removed from the static index while `app-a` remains.
  4. Refresh the client cache, assert `app-b` is no longer visible or installable, and verify `app-a` installs successfully.
  5. Clean up.

---

## 5. Harness Lifecycle & Cleanup Mechanics

To prevent orphaned containers, dangling processes, and stale environment files, the harness follows a strict lifecycle structure using Python's pytest fixtures:
- **`registry_server` fixture:** Spin up `aep-test-registry-{port}` using Podman or Docker. Clean up the container at the end of each test using a `finally` block or context teardown.
- **`test_dir` fixture:** Set up a workspace-local temporary folder under `tests/tmp_integration`. Delete the folder recursively upon test completion, including the `FLATPAK_USER_DIR` sandboxed client directories.

---

## 6. Integration & Tooling

### File Layout
The test harness is implemented in:
- [tests/test_harness.py](../../tests/test_harness.py): The pytest E2E client format compatibility suite.

### Commands & Automation
The integration suite is run via:
```makefile
integration-test: ## Run the end-to-end flatpak client integration tests
	uv run --python 3.14 pytest -m integration
```
This target is executed in the GHA CI workflow [.github/workflows/test.yml](../../.github/workflows/test.yml) after setting up Flatpak and OSTree on the runner.
