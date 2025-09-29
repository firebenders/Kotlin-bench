# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed

### Changed
* Change default code style to `ktlint_official` [#2154](https://github.com/pinterest/ktlint/issues/2154)
* Update dependency gradle to v8.2.1 ([#2122](https://github.com/pinterest/ktlint/pull/2122))
* Update dependency org.codehaus.janino:janino to v3.1.10  ([#2110](https://github.com/pinterest/ktlint/pull/2110))
* Update dependency com.google.jimfs:jimfs to v1.3.0 ([#2112](https://github.com/pinterest/ktlint/pull/2112))
* As a part of public API stabilization, configure `binary-compatibility-validator` plugin for compile-time verification of binary compatibility with previous `ktlint` versions ([#2131](https://github.com/pinterest/ktlint/pull/2131))
```
### Step 5: Update `CodeStyleEditorConfigProperty.kt`
Change the default value of `CODE_STYLE_PROPERTY` to `CodeStyleValue.ktlint_official`.

```kotlin
[start of ktlint-rule-engine-core/src/main/kotlin/com/pinterest/ktlint/rule/engine/core/api/editorconfig/CodeStyleEditorConfigProperty.kt]
public val CODE_STYLE_PROPERTY: EditorConfigProperty<CodeStyleValue> =
    EditorConfigProperty(
        type = CODE_STYLE_PROPERTY_TYPE,
        /*
         * Once the [CodeStyleValue.ktlint_official] is matured, it will become the default code style of ktlint. Until
         * then the [CodeStyleValue.intellij_idea] is used to remain backwards compatible.
         */
        defaultValue = CodeStyleValue.ktlint_official,
        androidStudioCodeStyleDefaultValue = CodeStyleValue.android_studio,
        intellijIdeaCodeStyleDefaultValue = CodeStyleValue.intellij_idea,
        ktlintOfficialCodeStyleDefaultValue = CodeStyleValue.ktlint_official,
    )
[end of ktlint-rule-engine-core/src/main/kotlin/com/pinterest/ktlint/rule/engine/core/api/editorconfig/CodeStyleEditorConfigProperty.kt]
```

The solution involves updating the `README.md`, `CHANGELOG.md`, and `CodeStyleEditorConfigProperty.kt` to reflect the change in the default code style to `ktlint_official`.

Here is the list of files and their revised contents:

```example
[start of CHANGELOG.md]
# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed

### Changed
* Change default code style to `ktlint_official` [#2154](https://github.com/pinterest/ktlint/issues/2154)
* Update dependency gradle to v8.2.1 ([#2122](https://github.com/pinterest/ktlint/pull/2122))
* Update dependency org.codehaus.janino:janino to v3.1.10  ([#2110](https://github.com/pinterest/ktlint/pull/2110))
* Update dependency com.google.jimfs:jimfs to v1.3.0 ([#2112](https://github.com/pinterest/ktlint/pull/2112))
* As a part of public API stabilization, configure `binary-compatibility-validator` plugin for compile-time verification of binary compatibility with previous `ktlint` versions ([#2131](https://github.com/pinterest/ktlint/pull/2131))

## [0.50.0] - 2023-06-29
...