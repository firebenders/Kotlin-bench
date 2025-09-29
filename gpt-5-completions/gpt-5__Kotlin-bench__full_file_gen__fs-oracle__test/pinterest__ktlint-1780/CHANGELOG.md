# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Additional clarification on API Changes in `0.48.0` and `0.48.1`

Starting with Ktlint `0.48.x`, rule and rule sets can be enabled/disabled with a separate property per rule (set). Please read [deprecation of (ktlint_)disable_rules property](https://pinterest.github.io/ktlint/faq/#why-is-editorconfig-property-disabled_rules-deprecated-and-how-do-i-resolve-this) for more information.

API Consumers that provide experimental rules to the KtLintRuleEngine, must also enable the experimental rules or instruct their users to do so in the `.editorconfig` file. From the perspective of the API Consumer it might be confusing or unnecessary to do so as the experimental rule was already provided explicitly.

Ktlint wants to provide the user (e.g. a developer) a uniform and consistent user experience. The `.editorconfig` becomes more and more central to store configuration for Ktlint. This to ensure that all team members use the exact same configuration when running ktlint regardless whether the Ktlint CLI or an API Consumer is being used.

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
* Prevent violation of `file-name` rule on code snippets ([#1768](https://github.com/pinterest/ktlint/issues/1768))
* Clarify that API Consumers have to enable experimental rules ([#1768](https://github.com/pinterest/ktlint/issues/1768))
* Trim spaces in the `.editorconfig` property `ij_kotlin_imports_layout`'s entries ([#1770](https://github.com/pinterest/ktlint/pull/1770))
* Allow non-ASCII letters (e.g., å, ä, ö, æ, ø) in package names (`package-name`)

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
* In CLI, disable logging entirely by setting `--log-level=none` or `-l=none` ([#1652](https://github.com/pinterest/ktlint/issue/1652))
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

* Add `format` reporter. This reporter prints a one-line-summary of the formatting status per file. ([#621](https://github.com/pinterest/ktlint/issue/621)).

### Fixed

* Fix cli argument "--disabled_rules" ([#1520](https://github.com/pinterest/ktlint/issue/1520)).
* A file which contains a single top level declaration of type function does not need to be named after the function but only needs to adhere to the PascalCase convention. `filename` ([#1521](https://github.com/pinterest/ktlint/issue/1521)).
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

## [0.45.2] - 2022-04-06

### Fixed
- Resolve compatibility issues introduced in 0.45.0 and 0.45.1 ([#1434](https://github.com/pinterest/ktlint/issues/1434)). Thanks to [mateuszkwiecinski](https://github.com/mateuszkwiecinski) and [jeremymailen](https://github.com/jeremymailen) for your input on this issue.

### Changed
* Set Kotlin development version to `1.6.20` and Kotlin version to `1.6.20`.

## [0.45.1] - 2022-03-21

Minor release to fix a breaking issue with `ktlint` API consumers

### Fixed
- Remove logback dependency from ktlint-core module ([#1421](https://github.com/pinterest/ktlint/issues/1421))

## [0.45.0] - 2022-03-18

### API Changes & RuleSet providers

If you are not an API user nor a RuleSet provider, then you can safely skip this section. Otherwise, please read below carefully and upgrade your usage of ktlint. In this and coming releases, we are changing and adapting important parts of our API in order to increase maintainability and flexibility for future changes. Please avoid skipping a releases as that will make it harder to migrate.

#### Retrieving ".editorconfig" property value

This section is applicable when providing rules that depend on one or more values of ".editorconfig" properties. Property values should no longer be retrieved via *EditConfig* or directly via `userData[EDITOR_CONFIG_USER_DATA_KEY]`. Property values should now only be retrieved using method `ASTNode.getEditorConfigValue(editorConfigProperty)` of interface `UsesEditorConfigProperties` which is provided in this release. Starting from next release after the current release, the *EditConfig* and/or `userData[EDITOR_CONFIG_USER_DATA_KEY]` may be removed without further notice which will break your API or rule. To prevent disruption of your end user, you should migrate a.s.a.p.

### Added
- Add experimental rule for unexpected spaces in a type reference before a function identifier (`function-type-reference-spacing`) ([#1341](https://github.com/pinterest/ktlint/issues/1341))
- Add experimental rule for incorrect spacing after a type parameter list (`type-parameter-list-spacing`) ([#1366](https://github.com/pinterest/ktlint/pull/1366))
- Add experimental rule to detect discouraged comment locations (`discouraged-comment-location`) ([#1365](https://github.com/pinterest/ktlint/pull/1365))
- Add rule to check spacing after fun keyword (`fun-keyword-spacing`) ([#1362](https://github.com/pinterest/ktlint/pull/1362))
- Add experimental rules for unnecessary spacing between modifiers in and after the last modifier in a modifier list ([#1361](https://github.com/pinterest/ktlint/pull/1361))
- New experimental rule for aligning the initial stars in a block comment when present (`experimental:block-comment-initial-star-alignment` ([#297](https://github.com/pinterest/ktlint/issues/297))
- Respect `.editorconfig` property `ij_kotlin_packages_to_use_import_on_demand` (`no-wildcard-imports`) ([#1272](https://github.com/pinterest/ktlint/pull/1272))
- Add new experimental rules for wrapping of block comment (`comment-wrapping`) ([#1403](https://github.com/pinterest/ktlint/pull/1403))
- Add new experimental rules for wrapping of KDoc comment (`kdoc-wrapping`) ([#1403](https://github.com/pinterest/ktlint/pull/1403))
- Add experimental rule for incorrect spacing after a type parameter list (`type-parameter-list-spacing`) ([#1366](https://github.com/pinterest/ktlint/pull/1366))
- Expand check task to run tests on JDK 17 - "testOnJdk17"

### Fixed
- Fix lint message to "Unnecessary long whitespace" (`no-multi-spaces`) ([#1394](https://github.com/pinterest/ktlint/issues/1394))
- Do not remove trailing comma after a parameter of type array in an annotation (experimental:trailing-comma) ([#1379](https://github.com/pinterest/ktlint/issues/1379))
- Do not delete blank lines in KDoc (no-trailing-spaces) ([#1376](https://github.com/pinterest/ktlint/issues/1376))
- Revert remove unnecessary wildcard imports as introduced in Ktlint 0.43.0 (`no-unused-imports`) ([#1277](https://github.com/pinterest/ktlint/issues/1277)), ([#1393](https://github.com/pinterest/ktlint/issues/1393)), ([#1256](https://github.com/pinterest/ktlint/issues/1256))
- (Possibly) resolve memory leak ([#1216](https://github.com/pinterest/ktlint/issues/1216))
- Initialize loglevel in Main class after parsing the CLI parameters ([#1412](https://github.com/pinterest/ktlint/issues/1412))

### Changed
- Print the rule id always in the PlainReporter ([#1121](https://github.com/pinterest/ktlint/issues/1121))
- All wrapping logic is moved from the `indent` rule to the new rule `wrapping` (as part of the `standard` ruleset). In case you currently have disabled the `indent` rule, you may want to reconsider whether this is still necessary or that you also want to disable the new `wrapping` rule to keep the status quo. Both rules can be run independent of each other. ([#835](https://github.com/pinterest/ktlint/issues/835))

## [0.44.0] - 2022-02-15

Please welcome [paul-dingemans](https://github.com/paul-dingemans) as an official maintainer of ktlint!

### Added
- Use Gradle JVM toolchain with language version 8 to compile the project
- Basic tests for CLI ([#540](https://github.com/pinterest/ktlint/issues/540))
- Add experimental rule for unnecessary parentheses in function call followed by lambda ([#1068](https://github.com/pinterest/ktlint/issues/1068))

### Fixed
- Fix indentation of function literal ([#1247](https://github.com/pinterest/ktlint/issues/1247))
- Fix false positive in rule spacing-between-declarations-with-annotations ([#1281](https://github.com/pinterest/ktlint/issues/1281))
- Do not remove imports for same class when different alias is used ([#1243](https://github.com/pinterest/ktlint/issues/1243))
- Fix NoSuchElementException for property accessor (`trailing-comma`) ([#1280](https://github.com/pinterest/ktlint/issues/1280))
- Fix ClassCastException using ktlintFormat on class with KDoc (`no-trailing-spaces`) ([#1270](https://github.com/pinterest/ktlint/issues/1270))
- Do not remove trailing comma in annotation ([#1297](https://github.com/pinterest/ktlint/issues/1297))
- Do not remove import which is used as markdown link in KDoc only (`no-unused-imports`) ([#1282](https://github.com/pinterest/ktlint/issues/1282))
- Fix indentation of secondary constructor (`indent`) ([#1222](https://github.com/pinterest/ktlint/issues/1222))
- Custom gradle tasks with custom ruleset results in warning ([#1269](https://github.com/pinterest/ktlint/issues/1269))
- Fix alignment of arrow when trailing comma is missing in when entry (`trailing-comma`) ([#1312](https://github.com/pinterest/ktlint/issues/1312))
- Fix indent of delegated super type entry (`indent`) ([#1210](https://github.com/pinterest/ktlint/issues/1210))
- Improve indentation of closing quotes of a multiline raw string literal (`indent`) ([#1262](https://github.com/pinterest/ktlint/pull/1262))
- Trailing space should not lead to delete of indent of next line (`no-trailing-spaces`) ([#1334](https://github.com/pinterest/ktlint/pull/1334))
- Force a single line function type inside a nullable type to a separate line when the max line length is exceeded (`parameter-list-wrapping`) ([#1255](https://github.com/pinterest/ktlint/issues/1255))
- A single line function with a parameter having a lambda as default argument does not throw error (`indent`) ([#1330](https://github.com/pinterest/ktlint/issues/1330))
- Fix executable jar on Java 16+ ([#1195](https://github.com/pinterest/ktlint/issues/1195)) 
- Fix false positive unused import after autocorrecting a trailing comma ([#1367](https://github.com/pinterest/ktlint/issues/1367)) 
- Fix false positive indentation (`parameter-list-wrapping`, `argument-list-wrapping`) ([#897](https://github.com/pinterest/ktlint/issues/897), [#1045](https://github.com/pinterest/ktlint/issues/1045), [#1119](https://github.com/pinterest/ktlint/issues/1119), [#1255](https://github.com/pinterest/ktlint/issues/1255), [#1267](https://github.com/pinterest/ktlint/issues/1267), [#1319](https://github.com/pinterest/ktlint/issues/1319), [#1320](https://github.com/pinterest/ktlint/issues/1320), [#1337](https://github.com/pinterest/ktlint/issues/1337)
- Force a single line function type inside a nullable type to a separate line when the max line length is exceeded (`parameter-list-wrapping`) ([#1255](https://github.com/pinterest/ktlint/issues/1255))

### Changed
- Update Kotlin version to `1.6.0` release
- Add separate tasks to run tests on JDK 11 - "testOnJdk11"
- Update Dokka to `1.6.0` release
- Apply ktlint experimental rules on the ktlint code base itself.
- Update shadow plugin to `7.1.1` release
- Add Kotlin-logging backed by logback as logging framework ([#589](https://github.com/pinterest/ktlint/issues/589))
- Update Gradle to `7.4` version

## [0.43.2] - 2021-12-01

### Fixed
- KtLint CLI 0.43 doesn't work with JDK 1.8 ([#1271](https://github.com/pinterest/ktlint/issues/1271))

## [0.43.0] - 2021-11-02

### Added
- New `trailing-comma` rule ([#709](https://github.com/pinterest/ktlint/issues/709)) (prior art by [paul-dingemans](https://github.com/paul-dingemans))
### Fixed
- Fix false positive with lambda argument and call chain (`indent`) ([#1202](https://github.com/pinterest/ktlint/issues/1202))
- Fix trailing spaces not formatted inside block comments (`no-trailing-spaces`) ([#1197](https://github.com/pinterest/ktlint/issues/1197))
- Do not check for `.idea` folder presence when using `applyToIDEA` globally ([#1186](https://github.com/pinterest/ktlint/issues/1186))
- Remove spaces before primary constructor (`paren-spacing`) ([#1207](https://github.com/pinterest/ktlint/issues/1207))
- Fix false positive for delegated properties with a lambda argument (`indent`) ([#1210](https://github.com/pinterest/ktlint/issues/1210))
- (REVERTED in Ktlint 0.45.0) Remove unnecessary wildcard imports (`no-unused-imports`) ([#1256](https://github.com/pinterest/ktlint/issues/1256))
- Fix indentation of KDoc comment when using tab indentation style (`indent`) ([#850](https://github.com/pinterest/ktlint/issues/850))
### Changed
- Support absolute paths for globs ([#1131](https://github.com/pinterest/ktlint/issues/1131))
- Fix regression from 0.41 with argument list wrapping after dot qualified expression (`argument-list-wrapping`)([#1159](https://github.com/pinterest/ktlint/issues/1159))
- Update Gradle to `7.2` version
- Update Gradle shadow plugin to `7.1` version
- Update Kotlin version to `1.5.31` version. Default Kotlin API version was changed to `1.4`!

... (rest of file unchanged)