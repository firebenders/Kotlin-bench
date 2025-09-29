```kotlin
package com.pinterest.ktlint.rule.engine.core.api

import com.pinterest.ktlint.rule.engine.core.api.ElementType.REGULAR_STRING_PART
import com.pinterest.ktlint.rule.engine.core.api.ElementType.STRING_TEMPLATE
import com.pinterest.ktlint.rule.engine.core.api.ElementType.VAL_KEYWORD
import com.pinterest.ktlint.rule.engine.core.api.ElementType.VARARG_KEYWORD
import com.pinterest.ktlint.rule.engine.core.api.ElementType.VAR_KEYWORD
import com.pinterest.ktlint.rule.engine.core.api.ElementType.WHITE_SPACE
import org.jetbrains.kotlin.com.intellij.lang.ASTNode
import org.jetbrains.kotlin.com.intellij.psi.PsiComment
import org.jetbrains.kotlin.com.intellij.psi.PsiElement
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.CompositeElement
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.LeafElement
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.PsiWhiteSpaceImpl
import org.jetbrains.kotlin.com.intellij.psi.tree.IElementType
import org.jetbrains.kotlin.psi.psiUtil.leaves
import org.jetbrains.kotlin.util.prefixIfNot
import org.jetbrains.kotlin.utils.addToStdlib.applyIf
import kotlin.reflect.KClass

// ...

public fun ASTNode.upsertWhitespaceBeforeMeAsSibling(text: String) {
    require(this is LeafElement)

    val previousLeaf = prevLeaf()
    if (previousLeaf != null && previousLeaf.elementType == WHITE_SPACE) {
        previousLeaf.replaceWhitespaceWith(text)
    } else {
        val newWhiteSpace = PsiWhiteSpaceImpl(text)
        (treeParent as CompositeElement).addChild(newWhiteSpace, this)
    }
}

// ...
```