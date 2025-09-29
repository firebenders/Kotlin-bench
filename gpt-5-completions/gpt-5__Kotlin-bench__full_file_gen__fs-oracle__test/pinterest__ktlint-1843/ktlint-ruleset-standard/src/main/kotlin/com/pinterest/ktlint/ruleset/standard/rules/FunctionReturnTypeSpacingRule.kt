package com.pinterest.ktlint.ruleset.standard.rules

import com.pinterest.ktlint.rule.engine.core.api.ElementType.COLON
import com.pinterest.ktlint.rule.engine.core.api.ElementType.FUN
import com.pinterest.ktlint.rule.engine.core.api.ElementType.WHITE_SPACE
import com.pinterest.ktlint.rule.engine.core.api.Rule
import com.pinterest.ktlint.rule.engine.core.api.RuleId
import com.pinterest.ktlint.rule.engine.core.api.nextLeaf
import com.pinterest.ktlint.rule.engine.core.api.prevLeaf
import com.pinterest.ktlint.rule.engine.core.api.upsertWhitespaceAfterMe
import com.pinterest.ktlint.ruleset.standard.StandardRule
import org.jetbrains.kotlin.com.intellij.lang.ASTNode

public class FunctionReturnTypeSpacingRule :
    StandardRule("function-return-type-spacing"),
    Rule.Experimental {
    override fun beforeVisitChildNodes(
        node: ASTNode,
        autoCorrect: Boolean,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
    ) {
        node.firstChildNode
        node
            .takeIf { node.elementType == FUN }
            ?.let { node.findChildByType(COLON) }
            ?.let { colonNode ->
                removeWhiteSpaceBetweenClosingParenthesisAndColon(colonNode, emit, autoCorrect)
                fixWhiteSpaceBetweenColonAndReturnType(colonNode, emit, autoCorrect)
            }
    }

    private fun removeWhiteSpaceBetweenClosingParenthesisAndColon(
        node: ASTNode,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
        autoCorrect: Boolean,
    ) {
        require(node.elementType == COLON)
        node
            .prevLeaf()
            ?.takeIf { it.elementType == WHITE_SPACE }
            ?.let { whitespaceBeforeColonNode ->
                emit(whitespaceBeforeColonNode.startOffset, "Unexpected whitespace", true)
                if (autoCorrect) {
                    whitespaceBeforeColonNode.treeParent?.removeChild(whitespaceBeforeColonNode)
                }
            }
    }

    private fun fixWhiteSpaceBetweenColonAndReturnType(
        node: ASTNode,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
        autoCorrect: Boolean,
    ) {
        require(node.elementType == COLON)

        val nextLeaf = node.nextLeaf()
        if (nextLeaf?.elementType == WHITE_SPACE) {
            val wsText = nextLeaf.text
            // Honor wrapping and max line length: if there's a newline after the colon, keep it as-is
            if (wsText.contains("\n")) {
                return
            }
            if (wsText != " ") {
                emit(node.startOffset, "Single space expected between colon and return type", true)
                if (autoCorrect) {
                    node.upsertWhitespaceAfterMe(" ")
                }
            }
        } else {
            // No whitespace found after colon: insert a single space
            emit(node.startOffset, "Single space expected between colon and return type", true)
            if (autoCorrect) {
                node.upsertWhitespaceAfterMe(" ")
            }
        }
    }
}

public val FUNCTION_RETURN_TYPE_SPACING_RULE_ID: RuleId = FunctionReturnTypeSpacingRule().ruleId