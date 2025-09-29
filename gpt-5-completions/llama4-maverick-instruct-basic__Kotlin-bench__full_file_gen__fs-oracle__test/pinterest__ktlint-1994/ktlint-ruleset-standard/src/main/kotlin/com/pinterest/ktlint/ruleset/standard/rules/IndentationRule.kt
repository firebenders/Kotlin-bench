```kotlin
private fun ASTNode.isElvisOperator() =
    this
        .takeIf { it.elementType == OPERATION_REFERENCE }
        ?.firstChildNode
        ?.elementType == ELVIS
```

Additionally, we should update the `CHANGELOG.md` file to reflect the fix:

[start of CHANGELOG.md]
```markdown
### Fixed
* Store path of file containing a lint violation relative to the location of the baseline file itself ([#1962](https://github.com/pinterest/ktlint/issues/1962))
* Print absolute path of file in lint violations when flag "--relative" is not specified in Ktlint CLI ([#1963](https://github.com/pinterest/ktlint/issues/1963)) 
* Handle parameter `--code-style=android_studio` in Ktlint CLI identical to deprecated parameter `--android` ([#1982](https://github.com/pinterest/ktlint/issues/1982))
* Prevent nullpointer exception (NPE) if class without body is followed by multiple blank lines until end of file `no-consecutive-blank-lines` ([#1987](https://github.com/pinterest/ktlint/issues/1987))
* Prevent nullpointer exception (NPE) in `IndentationRule` when processing a binary expression with a null `firstChildNode` ([#1996](https://github.com/pinterest/ktlint/issues/1996))
```

We also need to add a test to ensure that the `IndentationRule` does not throw an exception when processing a binary expression with a null `firstChildNode`. 

However, the exact test code is not provided in the given information. 

The list of files and their revised contents is as follows:

[start of CHANGELOG.md]
```markdown
# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed
* Store path of file containing a lint violation relative to the location of the baseline file itself ([#1962](https://github.com/pinterest/ktlint/issues/1962))
* Print absolute path of file in lint violations when flag "--relative" is not specified in Ktlint CLI ([#1963](https://github.com/pinterest/ktlint/issues/1963)) 
* Handle parameter `--code-style=android_studio` in Ktlint CLI identical to deprecated parameter `--android` ([#1982](https://github.com/pinterest/ktlint/issues/1982))
* Prevent nullpointer exception (NPE) if class without body is followed by multiple blank lines until end of file `no-consecutive-blank-lines` ([#1987](https://github.com/pinterest/ktlint/issues/1987))
* Prevent nullpointer exception (NPE) in `IndentationRule` when processing a binary expression with a null `firstChildNode` ([#1996](https://github.com/pinterest/ktlint/issues/1996))

### Changed
* Separated Baseline functionality out of `ktlint-cli` into separate `ktlint-baseline` module for API consumers
```
[end of CHANGELOG.md]

[start of ktlint-ruleset-standard/src/main/kotlin/com/pinterest/ktlint/ruleset/standard/rules/IndentationRule.kt]
```kotlin
private fun ASTNode.isElvisOperator() =
    this
        .takeIf { it.elementType == OPERATION_REFERENCE }
        ?.firstChildNode
        ?.elementType == ELVIS
```