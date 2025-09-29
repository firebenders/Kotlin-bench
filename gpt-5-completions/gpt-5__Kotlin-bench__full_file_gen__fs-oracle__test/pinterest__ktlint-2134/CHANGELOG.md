# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

### Removed

### Fixed

* Allow to disable ktlint in `.editorconfig` for a glob ([#2100](https://github.com/pinterest/ktlint/issues/2100))
* Fix wrapping of nested function literals `wrapping` ([#2106](https://github.com/pinterest/ktlint/issues/2106))
* Do not indent class body for classes having a long super type list in code style `ktlint_official` as it is inconsistent compared to other class bodies `indent` [#2115](https://github.com/pinterest/ktlint/issues/2115)
* In code style `ktlint_official` do not indent the closing parenthesis of a PARENTHESIZED expression `indent` [#920](https://github.com/pinterest/ktlint/issues/920) 
* Log message `Format was not able to resolve all violations which (theoretically) can be autocorrected in file ... in 3 consecutive runs of format` is now only displayed in case a new ktlint rule is actually needed. [#2129](https://github.com/pinterest/ktlint/issues/2129)
* Fix wrapping of function signature in case the opening brace of the function body block exceeds the maximum line length. Fix upsert of whitespace into composite nodes. `function-signature` [#2130](https://github.com/pinterest/ktlint/issues/2130)
* Fix spacing around colon in annotations `spacing-around-colon` ([#2093](https://github.com/pinterest/ktlint/issues/2093))
* Fix indent of IS_EXPRESSION, PREFIX_EXPRESSION and POSTFIX_EXPRESSION in case it contains a linebreak `indent` [#2094](https://github.com/pinterest/ktlint/issues/2094)
* Prevent endless formatting loop when a long elvis operator is wrapped: break before the `?:` operator instead of after it in binary expressions `binary-expression-wrapping`

### Changed

* Update dependency gradle to v8.2.1 ([#2122](https://github.com/pinterest/ktlint/pull/2122))
* Update dependency org.codehaus.janino:janino to v3.1.10  ([#2110](https://github.com/pinterest/ktlint/pull/2110))
* Update dependency com.google.jimfs:jimfs to v1.3.0 ([#2112](https://github.com/pinterest/ktlint/pull/2112))

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

At least you should analyse the problems by running your test suits by running ktlint and disabling the extension point. Next you can start with fixing and releasing the updated rules. All rules in this version of ktlint have already been refactored and are not dependent on the extension point anymore. In Ktlint, 7 out of 77 rules needed small and sometimes bigger changes to become independent of the extension point `org.jetbrains.kotlin.com.intellij.treeCopyHandler`. The impact on your custom rules may vary dependent on the way the autocorrect has been implemented. When manipulating `ASTNode`s there seems to be no impact. When, manipulating `PsiElement`s, some functions consistently result in a runtime exception.

... (rest of file unchanged)