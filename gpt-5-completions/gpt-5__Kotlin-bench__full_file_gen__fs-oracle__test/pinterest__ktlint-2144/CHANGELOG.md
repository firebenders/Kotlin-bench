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

### Changed

* Change default code style to `ktlint_official`. Previously, the default was `intellij_idea` (former `kotlin_official`). If you prefer IDE-compatible formatting, set `ktlint_code_style = intellij_idea` (or `android_studio`) in your `.editorconfig`. [#1.0-default-style]
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

In Kotlin 1.9 the extension points of the embedded kotlin compiler will change. Ktlint only uses the `org.jetbrains.kotlin.com.intellij.treeCopyHandler` extension point. This extension is not yet supported in 1.9, neither is it documented ([#KT-58704](https://youtrack.jetbrains.com/issue/KT-58704/Support-and-document-extension-point-org.jetbrains.kotlin.com.intellij.treeCopyHandler)). Without this extension point it might happen that your custom rules will throw exceptions during runtime. See [#1981](https://github.com/pinterest/ktlint/issues/1981).

In Ktlint, 7 out of 77 rules needed small and sometimes bigger changes to become independent of the extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler`. The impact on your custom rules may vary dependent on the way the autocorrect has been implemented. When manipulating `ASTNode`s there seems to be no impact. When, manipulating `PsiElement`s, some functions consistently result in a runtime exception.

Based on the refactoring of the rules as provided by `ktlint-ruleset-standard` in Ktlint `0.49.x` the suggested refactoring is as follows:

* Replace `LeafElement.replaceWithText(String)` with `LeafElement.rawReplaceWithText(String)`.
* Replace `PsiElement.addAfter(PsiElement, PsiElement)` with `AstNode.addChild(AstNode, AstNode)`. Note that this method inserts the new node (first) argument *before* the second argument node and as of that is not a simple replacement of the `PsiElement.addAfter(PsiElement, PsiElement)`.
* Replace `PsiElement.replace(PsiElement)` with a sequence of `AstNode.addChild(AstNode, AstNode)` and `AstNode.removeChild(AstNode)`.

Be aware that your custom rules might use other functions which also throw exceptions when the extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler` is no longer supported.

In order to help you to analyse and fix the problems with your custom rules, ktlint temporarily supports to disable the extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler` using a flag. This flag is available in the Ktlint CLI and in the `KtlintRuleEngine`. By default, the extension point is enabled like it was in previous versions of ktlint.

At least you should analyse the problems by running your test suits by running ktlint and disabling the extension point. Next you can start with fixing and releasing the updated rules. All rules in this version of ktlint have already been refactored and are not dependent on the extension point anymore. In Ktlint CLI the flag is to be activated with parameter `--disable-kotlin-extension-point`. API Consumers that use the `KtlintRuleEngine` directly, have to set property `enableKotlinCompilerExtensionPoint` to `false`.

At this point in time, it is not yet decided what the next steps will be. Ktlint might drop the support of the extension points entirely. Or, if the extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler` is fully supported at the time that ktlint will be based on kotlin 1.9 it might be kept. In either case, the flag will be dropped in a next version of ktlint.

### Added

* Add new experimental rule `binary-expression-wrapping`. This rule wraps a binary expression in case the max line length is exceeded ([#1940](https://github.com/pinterest/ktlint/issues/1940))
* Add flag to disable extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler` to analyse impact on custom rules [#1981](https://github.com/pinterest/ktlint/issues/1981)
* Add new experimental rule `no-empty-file` for all code styles. A kotlin (script) file may not be empty ([#1074](https://github.com/pinterest/ktlint/issues/1074))
* Add new experimental rule `statement-wrapping` which ensures function, class, or other blocks statement body doesn't start or end at starting or ending braces of the block ([#1938](https://github.com/pinterest/ktlint/issues/1938))
* Add new experimental rule `blank-line-before-declaration`. This rule requires a blank line before class, function or property declarations ([#1939](https://github.com/pinterest/ktlint/issues/1939))
* Wrap multiple statements on same line `wrapping` ([#1078](https://github.com/pinterest/ktlint/issues/1078))
* Add new rule `ktlint-suppression` to replace the `ktlint-disable` and `ktlint-enable` directives with annotations. This rule can not be disabled via the `.editorconfig` ([#1947](https://github.com/pinterest/ktlint/issues/1947))
* Inform user about using `--format` option of KtLint CLI when finding a violation that can be autocorrected ([#1071](https://github.com/pinterest/ktlint/issues/1071))

### Removed

* Code which was deprecated in `0.49.x` is removed. Consult changelog of 0.49.x` released for more information. Summary of removed code: 

### Fixed

* Do not flag a (potential) mutable extension property in case the getter is annotated or prefixed with a modifier `property-naming` ([#2024](https://github.com/pinterest/ktlint/issues/2024))
* Do not merge an annotated expression body with the function signature even if it fits on a single line ([#2043](https://github.com/pinterest/ktlint/issues/2043))
* Ignore property with name `serialVersionUID` in `property-naming` ([#2045](https://github.com/pinterest/ktlint/issues/2045))
* Prevent incorrect reporting of violations in case a nullable function type reference exceeds the maximum line length `parameter-list-wrapping` ([#1324](https://github.com/pinterest/ktlint/issues/1324)) 
* Prevent false negative on `else` branch when body contains only chained calls or binary expression ([#2057](https://github.com/pinterest/ktlint/issues/2057))
* Fix indent when property value is wrapped to next line ([#2095](https://github.com/pinterest/ktlint/issues/2095)) 

### Changed

* Fix Java interoperability issues with `RuleId` and `RuleSetId` classes. Those classes were defined as value classes in `0.49.0` and `0.49.1`. Although the classes were marked with `@JvmInline` it seems that it is not possible to uses those classes from Java base API Consumers like Spotless. The classes have now been replaced with data classes ([#2041](https://github.com/pinterest/ktlint/issues/2041))
* Update dependency `info.picocli:picocli` to v4.7.4
* Update dependency `org.junit.jupiter:junit-jupiter` to v5.9.3
* Update Kotlin development version to `1.8.22` and Kotlin version to `1.8.22`.
* Update dependency io.github.detekt.sarif4k:sarif4k to v0.4.0
* Update dependency org.jetbrains.dokka:dokka-gradle-plugin to v1.8.20
* Run format up to 3 times in case formatting introduces changes which also can be autocorrected ([#2084](https://github.com/pinterest/ktlint/issues/2084))

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
* Prevent multiple expressions on same line separated by semicolon ([#1078](https://github.com/pinterest/ktlint/issues/1078))

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

... (rest of the changelog remains unchanged)