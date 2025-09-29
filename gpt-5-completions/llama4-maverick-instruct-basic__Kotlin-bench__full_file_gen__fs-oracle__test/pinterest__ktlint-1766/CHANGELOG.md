# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed
* Do not enable the experimental rules by default when `.editorconfig` properties `disabled_rules` or `ktlint_disabled_rules` are set. ([#1771](https://github.com/pinterest/ktlint/issues/1771))
* A function signature not having any parameters which exceeds the `max-line-length` should be ignored by rule `function-signature` ([#1773](https://github.com/pinterest/ktlint/issues/1773))
* An array annotation with parameter(s) should be placed on a separate line prior to the annotated construct `annotation` ([#1765](https://github.com/pinterest/ktlint/issues/1765))

### Changed

## [0.48.1] - 2023-01-03

### Added

### Removed

### Fixed

* An enumeration class having a primary constructor and in which the list of enum entries is followed by a semicolon then do not remove the semicolon in case it is followed by code element `no-semi` ([#1733](https://github.com/pinterest/ktlint/issues/1733))
* Add API so that KtLint API consumer is able to process a Kotlin script snippet without having to specify a file path ([#1738](https://github.com/pinterest/ktlint/issues/1738))
* Disable the `standard:filename` rule whenever Ktlint CLI is run with option `--stdin` ([#1742](https://github.com/pinterest/ktlint/issues/1742))
* Fix initialization of the logger when `--log-level` is specified. Throw exception when an invalid value is passed. ([#1749](https://github.com/pinterest/ktlint/issues/1749))
* Fix loading of custom rule set JARs.
* Rules provided via a custom rule set JAR (Ktlint CLI) or by an API provider are enabled by default. Only rules in the `experimental` rule set are disabled by default. ([#1747](https://github.com/pinterest/ktlint/issues/1747))

### Changed

* Update Kotlin development version to `1.8.0` and Kotlin version to `1.8.0`.

## [0.48.0] - 2022-12-15