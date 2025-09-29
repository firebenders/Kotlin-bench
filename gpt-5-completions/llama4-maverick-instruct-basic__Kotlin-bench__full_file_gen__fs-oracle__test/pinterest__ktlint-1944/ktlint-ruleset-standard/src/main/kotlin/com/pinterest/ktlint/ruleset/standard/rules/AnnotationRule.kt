```kotlin
package com.pinterest.ktlint.ruleset.standard.rules

// ...

public class AnnotationRule :
    StandardRule(
        id = "annotation",
        // ...
    ) {
    // ...

    private fun ASTNode.shouldWrapAnnotations(): Boolean {
        // ...
        return hasAnnotationWithParameter() ||
            hasMultipleAnnotationsOnSameLine() ||
            hasAnnotationBeforeConstructor() ||
            isPartOfSingleLineLambda()
    }

    // ...

    private fun ASTNode.isPartOfSingleLineLambda(): Boolean {
        return treeParent.elementType == ElementType.FUNCTION_LITERAL &&
            treeParent.treeParent.elementType == ElementType.LAMBDA_EXPRESSION &&
            !treeParent.treeParent.textContains('\n')
    }

    // ...
}
```