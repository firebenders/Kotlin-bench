# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## Unreleased

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

### Removed

### Fixed

* Fix false positive in `parameter-list-wrapping` when parameter list is part of a call expression which is not wrapped on a separate line ([#2061](https://github.com/pinterest/ktlint/issues/2061))

### Changed