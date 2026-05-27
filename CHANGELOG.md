# Changelog

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
