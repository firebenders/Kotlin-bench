# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

* Add rule `class-signature`. This rule rewrites the class header to a consistent format. In code style `ktlint_official`, super types are always wrapped to a separate line. In other code styles, super types are only wrapped in classes having multiple super types. Especially for code style `ktlint_official` the class headers are rewritten in a more consistent format. See [examples in documentation](https://pinterest.github.io/ktlint/latest/rules/experimental/#class-signature). `class-signature` [#875](https://github.com/pinterest/ktlint/issues/1349), [#1349](https://github.com/pinterest/ktlint/issues/875)

### Removed

### Fixed

* Allow to disable ktlint in `.editorconfig` for a glob ([#2100](https://github.com/pinterest/ktlint/issues/2100))
* Fix wrapping of nested function literals `wrapping` ([#2106](https://github.com/pinterest/ktlint/issues/2106))
* Do not indent class body for classes having a long super type list in code style `ktlint_official` as it is inconsistent compared to other class bodies `indent` [#2115](https://github.com/pinterest/ktlint/issues/2115)
* In code style `ktlint_official` do not indent the closing parenthesis of a PARENTHESIZED expression `indent` [#920](https://github.com/pinterest/ktlint/issues/920) 
* Log message `Format was not able to resolve all violations which (theoretically) can be autocorrected in file ... in 3 consecutive runs of format` is now only displayed in case a new ktlint rule is actually needed. [#2129](https://github.com/pinterest/ktlint/issues/2129)
* Fix wrapping of function signature in case the opening brace of the function body block exceeds the maximum line length. Fix upsert of whitespace into composite nodes. `function-signature` [#2130](https://github.com/pinterest/ktlint/issues/2130)
* Fix spacing around colon in annotations `spacing-around-colon` ([#2093](https://github.com/pinterest/ktlint/issues/2093))
* Do not wrap a binary expression after an elvis operator in case the max line length is exceeded ([#2128](https://github.com/pinterest/ktlint/issues/2128))
* Fix indent of IS_EXPRESSION, PREFIX_EXPRESSION and POSTFIX_EXPRESSION in case it contains a linebreak `indent` [#2094](https://github.com/pinterest/ktlint/issues/2094)
* Add new experimental rule `function-literal`. This rule enforces the parameter list of a function literal to be formatted consistently. `function-literal` [#2121](https://github.com/pinterest/ktlint/issues/2121)
* Fix null pointer exception for if-else statement with empty THEN block `if-else-bracing` [#2135](https://github.com/pinterest/ktlint/issues/2135)
* Do not require SCREAMING_SNAKE_CASE for mutable collection properties declared as top-level or in objects. Such non-constant names should use lowerCamelCase. `property-naming` ([#???](https://github.com/pinterest/ktlint/issues/???))

### Changed

* Change default code style to `ktlint_official` ([#2143](https://github.com/pinterest/ktlint/pull/2143))
* Update dependency gradle to v8.2.1 ([#2122](https://github.com/pinterest/ktlint/pull/2122))
* Update dependency org.codehaus.janino:janino to v3.1.10  ([#2110](https://github.com/pinterest/ktlint/pull/2110))
* Update dependency com.google.jimfs:jimfs to v1.3.0 ([#2112](https://github.com/pinterest/ktlint/pull/2112))
* As a part of public API stabilization, configure `binary-compatibility-validator` plugin for compile-time verification of binary compatibility with previous `ktlint` versions ([#2131](https://github.com/pinterest/ktlint/pull/2131))

## [0.50.0] - 2023-06-29

### Deprecation of ktlint-enable and ktlint-disable directives

The `ktlint-disable` and `ktlint-enable` directives are no longer supported. Ktlint rules can now only be suppressed using the `@Suppress` or `@SuppressWarnings` annotations. A new rule, `internal:ktlint-suppression`, is provided to replace the directives with annotations.

API consumers do not need to provide this rule, but it does no harm when done.

The `internal:ktlint-suppression` rule can not be disabled via the `.editorconfig` nor via `@Suppress` or `@SuppressWarnings` annotations.

### Custom Rule Providers need to prepare for Kotlin 1.9

... (rest of file unchanged)