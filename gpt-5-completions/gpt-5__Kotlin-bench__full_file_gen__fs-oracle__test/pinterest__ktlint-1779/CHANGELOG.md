# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed
* Do not enable the experimental rules by default when `.editorconfig` properties `disabled_rules` or `ktlint_disabled_rules` are set. ([#1771](https://github.com/pinterest/ktlint/issues/1771))
* A function signature not having any parameters which exceeds the `max-line-length` should be ignored by rule `function-signature` ([#1773](https://github.com/pinterest/ktlint/issues/1773))
* Avoid false positive "Missing newline after "{" (wrapping)" when a lambda block is inside a Kotlin string template (e.g. in a raw string) and the overall line exceeds `max_line_length`. The `wrapping` rule no longer attempts to wrap blocks that are part of a string template entry. 

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

Constant `KtLint.FILE_PATH_USER_DATA_KEY` is deprecated and replaced and will be removed in KtLint version 0.49.0. The file name will be passed correctly to the node with element type FILE and can be retrieved as follows:
```kotlin
if (node.isRoot()) {
    val fileName = (node.psi as? KtFile)?.name
    ...
}
```

### Added
* Wrap blocks in case the max line length is exceeded or in case the block contains a new line `wrapping` ([#1643](https://github.com/pinterest/ktlint/issue/1643))
* patterns can be read in from `stdin` with the `--patterns-from-stdin` command line options/flags ([#1606](https://github.com/pinterest/ktlint/pull/1606))
* Add basic formatting for context receiver in `indent` rule and new experimental rule `context-receiver-wrapping` ([#1672](https://github.com/pinterest/ktlint/issue/1672))
* Add naming rules for classes and objects (`class-naming`), functions (`function-naming`) and properties (`property-naming`) ([#44](https://github.com/pinterest/ktlint/issue/44))
* Add new built-in reporter `plain-summary` which prints a summary the number of violation which have been autocorrected or could not be autocorrected, both split by rule. 


### Fixed

* Let a rule process all nodes even in case the rule is suppressed for a node so that the rule can update the internal state ([#1644](https://github.com/pinterest/ktlint/issue/1644))
* Read `.editorconfig` when running CLI with options `--stdin` and `--editorconfig` ([#1651](https://github.com/pinterest/ktlint/issue/1651))
* Do not add a trailing comma in case a multiline function call argument is found but no newline between the arguments `trailing-comma-on-call-site` ([#1642](https://github.com/pinterest/ktlint/issue/1642))
* Add missing `ktlint_disabled_rules` to exposed `editorConfigProperties` ([#1671](https://github.com/pinterest/ktlint/issue/1671))
* Do not add a second trailing comma, if the original trailing comma is followed by a KDOC `trailing-comma-on-declaration-site` and `trailing-comma-on-call-site` ([#1676](https://github.com/pinterest/ktlint/issue/1676))
* A function signature preceded by an annotation array should be handled similar as function preceded by a singular annotation `function-signature` ([#1690](https://github.com/pinterest/ktlint/issue/1690))
* Fix offset of annotation violations
* Fix line offset when blank line found between class and primary constructor
* Remove needless blank line between class followed by EOL, and primary constructor
* Fix offset of unexpected linebreak before assignment
* Remove whitespace before redundant semicolon if the semicolon is followed by whitespace 

### Changed
* Update Kotlin development version to `1.8.0-RC` and Kotlin version to `1.7.21`.
* The default value for trailing comma's on call site is changed to `true` unless the `android codestyle` is enabled. Note that KtLint from a consistency viewpoint *enforces* the trailing comma on call site while default IntelliJ IDEA formatting only *allows* the trailing comma but leaves it up to the developer's discretion. ([#1670](https://github.com/pinterest/ktlint/pull/1670))
* The default value for trailing comma's on declaration site is changed to `true` unless the `android codestyle` is enabled. Note that KtLint from a consistency viewpoint *enforces* the trailing comma on declaration site while default IntelliJ IDEA formatting only *allows* the trailing comma but leaves it up to the developer's discretion. ([#1669](https://github.com/pinterest/ktlint/pull/1669))
* CLI options `--debug`, `--trace`, `--verbose` and `-v` are replaced with `--log-level=<level>` or the short version `-l=<level>, see [CLI log-level](https://pinterest.github.io/ktlint/install/cli/#logging). ([#1632](https://github.com/pinterest/ktlint/issue/1632))
* In CLI, disable logging entirely by setting `--log-level=none` or `-l=none` ([#1652](https://github.com/pinterest/ktlint/issues/1652))
* Rewrite `indent` rule. Solving problems in the old algorithm was very difficult. With the new algorithm this becomes a lot easier. Although the new implementation of the rule has been compared against several open source projects containing over 400,000 lines of code, it is still likely that new issues will be discovered. Please report your indentation issues so that these can be fixed as well. ([#1682](https://github.com/pinterest/ktlint/pull/1682), [#1321](https://github.com/pinterest/ktlint/issues/1321), [#1200](https://github.com/pinterest/ktlint/issues/1200), [#1562](https://github.com/pinterest/ktlint/issues/1562), [#1563](https://github.com/pinterest/ktlint/issues/1563), [#1639](https://github.com/pinterest/ktlint/issues/1639))
* Add methods "ASTNode.upsertWhitespaceBeforeMe" and "ASTNode.upsertWhitespaceAfterMe" as replacements for "LeafElement.upsertWhitespaceBeforeMe" and "LeafElement.upsertWhitespaceAfterMe". The new methods are more versatile and allow code to be written more readable in most places. ([#1687](https://github.com/pinterest/ktlint/pull/1687))
* Rewrite `indent` rule. Solving problems in the old algorithm was very difficult. With the new algorithm this becomes a lot easier. Although the new implementation of the rule has been compared against several open source projects containing over 400,000 lines of code, it is still likely that new issues will be discovered. Please report your indentation issues so that these can be fixed as well. ([#1682](https://github.com/pinterest/ktlint/pull/1682), [#1321](https://github.com/pinterest/ktlint/issues/1321), [#1200](https://github.com/pinterest/ktlint/issues/1200), [#1562](https://github.com/pinterest/ktlint/issues/1562), [#1563](https://github.com/pinterest/ktlint/issues/1563), [#1639](https://github.com/pinterest/ktlint/issues/1639), [#1688](https://github.com/pinterest/ktlint/issues/1688))
* Add support for running tests on `java 19`, remove support for running tests on `java 18`.
* Update `io.github.detekt.sarif4k:sarif4k` version to `0.2.0` ([#1701](https://github.com/pinterest/ktlint/issues/1701)).

## [0.47.1] - 2022-09-07

### Fixed
* Do not add trailing comma in empty parameter/argument list with comments (`trailing-comma-on-call-site`, `trailing-comma-on-declaration-site`) ([#1602](https://github.com/pinterest/ktlint/issue/1602))
* Fix class cast exception when specifying a non-string editorconfig setting in the default ".editorconfig" ([#1627](https://github.com/pinterest/ktlint/issue/1627))
* Fix indentation before semi-colon when it is pushed down after inserting a trailing comma  ([#1609](https://github.com/pinterest/ktlint/issue/1609))
* Do not show deprecation warning about property "disabled_rules" when using CLi-parameter `--disabled-rules` ([#1599](https://github.com/pinterest/ktlint/issues/1599))
* Traversing directory hierarchy at Windows ([#1600](https://github.com/pinterest/ktlint/issues/1600))
* Ant-style path pattern support ([#1601](https://github.com/pinterest/ktlint/issues/1601))
* Apply `@file:Suppress` on all toplevel declarations ([#1623](https://github.com/pinterest/ktlint/issues/1623)) 

### Changed
* Display warning instead of error when no files are matched, and return with exit code 0. ([#1624](https://github.com/pinterest/ktlint/issues/1624))

## [0.47.0] - 2022-08-19

### API Changes & RuleSet providers

If you are not an API consumer nor a RuleSet provider, then you can safely skip this section. Otherwise, please read below carefully and upgrade your usage of ktlint. In this and coming releases, we are changing and adapting important parts of our API in order to increase maintainability and flexibility for future changes. Please avoid skipping a releases as that will make it harder to migrate.

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

The utility functions provided via `com.pinterest.ktlint.core.internal.CurrentBaseline` are moved to the new class. One new method `List<LintError>.doesNotContain(lintError: LintError)` is added.

### Added

* Add `format` reporter. This reporter prints a one-line-summary of the formatting status per file. ([#621](https://github.com/pinterest/ktlint/issue/621)).

### Fixed

* Fix cli argument "--disabled_rules" ([#1520](https://github.com/pinterest/ktlint/issue/1520)).
* A file which contains a single top level declaration of type function does not need to be named after the function but only needs to adhere to the PascalCase convention. The same applies to a file containing one single top level class declaration and one ore more extension functions for that class. `filename` ([#1521](https://github.com/pinterest/ktlint/issue/1521)).
* Disable/enable IndentationRule on blocks in middle of file. (`indent`) [#631](https://github.com/pinterest/ktlint/issues/631)
* Allow usage of letters with diacritics in enum values and filenames (`enum-entry-name-case`, `filename`) ([#1530](https://github.com/pinterest/ktlint/issue/1530)).
* Fix resolving of Java version when JAVA_TOOL_OPTIONS is set ([#1543](https://github.com/pinterest/ktlint/issues/1543))
* When a glob is specified then ensure that it matches files in the current directory and not only in subdirectories of the current directory ([#1533](https://github.com/pinterest/ktlint/issue/1533)).
* Execute `ktlint` cli on default kotlin extensions only when an (existing) path to a directory is given. ([#917](https://github.com/pinterest/ktlint/issue/917)).
* Invoke callback on `format` function for all errors including errors that are autocorrected ([#1491](https://github.com/pinterest/ktlint/issues/1491))
* Merge first line of body expression with function signature only when it fits on the same line `function-signature` ([#1527](https://github.com/pinterest/ktlint/issues/1527))
* Add missing whitespace when else is on same line as true condition `multiline-if-else` ([#1560](https://github.com/pinterest/ktlint/issues/1560))
* Fix multiline if-statements `multiline-if-else` ([#828](https://github.com/pinterest/ktlint/issues/828))
* Prevent class cast exception on ".editorconfig" property `ktlint_code_style`  ([#1559](https://github.com/pinterest/ktlint/issues/1559))
* Handle trailing comma in enums `trailing-comma` ([#1542](https://github.com/pinterest/ktlint/pull/1542))
* Allow EOL comment after annotation ([#1539](https://github.com/pinterest/ktlint/issues/1539))
* Split rule `trailing-comma` into `trailing-comma-on-call-site` and `trailing-comma-on-declaration-site` ([#1555](https://github.com/pinterest/ktlint/pull/1555))
* Support globs containing directories in the ".editorconfig" supplied via CLI "--editorconfig"  ([#1551](https://github.com/pinterest/ktlint/pull/1551))
* Fix indent of when entry with a dot qualified expression instead of simple value when trailing comma is required ([#1519](https://github.com/pinterest/ktlint/pull/1519))
* Fix whitespace between trailing comma and arrow in when entry when trailing comma is required ([#1519](https://github.com/pinterest/ktlint/pull/1519))
* Prevent false positive in parameter list for which the last value parameter is a destructuring declaration followed by a trailing comma `wrapping` ([#1578](https://github.com/pinterest/ktlint/issues/1578))

### Changed

* Print an error message and return with non-zero exit code when no files are found that match with the globs ([#629](https://github.com/pinterest/ktlint/issue/629)).
* Invoke callback on `format` function for all errors including errors that are autocorrected ([#1491](https://github.com/pinterest/ktlint/issues/1491))
* Improve rule `annotation` ([#1574](https://github.com/pinterest/ktlint/pull/1574))
* Rename `.editorconfig` property `disabled_rules` to `ktlint_disabled_rules` ([#701](https://github.com/pinterest/ktlint/issues/701))
* Allow file and directory paths in CLI-parameter "--editorconfig" ([#1580](https://github.com/pinterest/ktlint/pull/1580))
* Update Kotlin development version to `1.7.20-beta` and Kotlin version to `1.7.10`.
* Update release scripting to set version number in mkdocs documentation ([#1575](https://github.com/pinterest/ktlint/issue/1575)).
* Update Gradle to `7.5.1` version

### Removed
* Remove support to generate IntelliJ IDEA configuration files as this no longer fits the scope of the ktlint project ([#701](https://github.com/pinterest/ktlint/issues/701))

## [0.46.1] - 2022-06-21

Minor release to address some regressions introduced in 0.46.0

### Fixed

* Remove experimental flag `-Xuse-k2` as it forces API Consumers to compile their projects with this same flag ([#1506](https://github.com/pinterest/ktlint/pull/1506)).
* Account for separating spaces when parsing the disabled rules ([#1508](https://github.com/pinterest/ktlint/pull/1508)). 
* Do not remove space before a comment in a parameter list ([#1509](https://github.com/pinterest/ktlint/issue/1509)). 
* A delegate property which starts on the same line as the property declaration should not have an extra indentation `indent` ([#1510](https://github.com/pinterest/ktlint/pull/1510))

## [0.46.0] - 2022-06-18

### Promoting experimental rules to standard 

The rules below are promoted from the `experimental` ruleset to the `standard` ruleset.
* `annotation`
* `annotation-spacing`
* `argument-list-wrapping`
* `double-colon-spacing`
* `enum-entry-name-case`
* `multiline-if-else`
* `no-empty-first-line-in-method-block`
* `package-name`
* `trailing-comma`
* `spacing-around-angle-brackets`
* `spacing-between-declarations-with-annotations`
* `spacing-between-declarations-with-comments`
* `unary-op-spacing`

Note that as a result of moving the rules that the prefix `experimental:` has to be removed from all references to this rule. Check references in:
* The `.editorconfig` setting `disabled_rules`.
* KtLint disable and enable directives.
* The `VisitorModifier.RunAfterRule`.

If your project did not run with the `experimental` ruleset enabled before, you might expect new lint violations to be reported. Please note that rules can be disabled via the the `.editorconfig` in case you do not want the rules to be applied on your project.

### API Changes & RuleSet providers

If you are not an API user nor a RuleSet provider, then you can safely skip this section. Otherwise, please read below carefully and upgrade your usage of ktlint. In this and coming releases, we are changing and adapting important parts of our API in order to increase maintainability and flexibility for future changes. Please avoid skipping a releases as that will make it harder to migrate.

#### Lint and formatting functions

The lint and formatting changes no longer accept parameters of type `Params` but only `ExperimentalParams`. Also, the VisitorProvider parameter has been removed. Because of this, your integration with KtLint breaks. Based on feedback with ktlint 0.45.x, we now prefer to break at compile time instead of trying to keep the interface backwards compatible. Please raise an issue, in case you help to convert to the new API.

#### Use of ".editorconfig" properties & userData

The interface `UsesEditorConfigProperties` provides method `getEditorConfigValue` to retrieve a named `.editorconfig` property for a given ASTNode. When implementing this interface, the value `editorConfigProperties` needs to be overridden. Previously it was not checked whether a retrieved property was actually recorded in this list. Now, retrieval of unregistered properties results in an exception.

Property `Ktlint.DISABLED` has been removed. The property value can now be retrieved as follows:
```kotlin
astNode
    .getEditorConfigValue(DefaultEditorConfigProperties.disabledRulesProperty)
    .split(",")
```
and be supplied via the `ExperimentalParams` as follows:
```kotlin
ExperimentalParams(
    ...
    editorConfigOverride =  EditorConfigOverride.from(
      DefaultEditorConfigProperties.disabledRulesProperty to "some-rule-id,experimental:some-other-rule-id"
    )
    ...
)
```

Property `Ktlint.ANDROID_USER_DATA_KEY` has been removed. The property value can now be retrieved as follows:
```kotlin
astNode
    .getEditorConfigValue(DefaultEditorConfigProperties.codeStyleProperty)
```
and be supplied via the `ExperimentalParams` as follows:
```kotlin
ExperimentalParams(
    ...
    editorConfigOverride =  EditorConfigOverride.from(
      DefaultEditorConfigProperties.codeStyleProperty to "android" 
    )
    ...
)
```
This property defaults to the `official` Kotlin code style when not set.

#### Testing KtLint rules

An AssertJ style API for testing KtLint rules ([#1444](https://github.com/pinterest/ktlint/issues/1444)) has been added. Usage of this API is encouraged in favor of using the old RuleExtension API. For more information, see [KtLintAssertThat API]( https://github.com/pinterest/ktlint/blob/master/ktlint-test/README.MD)

### Added
- Add experimental rule for unexpected spacing between function name and opening parenthesis (`spacing-between-function-name-and-opening-parenthesis`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
- Add experimental rule for unexpected spacing in the parameter list (`parameter-list-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
- Add experimental rule for incorrect spacing around the function return type (`function-return-type-spacing`) ([#1341](https://github.com/pinterest/ktlint/pull/1341))
- Add experimental rule for unexpected spaces in a nullable type (`nullable-type-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
- Do not add a space after the typealias name (`type-parameter-list-spacing`) ([#1435](https://github.com/pinterest/ktlint/issues/1435))
- Add experimental rule for consistent spacing before the start of the function body (`function-start-of-body-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
- Suppress ktlint rules using `@Suppress` ([more information](https://github.com/pinterest/ktlint#disabling-for-a-statement-using-suppress)) ([#765](https://github.com/pinterest/ktlint/issues/765))
- Add experimental rule for rewriting the function signature (`function-signature`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))

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

... (rest of the changelog remains unchanged)