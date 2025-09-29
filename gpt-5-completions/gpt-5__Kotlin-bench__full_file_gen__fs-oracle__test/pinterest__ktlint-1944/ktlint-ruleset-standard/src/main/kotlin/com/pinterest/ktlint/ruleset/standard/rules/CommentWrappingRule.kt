package com.pinterest.ktlint.ruleset.standard.rules

import com.pinterest.ktlint.rule.engine.core.api.ElementType.BLOCK_COMMENT
import com.pinterest.ktlint.rule.engine.core.api.ElementType.EOL_COMMENT
import com.pinterest.ktlint.rule.engine.core.api.ElementType.LBRACE
import com.pinterest.ktlint.rule.engine.core.api.ElementType.RBRACE
import com.pinterest.ktlint.rule.engine.core.api.ElementType.WHITE_SPACE
import com.pinterest.ktlint.rule.engine.core.api.RuleId
import com.pinterest.ktlint.rule.engine.core.api.editorconfig.INDENT_SIZE_PROPERTY
import com.pinterest.ktlint.rule.engine.core.api.editorconfig.INDENT_STYLE_PROPERTY
import com.pinterest.ktlint.rule.engine.core.api.hasNewLineInClosedRange
import com.pinterest.ktlint.rule.engine.core.api.indent
import com.pinterest.ktlint.rule.engine.core.api.isPartOfComment
import com.pinterest.ktlint.rule.engine.core.api.nextLeaf
import com.pinterest.ktlint.rule.engine.core.api.prevLeaf
import com.pinterest.ktlint.rule.engine.core.api.upsertWhitespaceBeforeMe
import com.pinterest.ktlint.ruleset.standard.StandardRule
import org.jetbrains.kotlin.com.intellij.lang.ASTNode
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.LeafPsiElement
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.PsiCommentImpl

/**
 * Checks external wrapping of block comments. Wrapping inside the comment is not altered. A block comment following another element on the
 * same line is replaced with an EOL comment, if possible.
 */
public class CommentWrappingRule :
    StandardRule(
        id = "comment-wrapping",
        usesEditorConfigProperties =
            setOf(
                INDENT_SIZE_PROPERTY,
                INDENT_STYLE_PROPERTY,
            ),
    ) {
    override fun beforeVisitChildNodes(
        node: ASTNode,
        autoCorrect: Boolean,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
    ) {
        if (node.elementType == BLOCK_COMMENT) {
            // Do not interfere with a single line block comment inside a single line block, e.g.:
            //     val foo = { /* no-op */ }
            if (node.isSingleLineBlockCommentInsideSingleLineBlock()) {
                return
            }

            val nonIndentLeafOnSameLinePrecedingBlockComment =
                node
                    .prevLeaf()
                    ?.takeIf { isNonIndentLeafOnSameLine(it) }
            val nonIndentLeafOnSameLineFollowingBlockComment =
                node
                    .nextLeaf()
                    ?.takeIf { isNonIndentLeafOnSameLine(it) }

            if (nonIndentLeafOnSameLinePrecedingBlockComment != null &&
                nonIndentLeafOnSameLineFollowingBlockComment != null
            ) {
                if (hasNewLineInClosedRange(nonIndentLeafOnSameLinePrecedingBlockComment, nonIndentLeafOnSameLineFollowingBlockComment)) {
                    // Do not try to fix constructs like below:
                    //    val foo = "foo" /*
                    //    some comment
                    //    */ val bar = "bar"
                    emit(
                        node.startOffset,
                        "A block comment starting on same line as another element and ending on another line before another element is " +
                            "disallowed",
                        false,
                    )
                } else {
                    // Do not try to fix constructs like below:
                    //    val foo /* some comment */ = "foo"
                    emit(
                        node.startOffset,
                        "A block comment in between other elements on the same line is disallowed",
                        false,
                    )
                }
                return
            }

            nonIndentLeafOnSameLinePrecedingBlockComment
                ?.precedesBlockCommentOnSameLine(node, emit, autoCorrect)

            nonIndentLeafOnSameLineFollowingBlockComment
                ?.followsBlockCommentOnSameLine(node, emit, autoCorrect)
        }
    }

    private fun ASTNode.isSingleLineBlockCommentInsideSingleLineBlock(): Boolean {
        // Only consider single line block comments
        if (this.textContains('\n')) return false

        // Find the previous significant leaf on the same line
        var prev = this.prevLeaf()
        while (prev != null && !(prev.elementType == WHITE_SPACE && prev.textContains('\n'))) {
            if (!prev.isPartOfComment() && prev.elementType != WHITE_SPACE) {
                // Previous non-whitespace/comment leaf is found
                if (prev.elementType != LBRACE) return false

                // Find the next significant leaf on the same line
                var next = this.nextLeaf()
                while (next != null && !(next.elementType == WHITE_SPACE && next.textContains('\n'))) {
                    if (!next.isPartOfComment() && next.elementType != WHITE_SPACE) {
                        return next.elementType == RBRACE
                    }
                    next = next.nextLeaf()
                }
                return false
            }
            prev = prev.prevLeaf()
        }
        return false
    }

    private fun ASTNode.precedesBlockCommentOnSameLine(
        blockCommentNode: ASTNode,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
        autoCorrect: Boolean,
    ) {
        val leafAfterBlockComment = blockCommentNode.nextLeaf()
        if (!blockCommentNode.textContains('\n') && leafAfterBlockComment.isLastElementOnLine()) {
            emit(
                startOffset,
                "A single line block comment after a code element on the same line must be replaced with an EOL comment",
                true,
            )
            if (autoCorrect) {
                blockCommentNode.replaceWithEndOfLineComment()
            }
        } else {
            // It can not be autocorrected as it might depend on the situation and code style what is preferred.
            emit(
                blockCommentNode.startOffset,
                "A block comment after any other element on the same line must be separated by a new line",
                false,
            )
        }
    }

    private fun ASTNode.replaceWithEndOfLineComment() {
        val content = text.removeSurrounding("/*", "*/").trim()
        val eolComment = PsiCommentImpl(EOL_COMMENT, "// $content")
        (this as LeafPsiElement).rawInsertBeforeMe(eolComment)
        rawRemove()
    }

    private fun ASTNode.followsBlockCommentOnSameLine(
        blockCommentNode: ASTNode,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit,
        autoCorrect: Boolean,
    ) {
        emit(startOffset, "A block comment may not be followed by any other element on that same line", true)
        if (autoCorrect) {
            this.upsertWhitespaceBeforeMe(blockCommentNode.indent())
        }
    }

    private fun isNonIndentLeafOnSameLine(it: ASTNode) = it.elementType != WHITE_SPACE || !it.textContains('\n')

    private fun ASTNode?.isLastElementOnLine() = this == null || (elementType == WHITE_SPACE && textContains('\n'))
}

public val COMMENT_WRAPPING_RULE_ID: RuleId = CommentWrappingRule().ruleId