```kotlin
package com.pinterest.ktlint.ruleset.standard.rules

// ...

private fun fixFunctionBodyExpression(
    node: ASTNode,
    emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
    autoCorrect: Boolean,
    maxLengthRemainingForFirstLineOfBodyExpression: Int,
) {
    // ...

    if (autoCorrect) {
        functionBodyExpressionNodes
            .first()
            .upsertWhitespaceBeforeMeAsSibling(indentConfig.childIndentOf(node))
    }

    // ...
}

// ...
```