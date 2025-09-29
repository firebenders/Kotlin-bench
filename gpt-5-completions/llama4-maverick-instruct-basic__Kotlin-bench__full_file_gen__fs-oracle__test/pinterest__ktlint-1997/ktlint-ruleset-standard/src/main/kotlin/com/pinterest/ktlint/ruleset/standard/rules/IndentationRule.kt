private fun ASTNode.calculateIndentOfFunctionLiteralParameters() =
    if (codeStyle == ktlint_official || isFirstParameterOfFunctionLiteralPrecededByNewLine()) {
        // val fieldExample =
        //      LongNameClass {
        //              paramA,
        //              paramB,
        //              paramC ->
        //          ClassB(paramA, paramB, paramC)
        //      }
        indentConfig.indent.repeat(2)
    } else {
        // Allow default IntelliJ IDEA formatting:
        // val fieldExample =
        //     LongNameClass { paramA,
        //                     paramB,
        //                     paramC ->
        //         ClassB(paramA, paramB, paramC)
        //     }
        val textBeforeFirstParameter =
            treeParent
                .findChildByType(REFERENCE_EXPRESSION)
                ?.text
                ?.let { "$it {" }
                ?: "{"
        " ".repeat(textBeforeFirstParameter.length + 1)
    }
```

Additionally, we need to update the `CHANGELOG.md` file to reflect the changes made:

```markdown
[start of CHANGELOG.md]
### Fixed
* Store path of file containing a lint violation relative to the location of the baseline file itself ([#1962](https://github.com/pinterest/ktlint/issues/1962))
* Print absolute path of file in lint violations when flag "--relative" is not specified in Ktlint CLI ([#1963](https://github.com/pinterest/ktlint/issues/1963)) 
* Handle parameter `--code-style=android_studio` in Ktlint CLI identical to deprecated parameter `--android` ([#1982](https://github.com/pinterest/ktlint/issues/1982))
* Prevent nullpointer exception (NPE) if class without body is followed by multiple blank lines until end of file `no-consecutive-blank-lines` ([#1987](https://github.com/pinterest/ktlint/issues/1987))
* Allow to 'unset' the `.editorconfig` property `ktlint_function_signature_rule_force_multiline_when_parameter_count_greater_or_equal_than` when using `ktlint_official` code style `function-signature` ([#1977](https://github.com/pinterest/ktlint/issues/1977))
* Prevent nullpointer exception (NPE) if or operator at start of line is followed by dot qualified expression `indent` ([#1993](https://github.com/pinterest/ktlint/issues/1993))
* Restrict indentation of closing quotes to `ktlint_official` code style to keep formatting of other code styles consistent with `0.48.x` and before `indent` ([#1971](https://github.com/pinterest/ktlint/issues/1971))
* Correctly align parameters in lambda in code style `ktlint_official` `indent` ([#1756](https://github.com/pinterest/ktlint/issues/1756))
```
The list of files and their revised contents is as follows:

```example
[start of ktlint-ruleset-standard/src/main/kotlin/com/pinterest/ktlint/ruleset/standard/rules/IndentationRule.kt]
...
private fun ASTNode.calculateIndentOfFunctionLiteralParameters() =
    if (codeStyle == ktlint_official || isFirstParameterOfFunctionLiteralPrecededByNewLine()) {
        // val fieldExample =
        //      LongNameClass {
        //              paramA,
        //              paramB,
        //              paramC ->
        //          ClassB(paramA, paramB, paramC)
        //      }
        indentConfig.indent.repeat(2)
    } else {
        // Allow default IntelliJ IDEA formatting:
        // val fieldExample =
        //     LongNameClass { paramA,
        //                     paramB,
        //                     paramC ->
        //         ClassB(paramA, paramB, paramC)
        //     }
        val textBeforeFirstParameter =
            treeParent
                .findChildByType(REFERENCE_EXPRESSION)
                ?.text
                ?.let { "$it {" }
                ?: "{"
        " ".repeat(textBeforeFirstParameter.length + 1)
    }
...