# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed

* Do not flag a (potential) mutable extension property in case the getter is annotated or prefixed with a modifier `property-naming` ([#2024](https://github.com/pinterest/ktlint/issues/2024))
* Do not merge the first line of an expression body with the function signature when the expression starts with an annotation (e.g. @Suppress). This prevents violating the annotation rule when formatting `function-signature` ([#2028](https://github.com/pinterest/ktlint/issues/2028))

### Changed

* Fix Java interoperability issues with `RuleId` and `RuleSetId` classes. Those classes were defined as value classes in `0.49.0` and `0.49.1`. Although the classes were marked with `@JvmInline` it seems that it is not possible to uses those classes from Java base API Consumers like Spotless. The classes have now been replaced with data classes ([#2041](https://github.com/pinterest/ktlint/issues/2041))
* Update dependency `info.picocli:picocli` to v4.7.3
* Update dependency `org.junit.jupiter:junit-jupiter` to v5.9.3
* Update Kotlin development version to `1.8.21` and Kotlin version to `1.8.21`.
* Update dependency io.github.detekt.sarif4k:sarif4k to v0.4.0

## [0.49.1] - 2023-05-12

### Added

### Removed

### Fixed
* Store path of file containing a lint violation relative to the location of the baseline file itself ([#1962](https://github.com/pinterest/ktlint/issues/1962))
* Print absolute path of file in lint violations when flag "--relative" is not specified in Ktlint CLI ([#1963](https://github.com/pinterest/ktlint/issues/1963)) 
* Handle parameter `--code-style=android_studio` in Ktlint CLI identical to deprecated parameter `--android` ([#1982](https://github.com/pinterest/ktlint/issues/1982))
* Prevent nullpointer exception (NPE) if class without body is followed by multiple blank lines until end of file `no-consecutive-blank-lines` ([#1987](https://github.com/pinterest/ktlint/issues/1987))
* Allow to 'unset' the `.editorconfig` property `ktlint_function_signature_rule_force_multiline_when_parameter_count_greater_or_equal_than` when using `ktlint_official` code style `function-signature` ([#1977](https://github.com/pinterest/ktlint/issues/1977))
* Prevent nullpointer exception (NPE) if or operator at start of line is followed by dot qualified expression `indent` ([#1993](https://github.com/pinterest/ktlint/issues/1993))
* Fix indentation of multiline parameter list in function literal `indent` ([#1976](https://github.com/pinterest/ktlint/issues/1976))
* Restrict indentation of closing quotes to `ktlint_official` code style to keep formatting of other code styles consistent with `0.48.x` and before `indent` ([#1971](https://github.com/pinterest/ktlint/issues/1971))
* Extract rule `no-single-line-block-comment` from `comment-wrapping` rule. The `no-single-line-block-comment` rule is added as experimental rule to the `ktlint_official` code style, but it can be enabled explicitly for the other code styles as well. ([#1980](https://github.com/pinterest/ktlint/issues/1980))
* Clean-up unwanted logging dependencies ([#1998](https://github.com/pinterest/ktlint/issues/1998))
* Fix directory traversal for patterns referring to paths outside of current working directory or any of it child directories ([#2002](https://github.com/pinterest/ktlint/issues/2002))

### Changed

* Moved class `Baseline` from `ktlint-cli` to `ktlint-cli-reporter-baseline` so that Baseline functionality is reusable for API Consumers.

## [0.49.0] - 2023-04-21

WARNING: This version of KtLint contains a number of breaking changes in KtLint CLI and KtLint API. If you are using KtLint with custom ruleset jars or custom reporter jars, then those need to be upgraded before you can use them with this version of ktlint. Please contact the maintainers of those jars and ask them to upgrade a.s.a.p.

All rule id's in the output of Ktlint are now prefixed with a rule set. Although KtLint currently supports standard rules to be unqualified, users are encouraged to include the rule set id in all references to rules. This includes following:
* The `--disabled-rules` parameter in KtLint CLI.
* The `.editorconfig` properties used to enable or disable rule and rule sets. Note that properties `disabled_rules` and `ktlint_disabled_rules` have been removed in this release. See [disabled rules](https://pinterest.github.io/ktlint/rules/configuration-ktlint/#disabled-rules) for more information.
* The `source` element in the KtLint CLI `baseline.xml` file. Regenerating this file, fixes all rule references automatically.
* The KtLint disable directives `ktlint-enable` / `ktlint-disable` and the `@Suppress('ktlint:...')` annotations.
* The `VisitorModifier.RunAfterRule`.

### Moving experimental rules to standard rule set

The `experimental` rule set has been merged with `standard` rule set. The rules which formerly were part of the `experimental` rule set are still being treated as before. The rules will only be run in case `.editorconfig` property `ktlint_experimental` is enabled or in case the rule is explicitly enabled.

Note that the prefix `experimental:` has to be removed from all references to this rule. Check references in:
* The `--disabled-rules` parameter in KtLint CLI.
* The `.editorconfig` properties used to enable or disable rule and rule sets. Note that properties `disabled_rules` and `ktlint_disabled_rules` have been removed in this release. See [disabled rules](https://pinterest.github.io/ktlint/rules/configuration-ktlint/#disabled-rules) for more information.
* The KtLint disable directives `ktlint-enable` / `ktlint-disable` and the `@Suppress('ktlint:...')` annotations.
* The `VisitorModifier.RunAfterRule`.

### Promote experimental rules to non-experimental

The rules below have been promoted to non-experimental rules:
* [block-comment-initial-star-alignment](https://pinterest.github.io/ktlint/rules/standard/#block-comment-initial-star-alignment)
* [class-naming](https://pinterest.github.io/ktlint/rules/standard/#classobject-naming)
* [comment-wrapping](https://pinterest.github.io/ktlint/rules/standard/#comment-wrapping)
* [function-return-type-spacing](https://pinterest.github.io/ktlint/rules/standard/#function-return-type-spacing)
* [function-start-of-body-spacing](https://pinterest.github.io/ktlint/rules/standard/#function-start-of-body-spacing)
* [function-type-reference-spacing](https://pinterest.github.io/ktlint/rules/standard/#function-type-reference-spacing)
* [fun-keyword-spacing](https://pinterest.github.io/ktlint/rules/standard/#fun-keyword-spacing)
* [kdoc-wrapping](https://pinterest.github.io/ktlint/rules/standard/#kdoc-wrapping)
* [modifier-list-spacing](https://pinterest.github.io/ktlint/rules/standard/#modifier-list-spacing)
* [nullable-type-spacing](https://pinterest.github.io/ktlint/rules/standard/#nullable-type-spacing)
* [spacing-between-function-name-and-opening-parenthesis](https://pinterest.github.io/ktlint/rules/standard/#spacing-between-function-name-and-opening-parenthesis)
* [unnecessary-parentheses-before-trailing-lambda](https://pinterest.github.io/ktlint/rules/standard/#unnecessary-parenthesis-before-trailing-lambda)

Note that this only affects users that have enabled the standard ruleset while having the experimental rules disabled.

### API Changes & RuleSet providers & Reporter Providers

This release is intended to be the last release before the 1.0.x release of ktlint. If all goes as planned, the 1.0.x release does not contain any new breaking changes with except of removal of functionality which is deprecated in this release.

This release contains a lot of breaking changes which aims to improve the future maintainability of Ktlint. If you get stuck while migrating, please reach out to us by creating an issue.

#### Experimental rules

Rules in custom rule sets can now be marked as experimental by implementing the `Rule.Experimental` interface on the rule. Rules marked with this interface will only be executed by Ktlint if `.editorconfig` property `ktlint_experimental` is enabled or if the rule itself has been enabled explicitly.

When using this feature, experimental rules should *not* be defined in a separate rule set as that would require a distinct rule set id. When moving a rule from an experimental rule set to a non-experimental rule set this would mean that the qualified rule id changes. For users of such rules this means that ktlint directives to suppress the rule and properties in the `.editorconfig` files have to be changed.

#### EditorConfig

Field `defaultAndroidValue` in class `EditorConfigProperty` has been renamed to `androidStudioCodeStyleDefaultValue`. New fields `ktlintOfficialCodeStyleDefaultValue` and `intellijIdeaCodeStyleDefaultValue` have been added. Read more about this in the section "Ktlint Official code style".

The `.editorconfig` properties `disabled_rules` and `ktlint_disabled_rules` are no longer supported. Specifying those properties in the `editorConfigOverride` or `editorConfigDefaults` result in warnings at runtime.

#### 'Ktlint Official` code style and renaming of existing code styles

A new code style `ktlint_official` is introduced. This code style is work in progress but will become the default code style in the `1.0` release. Please try out the new code style and provide your feedback via the [issue tracker](https://github.com/pinterest/ktlint/issues).

This `ktlint_official` code style combines the best elements from the [Kotlin Coding conventions](https://kotlinlang.org/docs/coding-conventions.html) and [Android's Kotlin styleguide](https://developer.android.com/kotlin/style-guide). This code style also provides additional formatting on topics which are not (explicitly) mentioned in those conventions and style guide. But do note that this code style sometimes formats code in a way which is not accepted by the default code formatters in IntelliJ IDEA and Android Studio. The formatters of those editors produce nicely formatted code in the vast majority of cases. But in a number of edge cases, the formatting contains bugs which are waiting to be fixed for several years. The new code style formats code in a way which is compatible with the default formatting of the editors whenever possible. When using this codestyle, it is best to disable (e.g. not use) code formatting in the editor.

The existing code styles have been renamed to make more clear what the basis of the code style is.

The `official` code style has been renamed to `intellij_idea`. Code formatted with this code style aims to be compatible with default formatter of IntelliJ IDEA. This code style is based on [Kotlin Coding conventions](https://kotlinlang.org/docs/coding-conventions.html). If `.editorconfig` property `ktlint_code_style` has been set to `android` then do not forget to change the value of that property to `intellij_idea`. When not set, this is still the default code style of ktlint `0.49`. Note that the default code style will be changed to `ktlint_official` in the `1.0` release.

Code style `android` has been renamed to `android_studio`. Code formatted with this code style aims to be compatible with default formatter of Android Studio. This code style is based on [Android's Kotlin styleguide](https://developer.android.com/kotlin/style-guide). If `.editorconfig` property `ktlint_code_style` has been set to `android` then do not forget to change the value of that property to `android_studio`.

#### Package restructuring and class relocation

The internal structure of the Ktlint project has been revised. The Ktlint CLI and KtLint API modules have been decoupled where possible. Modules have been restructured and renamed. See [API Overview](https://pinterest.github.io/ktlint/api/overview/) for more information.

This is the last release that contains module `ktlint-core` as it had too many responsibilities. All classes in this module are relocated to other modules. Some classes have also been renamed. See tables below for details. Classes that are left behind in the `ktlint-core` module are deprecated and were kept in this version for backwards compatibility only. The `ktlint-core` module will be removed in Ktlint `0.50.x`.

Classes below have been moved from module `ktlint-core` to the new module `ktlint-rule-engine-core`:

| Old class/package name in `ktlint-core`                  | New class/package name in `ktlint-rule-engine-core`                               |
|----------------------------------------------------------|-----------------------------------------------------------------------------------|
| com.pinterest.ktlint.core.api.editorconfig               | com.pinterest.ktlint.rule.engine.core.api.editorconfig                            |
| com.pinterest.ktlint.core.api.EditorConfigProperties     | com.pinterest.ktlint.rule.engine.core.api.EditorConfig                            |
| com.pinterest.ktlint.core.api.OptInFeatures              | com.pinterest.ktlint.rule.engine.core.api.OptInFeatures                           |
| com.pinterest.ktlint.core.ast.ElementType                | com.pinterest.ktlint.rule.engine.core.api.ElementType                             |
| com.pinterest.ktlint.core.ast.package                    | com.pinterest.ktlint.rule.engine.core.api.ASTNodeExtension                        |
| com.pinterest.ktlint.core.IndentConfig                   | com.pinterest.ktlint.rule.engine.core.api.IndentConfig                            |
| com.pinterest.ktlint.core.Rule                           | com.pinterest.ktlint.rule.engine.core.api.Rule                                    |
| com.pinterest.ktlint.core.RuleProvider                   | com.pinterest.ktlint.rule.engine.core.api.RuleProvider                            |

Classes below have been moved from module `ktlint-core` to the new module `ktlint-rule-engine`:

| Old class/package name in `ktlint-core`                  | New class/package name in `ktlint-rule-engine`                               |
|----------------------------------------------------------|------------------------------------------------------------------------------|
| com.pinterest.ktlint.core.api.EditorConfigDefaults       | com.pinterest.ktlint.rule.engine.api.EditorConfigDefaults                    |
| com.pinterest.ktlint.core.api.EditorConfigOverride       | com.pinterest.ktlint.rule.engine.api.EditorConfigOverride                    |
| com.pinterest.ktlint.core.api.KtLintParseException       | com.pinterest.ktlint.rule.engine.api.KtLintParseException                    |
| com.pinterest.ktlint.core.api.KtLintRuleException        | com.pinterest.ktlint.rule.engine.api.KtLintRuleException                     |
| com.pinterest.ktlint.core.KtLint                         | com.pinterest.ktlint.rule.engine.api.KtLintRuleEngine                        |
| com.pinterest.ktlint.core.LintError                      | com.pinterest.ktlint.rule.engine.api.LintError                               |

Class `com.pinterest.ktlint.core.KtLint.Code.CodeFile` has been replaced with factory method `com.pinterest.ktlint.rule.engine.api.Code.fromFile`. Likewise, class `com.pinterest.ktlint.core.KtLint.Code.CodeSnippet` has been replaced with factory method `com.pinterest.ktlint.rule.engine.api.Code.fromSnippet`.

Class below has been moved from module `ktlint-core` to the new module `ktlint-cli-ruleset-core`:

| Old class/package name in `ktlint-core`                  | New class/package name in `ktlint-cli-ruleset-core`                           |
|----------------------------------------------------------|-------------------------------------------------------------------------------|
| com.pinterest.ktlint.core.RuleSetProviderV2              | com.pinterest.ktlint.cli.ruleset.core.api.RuleSetProviderV3                   |


Class below has been moved from module `ktlint-core` to the new module `ktlint-cli-reporter-core`:

| Old class/package name in `ktlint-core`   | New class/package name in `ktlint-cli-reporter-core`     |
|-------------------------------------------|----------------------------------------------------------|
| com.pinterest.ktlint.core.KtlintVersion   | com.pinterest.ktlint.cli.reporter.core.api.KtlintVersion |

Class below has been moved from module `ktlint-core` to the new module `ktlint-logger`:

| Old class/package name in `ktlint-core`               | New class/package name in `ktlint-logger`                   |
|-------------------------------------------------------|-------------------------------------------------------------|
| com.pinterest.ktlint.core.KtLintKLoggerInitializer.kt | com.pinterest.ktlint.logger.api.KtLintKLoggerInitializer.kt |

Class below has been relocated from module `ktlint-core` to module `ktlint-cli`:

| Old class/package name in `ktlint-core` | New class/package name in `ktlint-cli` |
|-----------------------------------------|----------------------------------------|
| com.pinterest.ktlint.core.api.Baseline  | com.pinterest.ktlint.cli.api.Baseline  |

Module `ktlint-reporter-baseline` has been renamed to `ktlint-cli-reporter-baseline`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-baseline` | New class/package name in `ktlint-cli-reporter-baseline` |
|------------------------------------------------------|----------------------------------------------------------|
| com.pinterest.ktlint.reporter.baseline               | com.pinterest.ktlint.cli.reporter.baseline               |

Module `ktlint-reporter-checkstyle` has been renamed to `ktlint-cli-reporter-checkstyle`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-checkstyle` | New class/package name in `ktlint-cli-reporter-checkstyle` |
|--------------------------------------------------------|------------------------------------------------------------|
| com.pinterest.ktlint.reporter.checkstyle               | com.pinterest.ktlint.cli.reporter.checkstyle               |

Module `ktlint-reporter-format` has been renamed to `ktlint-cli-reporter-format`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-format` | New class/package name in `ktlint-cli-reporter-format` |
|----------------------------------------------------|--------------------------------------------------------|
| com.pinterest.ktlint.reporter.format               | com.pinterest.ktlint.cli.reporter.format               |

Module `ktlint-reporter-html` has been renamed to `ktlint-cli-reporter-html`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-html` | New class/package name in `ktlint-cli-reporter-html` |
|--------------------------------------------------|------------------------------------------------------|
| com.pinterest.ktlint.reporter.html               | com.pinterest.ktlint.cli.reporter.html               |

Module `ktlint-reporter-json` has been renamed to `ktlint-cli-reporter-json`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-json` | New class/package name in `ktlint-cli-reporter-json` |
|--------------------------------------------------|------------------------------------------------------|
| com.pinterest.ktlint.reporter.json               | com.pinterest.ktlint.cli.reporter.json               |

Module `ktlint-reporter-plain` has been renamed to `ktlint-cli-reporter-plain`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-plain` | New class/package name in `ktlint-cli-reporter-plain` |
|---------------------------------------------------|-------------------------------------------------------|
| com.pinterest.ktlint.reporter.plain               | com.pinterest.ktlint.cli.reporter.plain               |

Module `ktlint-reporter-plain-summary` has been renamed to `ktlint-cli-reporter-plain-summary`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-plain-summary` | New class/package name in `ktlint-cli-reporter-plain-summary` |
|-----------------------------------------------------------|---------------------------------------------------------------|
| com.pinterest.ktlint.reporter.plain                       | com.pinterest.ktlint.cli.reporter.plainsummary                |

Module `ktlint-reporter-sarif` has been renamed to `ktlint-cli-reporter-sarif`. Class below has been relocated:

| Old class/package name in `ktlint-reporter-sarif` | New class/package name in `ktlint-cli-reporter-sarif` |
|---------------------------------------------------|-------------------------------------------------------|
| com.pinterest.ktlint.reporter.sarif               | com.pinterest.ktlint.cli.reporter.sarif               |

#### Custom Ruleset Provider `RuleSetProviderV2`

Custom rule sets build for older versions of KtLint are no longer supported by this version of KtLint. The `com.pinterest.ktlint.core.RuleSetProviderV2` interface has been replaced with `RuleSetProviderV3`. The accompanying interfaces `com.pinterest.ktlint.core.RuleProvider` and `com.pinterest.ktlint.core.Rule` have been replaced with `com.pinterest.ktlint.ruleset.core.api.RuleProvider` and `com.pinterest.ktlint.ruleset.core.api.Rule` respectively.

Contrary to `RuleSetProviderV2`, the `RuleSetProviderV3` no longer contains information about the rule set. About information now has to be specified in the new `Rule` class. This allows custom rule set providers to combine rules originating from different rule sets into a new rule set without loosing information about its origin. The type of the id of the rule set is changed from `String` to `RuleSetId`. 

Note that due to renaming and relocation of the `RuleSetProviderV3` interface the name of the service provider in the custom reporter needs to be changed from `resources/META-INF/services/com.pinterest.ktlint.core.RuleSetProviderV2` to `resources/META-INF/services/com.pinterest.ktlint.cli.ruleset.core.api.RuleSetProviderV3`.

The rule id's in `com.pinterest.ktlint.ruleset.core.api.Rule` have been changed from type `String` to `RuleId`. A `RuleId` has a value that must adhere the convention "`rule-set-id`:`rule-id`". The rule set id `standard` is reserved for rules which are maintained by the KtLint project. Rules created by custom rule set providers and API Consumers should use a prefix other than `standard` to mark the origin of rules which are not maintained by the KtLint project.

When wrapping a rule from the ktlint project and modifying its behavior, please change the `ruleId` and `about` fields in the wrapped rule, so that it is clear to users whenever they use the original rule provided by KtLint versus a modified version which is not maintained by the KtLint project.

The typealias `com.pinterest.ktlint.core.api.EditorConfigProperties` has been replaced with `com.pinterest.ktlint.rule.engine.core.api.EditorConfig`. The interface `com.pinterest.ktlint.core.api.UsesEditorConfigProperties` has been removed. Instead, the Rule property `usesEditorConfigProperties` needs to be set. As a result of those changes, the `beforeFirstNode` function in each rule has to changed to something like below: 

```kotlin
public class SomeRule : Rule(
  ruleId = RuleId("some-rule-set:some-rule"),
  usesEditorConfigProperties = setOf(MY_EDITOR_CONFIG_PROPERTY),
) {
  private lateinit var myEditorConfigProperty: MyEditorConfigProperty

  override fun beforeFirstNode(editorConfig: EditorConfig) {
    myEditorConfigProperty = editorConfig[MY_EDITOR_CONFIG_PROPERTY]
  }
  
  ...
}
```

Fields `loadOnlyWhenOtherRuleIsLoaded` and `runOnlyWhenOtherRuleIsEnabled` have been removed from class `com.pinterest.ktlint.rule.engine.core.api.Rule.VisitorModifier.RunAfterRule` and are replaced with a single field `mode`. The `mode` either contains value `REGARDLESS_WHETHER_RUN_AFTER_RULE_IS_LOADED_OR_DISABLED` or `ONLY_WHEN_RUN_AFTER_RULE_IS_LOADED_AND_ENABLED`.

#### Custom Reporter Provider `ReporterProvider`

Custom Reporters build for older versions of KtLint are no longer supported by this version of KtLint. The `com.pinterest.ktlint.core.ReporterProvider` interface has been replaced with `com.pinterest.ktlint.cli.reporter.core.api.ReporterProviderV2`. The accompanying interface `com.pinterest.ktlint.core.Reporter` has been replaced with `com.pinterest.ktlint.cli.reporter.core.api.ReporterV2`.

Note that due to renaming and relocation of the `ReporterProviderV2` interface the name of the service provider in the custom reporter needs to be changed from `resources/META-INF/services/com.pinterest.ktlint.core.ReporterProvider` to `resources/META-INF/services/com.pinterest.ktlint.cli.reporter.core.api.ReporterProviderV2`.

The biggest change in the `ReporterV2` is the replacement of the `LintError` class with `KtlintCliError` class. The latter class now contains a status field which more clearly explains the difference between a lint error which can be autocorrected versus a lint error that actually has been autocorrected.

#### Custom rules provided by API Consumer

API Consumers provide a set of rules directly to the Ktlint Rule Engine. The `com.pinterest.ktlint.core.Rule` has been replaced with `com.pinterest.ktlint.ruleset.core.api.Rule`.

The type of the rule id's has been changed from type `String` to `RuleId`. A `RuleId` has a value that must adhere to the convention "`rule-set-id`:`rule-id`". Rule set id `standard` is reserved for rules which are maintained by the KtLint project. Custom rules created by the API Consumer should use a prefix other than `standard` to clearly mark the origin of rules which are not maintained by the KtLint project.

Also, the field `About` has been added. This field specifies the name of the maintainer, and the repository url and issue tracker url of the rule. The about information of a rule is printed whenever a rule throws an exception which is caught by the Ktlint Rule Engine.

When wrapping a rule from the ktlint project and modifying its behavior, please change the `ruleId` and `about` fields in the wrapped rule, so that it is clear to users whenever they use the original rule provided by KtLint versus a modified version which is not maintained by the KtLint project.

The typealias `com.pinterest.ktlint.core.api.EditorConfigProperties` has been replaced with `com.pinterest.ktlint.rule.engine.core.api.EditorConfig`. The interface `com.pinterest.ktlint.core.api.UsesEditorConfigProperties` has been removed. Instead, the Rule property `usesEditorConfigProperties` needs to be set. As a result of those changes, the `beforeFirstNode` function in each rule has to changed to something like below:

```kotlin
public class SomeRule : Rule(
  ruleId = RuleId("some-rule-set:some-rule"),
  usesEditorConfigProperties = setOf(MY_EDITOR_CONFIG_PROPERTY),
) {
  private lateinit var myEditorConfigProperty: MyEditorConfigProperty

  override fun beforeFirstNode(editorConfig: EditorConfig) {
    myEditorConfigProperty = editorConfig[MY_EDITOR_CONFIG_PROPERTY]
  }
  
  ...
}
```

Fields `loadOnlyWhenOtherRuleIsLoaded` and `runOnlyWhenOtherRuleIsEnabled` have been removed from class `com.pinterest.ktlint.rule.engine.core.api.Rule.VisitorModifier.RunAfterRule` and are replaced with a single field `mode`. The `mode` either contains value `REGARDLESS_WHETHER_RUN_AFTER_RULE_IS_LOADED_OR_DISABLED` or `ONLY_WHEN_RUN_AFTER_RULE_IS_LOADED_AND_ENABLED`.

Like before, the API Consumer can still offer a mix of rules originating from `ktlint-ruleset-standard` as well as custom rules.

#### `.editorconfig` property `max_line_length` default value

Previously, the default value for `.editorconfig` property `max_line_length` was set to `-1` in ktlint unless the property was defined explicitly in the `.editorconfig` or when `ktlint_code_style` was set to Android. As a result of that rules have to check that max_line_length contains a positive value before checking that the actual line length is exceeding the maximum. Now the value `Int.MAX_VALUE` (use constant `MAX_LINE_LENGTH_PROPERTY_OFF` to refer to that value) is used instead. 

#### Psi filename replaces FILE_PATH_USER_DATA_KEY

Constant `KtLint.FILE_PATH_USER_DATA_KEY` has been removed. The file path is passed correctly to the node with element type FILE and can be retrieved as follows:
```kotlin
if (node.isRoot()) {
  val filePath = (node.psi as? KtFile)?.virtualFilePath
    ...
}
```

### Added

* Add new code style `ktlint_offical`. The code style is work in progress and should be considered a preview. It is intended to become the default code style in the next release. Please try it out and give your feedback. See [code styles](https://pinterest.github.io/ktlint/rules/code-styles/) for more information. The following rules have been added to the `ktlint_official` code style (the rules can also be run for other code styles when enabled explicitly):
  * Add new experimental rule `no-empty-first-line-in-class-body`. This rule disallows a class to start with a blank line.
  * Add new experimental rule `if-else-bracing`. This rules enforces consistent usage of braces in all branches of a single if, if-else or if-else-if statement.
  * Add new experimental rule `no-consecutive-comments`. This rule disallows consecutive comments except EOL comments (see [examples](See https://pinterest.github.io/ktlint/rules/experimental/#disallow-consecutive-comments)).
  * Add new experimental rule `try-catch-finally-spacing`. This rule enforces consistent spacing in try-catch, try-finally and try-catch-finally statement. This rule can also be run for other code styles, but then it needs to be enabled explicitly.
  * Add new experimental rule `no-blank-line-in-list`. This rule disallows blank lines to be used in super type lists, type argument lists, type constraint lists, type parameter lists, value argument lists, and value parameter lists. ([#1224](https://github.com/pinterest/ktlint/issues/1224))
  * Add new experimental rule `multiline-expression-wrapping`. This forces a multiline expression as value in an assignment to start on a separate line. ([#1217](https://github.com/pinterest/ktlint/issues/1217))
  * Add new experimental rule `string-template-indent`. This forces multiline string templates which are post-fixed with `.trimIndent()` to be formatted consistently. The opening and closing `"""` are placed on separate lines and the indentation of the content of the template is aligned with the `"""`. ([#925](https://github.com/pinterest/ktlint/issues/925))
  * Add new experimental rule `if-else-wrapping`. This enforces that a single line if-statement is kept simple. A single line if-statement may contain no more than one else-branch. The branches a single line if-statement may not be wrapped in a block. ([#812](https://github.com/pinterest/ktlint/issues/812))
* Wrap the type or value of a function or class parameter in case the maximum line length is exceeded `parameter-wrapping` ([#1846](https://github.com/pinterest/ktlint/pull/1846))
* Wrap the type or value of a property in case the maximum line length is exceeded `property-wrapping` ([#1846](https://github.com/pinterest/ktlint/pull/1846))
* Recognize Kotlin Script when linting and formatting code from `stdin` with KtLint CLI ([#1832](https://github.com/pinterest/ktlint/issues/1832))
* Support Bill of Materials (BOM), now you can integrate Ktlint in your `build.gradle` like:
  ```kotlin
  dependencies {
      implementation(platform("com.pinterest:ktlint-bom:0.49.0"))
      implementation("com.pinterest:ktlint-core")
      implementation("com.pinterest:ktlint-reporter-html")
      implementation("com.pinterest:ktlint-ruleset-standard")
      ...
  }
  ```
* Add new experimental rule `enum-wrapping` for all code styles. An enum should either be a single line, or each enum entry should be defined on a separate line. ([#1903](https://github.com/pinterest/ktlint/issues/1903))

### Removed

* Remove support of the `.editorconfig` properties `disabled_rules` and `ktlint_disabled_rules`. See [disabled rules](https://pinterest.github.io/ktlint/rules/configuration-ktlint/#disabled-rules) for more information.
* Remove CLI option `--print-ast`. Use IntelliJ IDEA PsiViewer plugin instead. ([#1925](https://github.com/pinterest/ktlint/issues/1925))

### Fixed

* An enumeration class having a primary constructor and in which the list of enum entries is followed by a semicolon then do not remove the semicolon in case it is followed by code element `no-semi` ([#1733](https://github.com/pinterest/ktlint/issues/1733))
* Do not add the (first line of) the body expression on the same line as the function signature in case the max line length would be exceeded. `function-signature`. 
* Do not add the first line of a multiline body expression on the same line as the function signature in case function body expression wrapping property is set to `multiline`. `function-signature`. 
* Disable the `standard:filename` rule whenever Ktlint CLI is run with option `--stdin` ([#1742](https://github.com/pinterest/ktlint/issues/1742))
* The parameters of a function literal containing a multiline parameter list are aligned with first parameter whenever the first parameter is on the same line as the start of that function literal (not allowed in `ktlint_official` code style) `indent` ([#1756](https://github.com/pinterest/ktlint/issues/1756))
* Do not throw exception when enum class does not contain entries `trailing-comma-on-declaration-site` ([#1711](https://github.com/pinterest/ktlint/issues/1711))
* Fix continuation indent for a dot qualified array access expression in `ktlint_official` code style only `indent` ([#1540](https://github.com/pinterest/ktlint/issues/1540))
* When generating the `.editorconfig` use value `off` for the `max_line_length` property instead of value `-1` to denote that lines are not restricted to a maximum length ([#1824](https://github.com/pinterest/ktlint/issues/1824))
* Do not report an "unnecessary semicolon" after adding a trailing comma to an enum class containing a code element after the last enum entry `trailing-comma-on-declaration-site` ([#1786](https://github.com/pinterest/ktlint/issues/1786))
* A newline before a function return type should not be removed in case that leads to exceeding the maximum line length `function-return-type-spacing` ([#1764](https://github.com/pinterest/ktlint/issues/1764))
* Wrap annotations on type arguments in same way as with other constructs `annotation`, `wrapping` ([#1725](https://github.com/pinterest/ktlint/issues/1725))
* Fix indentation of try-catch-finally when catch or finally starts on a newline `indent` ([#1788](https://github.com/pinterest/ktlint/issues/1788))
* Fix indentation of a multiline typealias `indent` ([#1788](https://github.com/pinterest/ktlint/issues/1788))
* Fix false positive when multiple KDOCs exists between a declaration and another annotated declaration `spacing-between-declarations-with-annotations` ([#1802](https://github.com/pinterest/ktlint/issues/1802))
* Fix false positive when a single line statement containing a block having exactly the maximum line length is preceded by a blank line `wrapping` ([#1808](https://github.com/pinterest/ktlint/issues/1808))
* Fix false positive when a single line contains multiple dot qualified expressions and/or safe expressions `indent` ([#1830](https://github.com/pinterest/ktlint/issues/1830))
* Enforce spacing around rangeUntil operator `..<` similar to the range operator `..` in `range-spacing`  ([#1858](https://github.com/pinterest/ktlint/issues/1858))
* When `.editorconfig` property `ij_kotlin_imports_layout` contains a `|` but no import exists that match any pattern before the first `|` then do not report a violation nor insert a blank line `import-ordering` ([#1845](https://github.com/pinterest/ktlint/issues/1845))
* When negate-patterns only are specified in Ktlint CLI then automatically add the default include patterns (`**/*.kt` and `**/*.kts`) so that all Kotlin files excluding the files matching the negate-patterns will be processed ([#1847](https://github.com/pinterest/ktlint/issues/1847))
* Do not remove newlines from multiline type parameter lists `type-parameter-list-spacing` ([#1867](https://github.com/pinterest/ktlint/issues/1867))
* Wrap each type parameter in a multiline type parameter list `wrapping` ([#1867](https://github.com/pinterest/ktlint/issues/1867))
* Allow value arguments with a multiline expression to be indented on a separate line `indent` ([#1217](https://github.com/pinterest/ktlint/issues/1217))
* When enabled, the ktlint rule checking is disabled for all code surrounded by the formatter tags (see [faq](https://pinterest.github.io/ktlint/faq/#are-formatter-tags-respected)) ([#670](https://github.com/pinterest/ktlint/issues/670)) 
* Remove trailing comma if last two enum entries are on the same line and trailing commas are not allowed. `trailing-comma-on-declaration-site` ([#1905](https://github.com/pinterest/ktlint/issues/1905))
* Wrap annotated function parameters to a separate line in code style `ktlint_official` only. `function-signature`, `parameter-list-wrapping` ([#1908](https://github.com/pinterest/ktlint/issues/1908))
* Wrap annotated projection types in type argument lists to a separate line `annotation` ([#1909](https://github.com/pinterest/ktlint/issues/1909))
* Add newline after adding trailing comma in parameter list of a function literal `trailing-comma-on-declaration-site` ([#1911](https://github.com/pinterest/ktlint/issues/1911))
* Wrap annotations before class constructor in code style `ktlint_official`. `annotation` ([#1916](https://github.com/pinterest/ktlint/issues/1916))
* Annotations on type projections should be wrapped in same way as other annotations `annotation` ([#1917](https://github.com/pinterest/ktlint/issues/1917))
* An if-else followed by an elvis operator should not be wrapped in an else-block `multiline-if-else` ([#1904](https://github.com/pinterest/ktlint/issues/1904))

### Changed
* Wrap the parameters of a function literal containing a multiline parameter list (only in `ktlint_official` code style) `parameter-list-wrapping` ([#1681](https://github.com/pinterest/ktlint/issues/1681)).
* KtLint CLI exits with an error in any of following cases (this list is not exhaustive):
  - A custom ruleset jar is to be loaded and that jar contains a deprecated RuleSetProviderV2.
  - A custom ruleset jar is to be loaded and that jar does not contain the required RuleSetProviderV3.
  - A custom reporter jar is to be loaded and that jar contains a deprecated ReporterProvider.
  - A custom reporter jar is to be loaded and that jar does not contain the required ReporterProviderV2.
* Disable the default patterns if the option `--patterns-from-stdin` is specified ([#1793](https://github.com/pinterest/ktlint/issues/1793))
* Update Kotlin development version to `1.8.20` and Kotlin version to `1.8.20`.
* Revert to matrix build to speed up build, especially for the Windows related build ([#1787](https://github.com/pinterest/ktlint/pull/1787))
* For the new code style `ktlint_official`, do not allow wildcard imports `java.util` and `kotlinx.android.synthetic` by default. Important: `.editorconfig` property `ij_kotlin_packages_to_use_import_on_demand` needs to be set to value `unset` in order to enforce IntelliJ IDEA default formatter to not generate wildcard imports `no-wildcard-imports` ([#1797](https://github.com/pinterest/ktlint/issues/1797))
* Convert a single line block comment to an EOL comment if not preceded or followed by another code element on the same line `comment-wrapping` ([#1941](https://github.com/pinterest/ktlint/issues/1941))
* Ignore a block comment inside a single line block `comment-wrapping` ([#1942](https://github.com/pinterest/ktlint/issues/1942))

## [0.48.2] - 2023-01-21

### Additional clarification on API Changes in `0.48.0` and `0.48.1`

Starting with Ktlint `0.48.x`, rule and rule sets can be enabled/disabled with a separate property per rule (set). Please read [deprecation of (ktlint_)disable_rules property](https://pinterest.github.io/ktlint/faq/#why-is-editorconfig-property-disabled_rules-deprecated-and-how-do-i-resolve-this) for more information.

API Consumers that provide experimental rules to the KtLintRuleEngine, must also enable the experimental rules or instruct their users to do so in the `.editorconfig` file. From the perspective of the API Consumer it might be confusing or unnecessary to do so as the experimental rule was already provided explicitly.

Ktlint wants to provide the user (e.g. a developer) a uniform and consistent user experience. The `.editorconfig` becomes more and more central to store configuration for KtLint. This to ensure that all team members use the exact same configuration when running ktlint regardless whether the Ktlint CLI or an API Consumer is being used.

The `.editorconfig` is a powerful configuration tool which can be used in very different ways. Most projects use a single `.editorconfig` file containing one common section for kotlin and kotlin scripts files. For example, the `.editorconfig` file of the Ktlint project contains following section:
```editorconfig
[*.{kt,kts}]
ij_kotlin_imports_layout = *
ij_kotlin_allow_trailing_comma = true
ij_kotlin_allow_trailing_comma_on_call_site = true
```
Other projects might contain multiple `.editorconfig` files for different parts of the project directory hierarchy. Or, use a single `.editorconfig` file containing multiple sections with different globs. Like all other configuration settings in Ktlint, the user should be able to enable and disable the experimental rules. Both for the entire set of experimental rules and for individual experimental rules.

Ktlint allows API Consumers to set default values and override values for the `.editorconfig`. Specifying a default value means that the user does not need to define the property in the `.editorconfig` file but if the user specifies the value, it will take precedence. Specifying the override value ensures that this takes precedence on a value specified by the user in the `.editorconfig`.

From the Ktlint perspective, it is advised that API Consumers provide the default value. See example below, for how to specify the `editorConfigDefault` property:
```
KtLintRuleEngine(
    ruleProviders = ruleProviders,
    editorConfigDefaults = EditorConfigDefaults(
        EditorConfig
            .builder()
            .section(
                Section
                    .builder()
                    .glob(Glob("*.{kt,kts}"))
                    .properties(
                        Property
                            .builder()
                            .name("ktlint_experimental")
                            .value("enabled"),
                    ),
            )
            .build()
    )
)
```
If the user has set property `ktlint_experimental` explicitly than that value will be used. If the value is not defined, the value provided via `editorConfigDefaults` will be used.

If you do want to ignore the value of `ktlint_experimental` as set by the user, than you can set the EditorConfigOverride property. But as said before that is discouraged as the user might not understand why the `.editorconfig` property is being ignored (provided that the value set is not equal to the value provided by the API Consumer).

### Added

### Removed

### Fixed
* Fix with array-syntax annotations on the same line as other annotations `annotation` ([#1765](https://github.com/pinterest/ktlint/issues/1765))
* Do not enable the experimental rules by default when `.editorconfig` properties `disabled_rules` or `ktlint_disabled_rules` are set. ([#1771](https://github.com/pinterest/ktlint/issues/1771))
* A function signature not having any parameters which exceeds the `max-line-length` should be ignored by rule `function-signature` ([#1773](https://github.com/pinterest/ktlint/issues/1773))
* Allow diacritics in names of classes, functions packages, and properties `class-naming`, `function-naming`, `package-name`, `property-naming` ([#1757](https://github.com/pinterest/ktlint/issues/1757))
* Prevent violation of `file-name` rule on code snippets ([#1768](https://github.com/pinterest/ktlint/issues/1768))
* Clarify that API Consumers have to enable experimental rules ([#1768](https://github.com/pinterest/ktlint/issues/1768))
* Trim spaces in the `.editorconfig` property `ij_kotlin_imports_layout`'s entries ([#1770](https://github.com/pinterest/ktlint/pull/1770))

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

### Indent rule

The `indent` rule has been rewritten from scratch. Solving problems in the old algorithm was very difficult. With the new algorithm this becomes a lot easier. Although the new implementation of the rule has been compared against several open source projects containing over 400,000 lines of code, it is still likely that new issues will be discovered. Please report your indentation issues so that these can be fixed as well.

### `.editorconfig` property to disable rules

In the previous release (0.47.x), the `.editorconfig`  property `disabled_rules` was deprecated and replaced with `ktlint_disabled_rules`. This latter property has now been deprecated as well in favour of a more flexible and better maintainable solution. Rule and rule sets can now be enabled/disabled with a separate property per rule (set). Please read [deprecation of (ktlint_)disable_rules property](https://pinterest.github.io/ktlint/faq/#why-is-editorconfig-property-disabled_rules-deprecated-and-how-do-i-resolve-this) for more information.

The KtLint CLI has not been changed. Although you can still use parameter `--experimental` to enable KtLint's Experimental rule set, you might want to set `.editorconfig` property `ktlint_experimental = enabled` instead.

### API Changes & RuleSet providers

If you are not an API consumer or Rule Set provider then you can skip this section.

#### Class relocations

Classes below have been relocated:

* Class `com.pinterest.ktlint.core.api.UsesEditorConfigProperties.EditorConfigProperty` has been replaced with `com.pinterest.ktlint.core.api.editorconfig.EditorConfigProperty`. 
* Class `com.pinterest.ktlint.core.KtLintParseException` has been replaced with `com.pinterest.ktlint.core.api.KtLintParseException`.
* Class `com.pinterest.ktlint.core.RuleExecutionException` has been replaced with `com.pinterest.ktlint.core.api.KtLintRuleException`.
* Class `com.pinterest.ktlint.reporter.format.internal.Color` has been moved to `com.pinterest.ktlint.reporter.format.Color`.
* Class `com.pinterest.ktlint.reporter.plain.internal.Color` has been moved to `com.pinterest.ktlint.reporter.plain.Color`.

#### Invoking `lint` and `format`

This is the last release that supports the `ExperimentalParams` to invoke the `lint` and `format` functions of KtLint. The `ExperimentalParams` contains a mix of configuration settings which are not dependent on the file/code which is to be processed. Other parameters in that class describe the code/file to be processed but can be configured inconsistently (for example a file with name "foo.kt" could be marked as a Kotlin Script file).

The static object `KtLint` is deprecated and replaced by class `KtLintRuleEngine` which is configured with `KtLintRuleEngineConfiguration`. The instance of the `KtLintRuleEngine` is intended to be reused for scanning all files in a project and should not be recreated per file.

Both `lint` and `format` are simplified and can now be called for a code block or for an entire file.

```kotlin
import java.io.File

// Define a reusable instance of the KtLint Rule Engine
val ktLintRuleEngine = KtLintRuleEngine(
  // Define configuration
)


// Process a collection of files
val files: Set<File> // Collect files in a convenient way
files.forEach(file in files) {
    ktLintRuleEngine.lint(file) {
        // Handle lint violations
    }
}

// or process a code sample for a given filepath
ktLintRuleEngine.lint(
  code = "code to be linted",
  filePath = Path("/path/to/source/file")
) {
  // Handle lint violations
}
```

#### Retrieve `.editorconfig`s

The list of `.editorconfig` files which will be accessed by KtLint when linting or formatting a given path can now be retrieved with the new API `KtLint.editorConfigFilePaths(path: Path): List<Path>`. 

This API can be called with either a file or a directory. It's intended usage is that it is called once with the root directory of a project before actually linting or formatting files of that project. When called with a directory path, all `.editorconfig` files in the directory or any of its subdirectories (except hidden directories) are returned. In case the given directory does not contain an `.editorconfig` file or if it does not contain the `root=true` setting, the parent directories are scanned as well until a root `.editorconfig` file is found.

Calling this API with a file path results in the `.editorconfig` files that will be accessed when processing that specific file. In case the directory in which the file resides does not contain an `.editorconfig` file or if it does not contain the `root=true` setting, the parent directories are scanned until a root `.editorconfig` file is found.

#### Psi filename replaces FILE_PATH_USER_DATA_KEY

Constant `KtLint.FILE_PATH_USER_DATA_KEY` is deprecated and will be removed in KtLint version 0.49.0. The file name will be passed correctly to the node with element type FILE and can be retrieved as follows:
```kotlin
if (node.isRoot()) {
    val fileName = (node.psi as? KtFile)?.name
    ...
}
```

### Added
* Wrap blocks in case the max line length is exceeded or in case the block contains a new line `wrapping` ([#1643](https://github.com/pinterest/ktlint/issues/1643))
* patterns can be read in from `stdin` with the `--patterns-from-stdin` command line options/flags ([#1606](https://github.com/pinterest/ktlint/pull/1606))
* Add basic formatting for context receiver in `indent` rule and new experimental rule `context-receiver-wrapping` ([#1672](https://github.com/pinterest/ktlint/issues/1672))
* Add naming rules for classes and objects (`class-naming`), functions (`function-naming`) and properties (`property-naming`) ([#44](https://github.com/pinterest/ktlint/issues/44))
* Add new experimental rule for unexpected spacing between function name and opening parenthesis (`spacing-between-function-name-and-opening-parenthesis`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
* Add new experimental rule for unexpected spacing in the parameter list (`parameter-list-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
* Add new experimental rule for incorrect spacing around the function return type (`function-return-type-spacing`) ([#1341](https://github.com/pinterest/ktlint/pull/1341))
* Add new experimental rule for unexpected spaces in a nullable type (`nullable-type-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
* Do not add a space after the typealias name (`type-parameter-list-spacing`) ([#1435](https://github.com/pinterest/ktlint/issues/1435))
* Add new experimental rule for consistent spacing before the start of the function body (`function-start-of-body-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
* Suppress ktlint rules using `@Suppress` ([more information](https://github.com/pinterest/ktlint#disabling-for-a-statement-using-suppress)) ([#765](https://github.com/pinterest/ktlint/issues/765))
* Add experimental rule for rewriting the function signature (`function-signature`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))

### Fixed
- Move disallowing blank lines in chained method calls from `no-consecutive-blank-lines` to new rule (`no-blank-lines-in-chained-method-calls`) ([#1248](https://github.com/pinterest/ktlint/issues/1248))
- Fix check of spacing in the receiver type of an anonymous function ([#1440](https://github.com/pinterest/ktlint/issues/1440))
- Allow comment on same line as super class in class declaration `wrapping` ([#1457](https://github.com/pinterest/ktlint/pull/1457))
- Respect git hooksPath setting ([#1465](https://github.com/pinterest/ktlint/issues/1465))
- Fix formatting of a property delegate with a dot-qualified-expression `indent` ([#1340](https://github.com/pinterest/ktlint/ssues/1340))
- Keep formatting of for-loop in sync with default IntelliJ formatter (`indent`) and a newline in the expression in a for-statement should not force to wrap it `wrapping` ([#1350](https://github.com/pinterest/ktlint/issues/1350))
- Fix indentation of property getter/setter when the property has an initializer on a separate line `indent` ([#1335](https://github.com/pinterest/ktlint/issues/1335))
- When `.editorconfig` setting `indentSize` is set to value `tab` then return the default tab width as value for `indentSize` ([#1485](https://github.com/pinterest/ktlint/issues/1485))
- Allow suppressing all rules or a list of specific rules in the entire file with `@file:Suppress(...)`  ([#1029](https://github.com/pinterest/ktlint/issues/1029))


### Changed
- Update Kotlin development version to `1.7.0` and Kotlin version to `1.7.0`.
- Update shadow plugin to `7.1.2` release
- Update picocli to `4.6.3` release
- A file containing only one (non private) top level declaration (class, interface, object, type alias or function) must be named after that declaration. The name also must comply with the Pascal Case convention. The same applies to a file containing one single top level class declaration and one ore more extension functions for that class. `filename` ([#1004](https://github.com/pinterest/ktlint/pull/1117))
- Promote experimental rules to standard rules set: `annotation`, `annotation-spacing`, `argument-list-wrapping`, `double-colon-spacing`, `enum-entry-name-case`, `multiline-if-else`, `no-empty-first-line-in-method-block`, `package-name`, `traling-comma`, `spacing-around-angle-brackets`, `spacing-between-declarations-with-annotations`, `spacing-between-declarations-with-comments`, `unary-op-spacing` ([#1481](https://github.com/pinterest/ktlint/pull/1481))
- The CLI parameter `--android` can be omitted when the `.editorconfig` property `ktlint_code_style = android` is defined

## [0.47.1] - 2022-09-07

### Fixed
* Do not add trailing comma in empty parameter/argument list with comments (`trailing-comma-on-call-site`, `trailing-comma-on-declaration-site`) ([#1602](https://github.com/pinterest/ktlint/issues/1602))
* Fix class cast exception when specifying a non-string editorconfig setting in the default ".editorconfig" ([#1627](https://github.com/pinterest/ktlint/issues/1627))
* Fix indentation before semi-colon when it is pushed down after inserting a trailing comma  ([#1609](https://github.com/pinterest/ktlint/issues/1609))
* Do not show deprecation warning about property "disabled_rules" when using CLi-parameter `--disabled-rules` ([#1599](https://github.com/pinterest/ktlint/issues/1599))
* Traversing directory hierarchy at Windows ([#1600](https://github.com/pinterest/ktlint/issues/1600))
* Ant-style path pattern support ([#1601](https://github.com/pinterest/ktlint/issues/1601))
* Apply `@file:Suppress` on all toplevel declarations ([#1623](https://github.com/pinterest/ktlint/issues/1623)) 

### Changed
* Display warning instead of error when no files are matched, and return with exit code 0. ([#1624](https://github.com/pinterest/ktlint/issues/1624))

## [0.47.0] - 2022-08-19

### API Changes & RuleSet providers

If you are not an API user nor a RuleSet provider, then you can safely skip this section. Otherwise, please read below carefully and upgrade your usage of ktlint. In this and coming releases, we are changing and adapting important parts of our API in order to increase maintainability and flexibility for future changes. Please avoid skipping a releases as that will make it harder to migrate.

#### Rule lifecycle hooks / deprecate RunOnRootOnly visitor modifier

Up until ktlint 0.46 the Rule class provided only one life cycle hook. This "visit" hook was called in a depth-first-approach on all nodes in the file. A rule like the IndentationRule used the RunOnRootOnly visitor modifier to call this lifecycle hook for the root node only in combination with an alternative way of traversing the ASTNodes. Downside of this approach was that suppression of the rule on blocks inside a file was not possible ([#631](https://github.com/pinterest/ktlint/issues/631)). More generically, this applied to all rules, applying alternative traversals of the AST.

The Rule class now offers new life cycle hooks:
* beforeFirstNode: This method is called once before the first node is visited. It can be used to initialize the state of the rule before processing of nodes starts. The ".editorconfig" properties (including overrides) are provided as parameter.
* beforeVisitChildNodes: This method is called on a node in AST before visiting its child nodes. This is repeated recursively for the child nodes resulting in a depth first traversal of the AST. This method is the equivalent of the "visit" life cycle hooks. However, note that in KtLint 0.48, the UserData of the rootnode no longer provides access to the ".editorconfig" properties. This method can be used to emit Lint Violations and to autocorrect if applicable.
* afterVisitChildNodes: This method is called on a node in AST after all its child nodes have been visited. This method can be used to emit Lint Violations and to autocorrect if applicable.
* afterLastNode: This method is called once after the last node in the AST is visited. It can be used for teardown of the state of the rule.

Optionally, a rule can stop the traversal of the remainder of the AST whenever the goal of the rule has been achieved. See KDoc on Rule class for more information.

The "visit" life cycle hook will be removed in Ktlint 0.48. In KtLint 0.47 the "visit" life cycle hook will be called *only* when hook "beforeVisitChildNodes" is not overridden. It is recommended to migrate to the new lifecycle hooks in KtLint 0.47. Please create an issue, in case you need additional assistence to implement the new life cycle hooks in your rules.


#### Ruleset providing by Custom Rule Set Provider

The KtLint engine needs a more fine-grained control on the instantiation of new Rule instances. Currently, a new instance of a rule can be created only once per file. However, when formatting files the same rule instance is reused for a second processing iteration in case a Lint violation has been autocorrected. By re-using the same rule instance, state of that rule might leak from the first to the second processing iteration.

Providers of custom rule sets have to migrate the custom rule set JAR file. The current RuleSetProvider interface which is implemented in the custom rule set is deprecated and marked for removal in KtLint 0.48. Custom rule sets using the old RuleSetProvider interface will not be run in KtLint 0.48 or above.

For now, it is advised to implement the new RuleSetProviderV2 interface without removing the old RuleSetProvider interface. In this way, KtLint 0.47 and above use the RuleSetProviderV2 interface and ignore the old RuleSetProvider interface completely. KtLint 0.46 and below only use the old RuleSetProvider interface.

Adding the new interface is straight forward, as can be seen below:

```
// Current implementation
public class CustomRuleSetProvider : RuleSetProvider {
    override fun get(): RuleSet = RuleSet(
        "custom",
        CustomRule1(),
        CustomRule2(),
    )
}

// New implementation
public class CustomRuleSetProvider :
    RuleSetProviderV2(CUSTOM_RULE_SET_ID),
    RuleSetProvider {
    override fun get(): RuleSet =
        RuleSet(
            CUSTOM_RULE_SET_ID,
            CustomRule1(),
            CustomRule2()
        )

    override fun getRuleProviders(): Set<RuleProvider> =
        setOf(
            RuleProvider { CustomRule1() },
            RuleProvider { CustomRule2() }
        )

    private companion object {
        const val CUSTOM_RULE_SET_ID = custom"
    }
}

```

Also note that file 'resource/META-INF/services/com.pinterest.ktlint.core.RuleSetProviderV2' needs to be added. In case your custom rule set provider implements both RuleSetProvider and RuleSetProviderV2, the resource directory contains files for both implementation. The content of those files is identical as the interfaces are implemented on the same class.

Once above has been implemented, rules no longer have to clean up their internal state as the KtLint rule engine can request a new instance of the Rule at any time it suspects that the internal state of the Rule is tampered with (e.g. as soon as the Rule instance is used for traversing the AST).

#### Rule set providing by API Consumer

The KtLint engine needs a more fine-grained control on the instantiation of new Rule instances. Currently, a new instance of a rule can be created only once per file. However, when formatting files the same rule instance is reused for a second processing iteration in case a Lint violation has been autocorrected. By re-using the same rule instance, state of that rule might leak from the first to the second processing iteration.

The ExperimentalParams parameter which is used to invoke "KtLint.lint" and "KtLint.format" contains a new parameter "ruleProviders" which will replace the "ruleSets" parameter in KtLint 0.48. Exactly one of those parameters should be a non-empty set. It is preferred that API consumers migrate to using "ruleProviders".

```
// Old style using "ruleSets"
KtLint.format(
    KtLint.ExperimentalParams(
        ...
        ruleSets = listOf(
            RuleSet(
                "custom",
                CustomRule1(),
                CustomRule2()
            )
        ),
        ...
    )
)

// New style using "ruleProviders"
KtLint.format(
    KtLint.ExperimentalParams(
        ...
        ruleProviders = setOf(
            RuleProvider { CustomRule1() },
            RuleProvider { CustomRule2() }
        ),
        cb = { _, _ -> }
    )
)
```

Once above has been implemented, rules no longer have to clean up their internal state as the KtLint rule engine can request a new instance of the Rule at any time it suspects that the internal state of the Rule is tampered with (e.g. as soon as the Rule instance is used for traversing the AST).

#### Format callback

The callback function provided as parameter to the format function is now called for all errors regardless whether the error has been autocorrected. Existing consumers of the format function should now explicitly check the `autocorrected` flag in the callback result and handle it appropriately (in most case this will be ignoring the callback results for which `autocorrected` has value `true`).

#### CurrentBaseline

Class `com.pinterest.ktlint.core.internal.CurrentBaseline` has been replaced with `com.pinterest.ktlint.core.api.Baseline`.

Noteworthy changes:
* Field `baselineRules` (nullable) is replaced with `lintErrorsPerFile (non-nullable).
* Field `baselineGenerationNeeded` (boolean) is replaced with `status` (type `Baseline.Status`).

The utility functions provided via `com.pinterest.ktlint.core.internal.CurrentBaseline` are moved to the new class. One new method `List<LintError>.doesNotContain(lintError: LintError)` is added.

#### .editorconfig property "disabled_rules"

The `.editorconfig` property `disabled_rules` (api property `DefaultEditorConfigProperties.disabledRulesProperty`) has been deprecated and will be removed in a future version. Use `ktlint_disabled_rules` (api property `DefaultEditorConfigProperties.ktlintDisabledRulesProperty`) instead as it more clearly identifies that ktlint is the owner of the property. This property is to be renamed in `.editorconfig` files and `ExperimentalParams.editorConfigOverride`.   

Although, Ktlint 0.47.0 falls back on property `disabled_rules` whenever `ktlint_disabled_rules` is not found, this result in a warning message being printed. 

#### Default/alternative .editorconfig

Parameter "ExperimentalParams.editorConfigPath" is deprecated in favor of the new parameter "ExperimentalParams.editorConfigDefaults". When used in the old implementation this resulted in ignoring all ".editorconfig" files on the path to the file. The new implementation uses properties from the "editorConfigDefaults"parameter only when no ".editorconfig" files on the path to the file supplies this property for the filepath.

API consumers can easily create the EditConfigDefaults by calling
"EditConfigDefaults.load(path)" or creating it programmatically.

#### Reload of `.editorconfig` file

Some API Consumers keep a long-running instance of the KtLint engine alive. In case an `.editorconfig` file is changed, which was already loaded into the internal cache of the KtLint engine this change would not be taken into account by KtLint. One way to deal with this, was to clear the entire KtLint cache after each change in an `.editorconfig` file.

Now, the API consumer can reload an `.editorconfig`. If the `.editorconfig` with given path is actually found in the cached, it will be replaced with the new value directly. If the file is not yet loaded in the cache, loading will be deferred until the file is actually requested again.

Example:
```kotlin
KtLint.reloadEditorConfigFile("/some/path/to/.editorconfig")
```

#### Miscellaneous

Several methods for which it is unlikely that they are used by API consumers have been marked for removal from the public API in KtLint 0.48.0. Please create an issue in case you have a valid business case to keep such methods in the public API.

### Added

* Add `format` reporter. This reporter prints a one-line-summary of the formatting status per file. ([#621](https://github.com/pinterest/ktlint/issues/621)).

### Fixed

* Fix cli argument "--disabled_rules" ([#1520](https://github.com/pinterest/ktlint/issues/1520)).
* A file which contains a single top level declaration of type function does not need to be named after the function but only needs to adhere to the PascalCase convention. `filename` ([#1521](https://github.com/pinterest/ktlint/issues/1521)).
* Disable/enable IndentationRule on blocks in middle of file. (`indent`) [#631](https://github.com/pinterest/ktlint/issues/631)
* Allow usage of letters with diacritics in enum values and filenames (`enum-entry-name-case`, `filename`) ([#1530](https://github.com/pinterest/ktlint/issues/1530)).
* Fix resolving of Java version when JAVA_TOOL_OPTIONS is set ([#1543](https://github.com/pinterest/ktlint/issues/1543))
* When a glob is specified then ensure that it matches files in the current directory and not only in subdirectories of the current directory ([#1533](https://github.com/pinterest/ktlint/issues/1533)).
* Execute `ktlint` cli on default kotlin extensions only when an (existing) path to a directory is given. ([#917](https://github.com/pinterest/ktlint/issues/917)).
* Invoke callback on `format` function for all errors including the errors that are autocorrected ([#1491](https://github.com/pinterest/ktlint/issues/1491))
* Merge first line of body expression with function signature only when it fits on the same line `function-signature` ([#1527](https://github.com/pinterest/ktlint/issues/1527))
* Add missing whitespace when else is on same line as true condition `multiline-if-else` ([#1560](https://github.com/pinterest/ktlint/issues/1560))
* Fix multiline if-statements `multiline-if-else` ([#828](https://github.com/pinterest/ktlint/issues/828))
* Prevent class cast exception on ".editorconfig" property `ktlint_code_style`  ([#1559](https://github.com/pinterest/ktlint/issues/1559))
* Handle trailing comma in enums `trailing-comma` ([#1542](https://github.com/pinterest/ktlint/pull/1542))
* Support globs containing directories in the ".editorconfig" supplied via CLI "--editorconfig"  ([#1551](https://github.com/pinterest/ktlint/pull/1551))
* Fix indent of when entry with a dot qualified expression instead of simple value when trailing comma is required ([#1519](https://github.com/pinterest/ktlint/pull/1519))
* Fix whitespace between trailing comma and arrow in when entry when trailing comma is required ([#1519](https://github.com/pinterest/ktlint/pull/1519))
* Prevent false positive in parameter list for which the last value parameter is a destructuring declaration followed by a trailing comma `wrapping` ([#1578](https://github.com/pinterest/ktlint/issues/1578))

### Changed

* Print an error message and return with non-zero exit code when no files are found that match with the globs ([#629](https://github.com/pinterest/ktlint/issues/629)).
* Invoke callback on `format` function for all errors including the errors that are autocorrected ([#1491](https://github.com/pinterest/ktlint/issues/1491))
* Improve rule `annotation` ([#1574](https://github.com/pinterest/ktlint/pull/1574))
* Rename `.editorconfig` property `disabled_rules` to `ktlint_disabled_rules` ([#701](https://github.com/pinterest/ktlint/issues/701))
* Allow file and directory paths in CLI-parameter "--editorconfig" ([#1580](https://github.com/pinterest/ktlint/pull/1580))
* Update Kotlin development version to `1.7.20-beta` and Kotlin version to `1.7.10`.
* Update release scripting to set version number in mkdocs documentation ([#1575](https://github.com/pinterest/ktlint/issues/1575)).
* Update Gradle to `7.5.1` version

### Removed
* Remove support to generate IntelliJ IDEA configuration files as this no longer fits the scope of the ktlint project ([#701](https://github.com/pinterest/ktlint/issues/701))

...