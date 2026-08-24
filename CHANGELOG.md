# Changelog

## [3.13.0](https://github.com/aetherpak/actions/compare/v3.12.0...v3.13.0) (2026-08-24)


### Features

* adopt config input across composite actions and publish workflow ([#138](https://github.com/aetherpak/actions/issues/138)) ([a118c60](https://github.com/aetherpak/actions/commit/a118c60719003affaeb0af13d8e17d80db073147))

## [3.12.0](https://github.com/aetherpak/actions/compare/v3.11.2...v3.12.0) (2026-08-23)


### Features

* **build:** add config input to support aetherpak.yaml inheritance ([#135](https://github.com/aetherpak/actions/issues/135)) ([44e667d](https://github.com/aetherpak/actions/commit/44e667da0aa6bca76abb436db97e560101f97c82))

## [3.11.2](https://github.com/aetherpak/actions/compare/v3.11.1...v3.11.2) (2026-06-14)


### Bug Fixes

* **ci:** correct jq syntax in prune workflow ([df5e199](https://github.com/aetherpak/actions/commit/df5e1990854c882836ea2e71d810fdcb5cc277e8))


### Miscellaneous Chores

* **deps:** bump aetherpak cli version to v0.32.0 ([#129](https://github.com/aetherpak/actions/issues/129)) ([2a005eb](https://github.com/aetherpak/actions/commit/2a005ebbf354951697dc002d3c6f84b77280d58a))

## [3.11.1](https://github.com/aetherpak/actions/compare/v3.11.0...v3.11.1) (2026-06-11)


### Miscellaneous Chores

* **deps:** bump aetherpak cli version to v0.30.0 ([#126](https://github.com/aetherpak/actions/issues/126)) ([663369c](https://github.com/aetherpak/actions/commit/663369c33bdce582f6725d4538914903cab301da))

## [3.11.0](https://github.com/aetherpak/actions/compare/v3.10.1...v3.11.0) (2026-06-11)


### Features

* **publish:** propagate oci-repository input to build-site step ([caed6a0](https://github.com/aetherpak/actions/commit/caed6a060716359718881371ef4834cc5b75b459))

## [3.10.1](https://github.com/aetherpak/actions/compare/v3.10.0...v3.10.1) (2026-06-10)


### Miscellaneous Chores

* **deps:** bump aetherpak cli version to v0.26.0 ([#120](https://github.com/aetherpak/actions/issues/120)) ([22fd052](https://github.com/aetherpak/actions/commit/22fd052fa8ee56cd3a35c716ba77d866b7944a2c))

## [3.10.0](https://github.com/aetherpak/actions/compare/v3.9.1...v3.10.0) (2026-06-10)


### Features

* support and document plan override-branch and app-id//branch refs ([#117](https://github.com/aetherpak/actions/issues/117)) ([17a4e70](https://github.com/aetherpak/actions/commit/17a4e70c42d0af5b665c925b0389b28e8580a10f))

## [3.9.1](https://github.com/aetherpak/actions/compare/v3.9.0...v3.9.1) (2026-06-10)


### Miscellaneous Chores

* release 3.9.1 ([00cb98f](https://github.com/aetherpak/actions/commit/00cb98f748918a5c7eb4fef636c8f81c0b9c08d3))

## [3.9.0](https://github.com/aetherpak/actions/compare/v3.8.2...v3.9.0) (2026-06-09)


### Features

* **actions:** trust workspace directory and prioritize PR base SHA fallback ([ddb8437](https://github.com/aetherpak/actions/commit/ddb843748e1b81ec14a4e9d34eb0c0f54213429d))
* make pages-url input optional with automated fallback ([0f936ef](https://github.com/aetherpak/actions/commit/0f936efa2dbda69f4328013975118f31f14ccb96))
* optimize cache pruning in container jobs ([210b5d8](https://github.com/aetherpak/actions/commit/210b5d8af6ff23587f744ecabd61557b3e413a7c))
* **publish:** drop default builder-args and update docs ([#106](https://github.com/aetherpak/actions/issues/106)) ([702a2ba](https://github.com/aetherpak/actions/commit/702a2bab9924fe2c82e16f46665f69394d18dd1f))
* remove redundant manual OSTree empty directory restoration ([54c37d7](https://github.com/aetherpak/actions/commit/54c37d79d54d61703a3c1f97b57a7f2d384e2a27))
* scope Flatpak build caches per app ID ([9edf51a](https://github.com/aetherpak/actions/commit/9edf51a17cb478e4fd2fa7e2f7d35c1e3dc0216c))


### Bug Fixes

* resolve container workspace path mapping for TMPDIR ([b967d45](https://github.com/aetherpak/actions/commit/b967d456ee51d6f547f2c052ece8521b6650ca3d))
* revert TMPDIR and FLATPAK_SYSTEM_CACHE_DIR redirections ([c8596a0](https://github.com/aetherpak/actions/commit/c8596a0953b6b6288c2d94773db35492101a884a))

## [3.8.2](https://github.com/aetherpak/actions/compare/v3.8.1...v3.8.2) (2026-06-09)


### Bug Fixes

* support runtime ref types in build bundle export ([22372d9](https://github.com/aetherpak/actions/commit/22372d9fabaec8cd4602ed04f1598861448c9455))
* support runtime refs in publish workflow prebuilt bundle match ([6547346](https://github.com/aetherpak/actions/commit/6547346c6f53e2c982be3dbd5c1ba0424552a6e8))

## [3.8.1](https://github.com/aetherpak/actions/compare/v3.8.0...v3.8.1) (2026-06-08)


### Miscellaneous Chores

* **deps:** bump aetherpak cli version to v0.17.1 ([#93](https://github.com/aetherpak/actions/issues/93)) ([58a96b7](https://github.com/aetherpak/actions/commit/58a96b7f405cb3d0a7382ecee8bfc6175844945c))

## [3.8.0](https://github.com/aetherpak/actions/compare/v3.7.0...v3.8.0) (2026-06-08)


### Features

* resolve remote-name via aetherpak config get ([71b4fca](https://github.com/aetherpak/actions/commit/71b4fcad2ea6145c18a3005902952efc3a3b7ef4))

## [3.7.0](https://github.com/aetherpak/actions/compare/v3.6.1...v3.7.0) (2026-06-07)


### Features

* simplify publish-oci action by delegating ref resolution to CLI ([5644708](https://github.com/aetherpak/actions/commit/5644708f2f3254b3a430e471b87d9697699e0c99))


### Bug Fixes

* prevent non-zero exit status on unsigned/no-sign oci push and site build ([0bfacfd](https://github.com/aetherpak/actions/commit/0bfacfd00ef9114bee0959763ca6df6408ecff46))

## [3.6.1](https://github.com/aetherpak/actions/compare/v3.6.0...v3.6.1) (2026-06-07)


### Miscellaneous Chores

* release 3.6.1 ([5d52ad3](https://github.com/aetherpak/actions/commit/5d52ad3acf39cb4664158e03c2a5945ff0473861))

## [3.6.0](https://github.com/aetherpak/actions/compare/v3.5.3...v3.6.0) (2026-06-04)


### Features

* **workflow:** add prune-github-container-registry shared workflow ([ebe5f32](https://github.com/aetherpak/actions/commit/ebe5f32a65583bd2e19d426fff259d47fd2964d8))

## [3.5.3](https://github.com/aetherpak/actions/compare/v3.5.2...v3.5.3) (2026-06-04)


### Bug Fixes

* **workflow:** remove explicit job-level permissions to allow dry-run without write access ([8c0c7ab](https://github.com/aetherpak/actions/commit/8c0c7ab6b8880db25c06ebf163e66652827cefbc))

## [3.5.2](https://github.com/aetherpak/actions/compare/v3.5.1...v3.5.2) (2026-06-04)


### Miscellaneous Chores

* **deps:** bump aetherpak cli version to v0.15.1 ([#78](https://github.com/aetherpak/actions/issues/78)) ([a9a152d](https://github.com/aetherpak/actions/commit/a9a152d783a1cbbac38c6d8f7d01ef719d266eef))

## [3.5.1](https://github.com/aetherpak/actions/compare/v3.5.0...v3.5.1) (2026-06-03)


### Features

* implement smart caching and customizable controls for build action ([7571c83](https://github.com/aetherpak/actions/commit/7571c832b6d3a83d416ee93010988795120b5ed9))


### Miscellaneous Chores

* release 3.5.1 ([067f8da](https://github.com/aetherpak/actions/commit/067f8dac8bef3bfe269e44ca032ce92827ea2387))

## [3.5.0](https://github.com/aetherpak/actions/compare/v3.4.0...v3.5.0) (2026-06-03)


### Features

* support multiple bundle ingestion and bump default CLI to v0.14.0 ([e987137](https://github.com/aetherpak/actions/commit/e98713749f72c23e49ca0582dca2cba89094827c))
* update E2E tests and documentation to show multiline bundle-path block format ([9f628d4](https://github.com/aetherpak/actions/commit/9f628d4fe563e08788d1c97f8b2cf017738b272f))


### Bug Fixes

* parse multiline bundle-path and url blocks correctly in actions ([d211266](https://github.com/aetherpak/actions/commit/d2112669ceaa09afb7c2b96e9e9844866a6c8e78))

## [3.4.0](https://github.com/aetherpak/actions/compare/v3.3.1...v3.4.0) (2026-06-03)


### Features

* allow dry run in shared publish workflow ([8f3d0db](https://github.com/aetherpak/actions/commit/8f3d0db49f62b908af2e907ca42f05ad7f2a22ea))
* support CLI version overrides, pinned defaults, and automated weekly bump ([#62](https://github.com/aetherpak/actions/issues/62)) ([1a40038](https://github.com/aetherpak/actions/commit/1a400380bc551fd61476a845f3f39b0a8937e423))
* support exporting and uploading built Flatpak bundles ([c40ac54](https://github.com/aetherpak/actions/commit/c40ac5440ec256be4ac9625a679a503ced334c88))
* support local prebuilt bundle artifact ingestion in publish workflow ([521af4d](https://github.com/aetherpak/actions/commit/521af4d2112746b38d7911727506b56fd107739e))


### Bug Fixes

* **ci:** fix credentials config and upgrade create-pull-request to v8 in bump-cli ([03f164c](https://github.com/aetherpak/actions/commit/03f164cfb90388a4acc0b96b50c96e75b6c9ea86))

## [3.3.1](https://github.com/aetherpak/actions/compare/v3.3.0...v3.3.1) (2026-06-02)


### Miscellaneous Chores

* release 3.3.1 ([939795b](https://github.com/aetherpak/actions/commit/939795bc2b96120154bd4f34eb457a8272c0f8ec))

## [3.3.0](https://github.com/aetherpak/actions/compare/v3.2.0...v3.3.0) (2026-06-02)


### Features

* **publish:** support pre-built flatpaks with outputs and app-id forwarding ([a4c0deb](https://github.com/aetherpak/actions/commit/a4c0deb3109fbe32cb2b2b95fa1eb31ed784c239))


### Bug Fixes

* **publish-site:** strip trailing slash from pages-url before build-site ([836fd3d](https://github.com/aetherpak/actions/commit/836fd3dfd042b7c4db73d2075965a413909ebc21))
* trigger setup-cli if any manifest build dependency is missing ([fa2e3ee](https://github.com/aetherpak/actions/commit/fa2e3ee5ae9dd62b5abe438fdc0443e7b3985df0))

## [3.2.0](https://github.com/aetherpak/actions/compare/v3.1.0...v3.2.0) (2026-06-01)


### Features

* **publish:** disable dependency installation in plan and publish-site fallbacks ([532f0c3](https://github.com/aetherpak/actions/commit/532f0c369050c07429df719c0328f17035adcb24))
* **publish:** support setup-cli fallback and site-subpath ([57b518f](https://github.com/aetherpak/actions/commit/57b518f40c4bbb74201c93f24c40f3c1a1cb76f0))

## [3.1.0](https://github.com/aetherpak/actions/compare/v3.0.1...v3.1.0) (2026-06-01)


### Features

* **publish:** adopt aetherpak CLI v0.9.0 with index-template input and status diagnostics ([3d8935d](https://github.com/aetherpak/actions/commit/3d8935d626c0000f59ff80091544c906a654f712))

## [3.0.1](https://github.com/aetherpak/actions/compare/v3.0.0...v3.0.1) (2026-05-31)


### Bug Fixes

* **publish:** fetch submodules in plan job for manifest mode ([c91a3fd](https://github.com/aetherpak/actions/commit/c91a3fd4aab40c637d99005b55a248f65252a8f5))

## [3.0.0](https://github.com/aetherpak/actions/compare/v2.3.1...v3.0.0) (2026-05-31)


### ⚠ BREAKING CHANGES

* **publish:** remove publish-multi.yml; publish.yml handles both modes
* **publish:** unify single- and multi-app into one workflow

### Features

* **plan:** map manifest runtime to flathub container tag ([a83d7c6](https://github.com/aetherpak/actions/commit/a83d7c64d74158cd625824fb93ff95edc7f3d6e7))
* **publish:** remove publish-multi.yml; publish.yml handles both modes ([811d60b](https://github.com/aetherpak/actions/commit/811d60b85c5b6de536768ac21e4aaebb869852a8))
* **publish:** support no-sign and allow-unsigned flags for image signing ([3fd0573](https://github.com/aetherpak/actions/commit/3fd05733eb05ad190a3d6ec290786fc07045480a))
* **publish:** unify single- and multi-app into one workflow ([2ae6e95](https://github.com/aetherpak/actions/commit/2ae6e95ca9ee2ebf257c5d83b3ffa952f532cfa6))


### Bug Fixes

* **publish:** adopt CLI 0.7.0 plan --disable-linter and off-mode --allow-unsigned ([f86490c](https://github.com/aetherpak/actions/commit/f86490cc5854616855db306732fbca215e81f38e))

## [2.3.1](https://github.com/aetherpak/actions/compare/v2.3.0...v2.3.1) (2026-05-29)


### Bug Fixes

* pin aetherpak CLI to v0.6.0 ([eaa781b](https://github.com/aetherpak/actions/commit/eaa781b965da3b5d50320edf3ccfdbe685191863))

## [2.3.0](https://github.com/aetherpak/actions/compare/v2.2.0...v2.3.0) (2026-05-29)


### Features

* **build:** pass builder-args through to flatpak-builder ([3b0fb2f](https://github.com/aetherpak/actions/commit/3b0fb2f54f678399bc592e0d0d84895eaa386dfe))
* delegate the GitHub Actions to the aetherpak CLI ([cb48456](https://github.com/aetherpak/actions/commit/cb48456c0fbff74b0ee26b7b5e075ab64192dffe))
* implement E2E integration test harness and client compatibility checks ([3b3690a](https://github.com/aetherpak/actions/commit/3b3690a31df85267c3bcf2a655e74a0302fed70a))


### Bug Fixes

* pin aetherpak CLI to v0.3.0 ([a5d9936](https://github.com/aetherpak/actions/commit/a5d9936e63f08e8f040ad5ea5cbf764f8db213bb))
* pin aetherpak CLI to v0.4.0 ([2754b15](https://github.com/aetherpak/actions/commit/2754b15a19f659d0ec8499bafd626f396176dcf7))
* pin aetherpak CLI to v0.5.0 ([bac0eb3](https://github.com/aetherpak/actions/commit/bac0eb3f92760dd8abca5524535fe3802310fb75))
* **publish-oci:** restore ostree repo dirs dropped by artifact upload ([3a3c40f](https://github.com/aetherpak/actions/commit/3a3c40fe6045aca29eedae512f597edf8a4f3f47))

## [2.2.0](https://github.com/aetherpak/actions/compare/v2.1.4...v2.2.0) (2026-05-28)


### Features

* **seo:** add og:image and align section indentation ([8233f95](https://github.com/aetherpak/actions/commit/8233f95f7e0e70504fc4f29cc55fcfdf7321677b))
* **seo:** add OpenGraph metadata and wrap sections in main tags ([8cba15f](https://github.com/aetherpak/actions/commit/8cba15f775625e8b4fa23a4c3c3e2cb937c80d6f))


### Bug Fixes

* **publish-site:** single-arch publishes land records ([5a1f84f](https://github.com/aetherpak/actions/commit/5a1f84ff4785e1c74c1e86e49699008451823e62))

## [2.1.4](https://github.com/aetherpak/actions/compare/v2.1.3...v2.1.4) (2026-05-28)


### Bug Fixes

* **publish-oci:** pin records-dir LCA via sentinel ([10d0963](https://github.com/aetherpak/actions/commit/10d0963642233b9d3927052e5a6893dae06d03e7))
* **publish-site:** no-op reconcile when index is absent ([5e47f11](https://github.com/aetherpak/actions/commit/5e47f111937f0adb2b38b1fa637d64736b72d09c))

## [2.1.3](https://github.com/aetherpak/actions/compare/v2.1.2...v2.1.3) (2026-05-27)


### Bug Fixes

* **prep-bundle:** rebind xa.ref via build-commit-from ([5cc8c0b](https://github.com/aetherpak/actions/commit/5cc8c0bede3a7736356d0ac084455d7f716da433))

## [2.1.2](https://github.com/aetherpak/actions/compare/v2.1.1...v2.1.2) (2026-05-27)


### Bug Fixes

* **publish-oci:** rebind bundle ref to target branch ([#17](https://github.com/aetherpak/actions/issues/17)) ([6dc8d4b](https://github.com/aetherpak/actions/commit/6dc8d4b36182cd75e9d6fb31b7c1cb288f8f3cfd))

## [2.1.1](https://github.com/aetherpak/actions/compare/v2.1.0...v2.1.1) (2026-05-27)


### Bug Fixes

* **publish-oci:** normalize OCI tag so flatpak verifies sigs ([#14](https://github.com/aetherpak/actions/issues/14)) ([c746c11](https://github.com/aetherpak/actions/commit/c746c1166f9e0ed5ec503629b8169beff5969212))

## [2.1.0](https://github.com/aetherpak/actions/compare/v2.0.0...v2.1.0) (2026-05-27)


### Features

* **workflows:** add reconcile-only to skip builds ([#11](https://github.com/aetherpak/actions/issues/11)) ([047c040](https://github.com/aetherpak/actions/commit/047c0408b4b87b81a51d9c55b008c84c7cc6ccf9))

## [2.0.0](https://github.com/aetherpak/actions/compare/v1.3.0...v2.0.0) (2026-05-27)


### ⚠ BREAKING CHANGES

* the multi-app config file is renamed from `apps.yaml` to `aetherpak.yaml`. Callers either rename the file at the repo root or pass `config: apps.yaml` to the `plan` / `publish-multi.yml` inputs.

### Features

* **plan:** validate field shapes in apps.yaml entries ([5e7bfe7](https://github.com/aetherpak/actions/commit/5e7bfe798ce75b2b9cc01128ee6ded2f29be3a55))


### Code Refactoring

* rename apps.yaml to aetherpak.yaml and harden action boundaries ([#10](https://github.com/aetherpak/actions/issues/10)) ([05a2d1e](https://github.com/aetherpak/actions/commit/05a2d1e1e75d2dad9f94f0a7c9a0db22a94aa45a))

## [1.3.0](https://github.com/aetherpak/actions/compare/v1.2.1...v1.3.0) (2026-05-27)


### Features

* **plan:** add apps.yaml-to-matrix planner ([23aefd5](https://github.com/aetherpak/actions/commit/23aefd577f6b0154fc3d5a442a3d53e4414b13b3))
* **plan:** add plan composite action ([2746c4d](https://github.com/aetherpak/actions/commit/2746c4d10c51393b038d306c75bcdb8504e434e7))
* **prep-bundle:** add bundle fetch+import+re-tag composite ([c9dfcce](https://github.com/aetherpak/actions/commit/c9dfccedde67e38171fd9350e50195aef459b26f))
* **publish-oci:** add parallel push+sign+record composite ([51407d4](https://github.com/aetherpak/actions/commit/51407d40be8d7004aa2ec35735fe840514be7481))
* **publish-site:** add records-to-site composite ([f2fb962](https://github.com/aetherpak/actions/commit/f2fb962e50a61c27d8378cbaa0b3fb4609a92131))
* **publish:** add records library for cell-level publish data ([1d808d3](https://github.com/aetherpak/actions/commit/1d808d326f6813b8e1258565ce847c5f25b6c37d))
* **workflow:** add publish-multi.yml reusable workflow ([b2d7e3a](https://github.com/aetherpak/actions/commit/b2d7e3a909dae6a25c7f123d4a0d95ca1082a8a4))

## [1.2.1](https://github.com/aetherpak/actions/compare/v1.2.0...v1.2.1) (2026-05-27)


### Bug Fixes

* **publish:** download each arch artifact to an explicit path ([2d582c2](https://github.com/aetherpak/actions/commit/2d582c21bc8459e1fdc5f6109e360b84ea5590bc))

## [1.2.0](https://github.com/aetherpak/actions/compare/v1.1.1...v1.2.0) (2026-05-27)


### Features

* **publish:** add submodules input, default recursive ([ebb5b8f](https://github.com/aetherpak/actions/commit/ebb5b8f05306eebb9497f8916d0c7fab5f708f9e))

## [1.1.1](https://github.com/aetherpak/actions/compare/v1.1.0...v1.1.1) (2026-05-27)


### Bug Fixes

* **site:** keep landing pages contained on mobile ([f049094](https://github.com/aetherpak/actions/commit/f04909446e81076545d9727c6c1d08ca58079eb2))
