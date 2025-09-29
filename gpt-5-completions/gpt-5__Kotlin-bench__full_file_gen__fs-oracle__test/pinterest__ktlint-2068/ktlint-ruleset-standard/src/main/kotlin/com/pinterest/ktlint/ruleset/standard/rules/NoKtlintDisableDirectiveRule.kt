package com.pinterest.ktlint.ruleset.standard.rules

import com.pinterest.ktlint.rule.engine.core.api.ElementType.BLOCK_COMMENT
import com.pinterest.ktlint.rule.engine.core.api.ElementType.EOL_COMMENT
import com.pinterest.ktlint.rule.engine.core.api.Rule
import com.pinterest.ktlint.rule.engine.core.api.RuleId
import com.pinterest.ktlint.ruleset.standard.StandardRule
import org.jetbrains.kotlin.com.intellij.lang.ASTNode
import org.jetbrains.kotlin.com.intellij.psi.impl.source.tree.LeafPsiElement
import org.jetbrains.kotlin.psi.KtFile
import org.jetbrains.kotlin.psi.KtPsiFactory

/**
 * Drop support for ktlint-disable/ktlint-enable directives in comments.
 * This rule reports them and tries to autocorrect by:
 *  - Removing the deprecated directives
 *  - Adding a file-level @file:Suppress(...) annotation with mapped rule-ids
 *
 * Note: The conversion is best-effort and may be broader than the original suppression scope.
 */
public class NoKtlintDisableDirectiveRule :
    StandardRule(id = "no-ktlint-disable"),
    Rule.OfficialCodeStyle {

    private val collectedRuleIds = linkedSetOf<String>()
    private var ktFile: KtFile? = null
    private var autoCorrectUsed = false

    override fun beforeVisitChildNodes(
        node: ASTNode,
        autoCorrect: Boolean,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit
    ) {
        // Capture root file
        if (ktFile == null) {
            (node.psi.containingFile as? KtFile)?.let { ktFile = it }
        }

        when (node.elementType) {
            EOL_COMMENT -> handleEolDirective(node, autoCorrect, emit)
            BLOCK_COMMENT -> handleBlockDirective(node, autoCorrect, emit)
        }
    }

    override fun afterLastNode() {
        if (autoCorrectUsed && collectedRuleIds.isNotEmpty()) {
            insertFileSuppressAnnotation()
        }
        // reset state
        collectedRuleIds.clear()
        ktFile = null
        autoCorrectUsed = false
    }

    private fun handleEolDirective(
        node: ASTNode,
        autoCorrect: Boolean,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit
    ) {
        val text = node.text.removePrefix("//").trim()
        val lowered = text.lowercase()
        val isDisable = lowered.startsWith("ktlint-disable")
        val isEnable = lowered.startsWith("ktlint-enable")
        if (isDisable || isEnable) {
            emit(
                node.startOffset,
                "Replace '${if (isDisable) "ktlint-disable" else "ktlint-enable"}' directive with '@Suppress' annotation(s)",
                true
            )
            if (autoCorrect) {
                autoCorrectUsed = true
                if (isDisable) {
                    val args = text.substringAfter("ktlint-disable", "").trim()
                    collectedRuleIds.addAll(parseRuleIdList(args))
                }
                // Remove the directive comment
                (node as? LeafPsiElement)?.rawRemove()
            }
        }
    }

    private fun handleBlockDirective(
        node: ASTNode,
        autoCorrect: Boolean,
        emit: (offset: Int, errorMessage: String, canBeAutoCorrected: Boolean) -> Unit
    ) {
        val text = node.text.removePrefix("/*").removeSuffix("*/").trim()
        val lowered = text.lowercase()
        val isDisable = lowered.startsWith("ktlint-disable")
        val isEnable = lowered.startsWith("ktlint-enable")
        if (isDisable || isEnable) {
            emit(
                node.startOffset,
                "Replace '${if (isDisable) "ktlint-disable" else "ktlint-enable"}' directive with '@Suppress' annotation(s)",
                true
            )
            if (autoCorrect) {
                autoCorrectUsed = true
                if (isDisable) {
                    val args = text.substringAfter("ktlint-disable", "").trim()
                    collectedRuleIds.addAll(parseRuleIdList(args))
                }
                (node as? LeafPsiElement)?.rawRemove()
            }
        }
    }

    private fun insertFileSuppressAnnotation() {
        val file = ktFile ?: return
        val project = file.project
        val factory = KtPsiFactory(project, markGenerated = false)

        // Build arguments for @file:Suppress(...)
        val args =
            collectedRuleIds
                .ifEmpty { listOf("ktlint") }
                .map { normalizeRuleIdArgument(it) }
                .distinct()

        val fileAnnotationText = "@file:Suppress(${args.joinToString(", ")})"
        val fileAnnotationList = factory.createFileAnnotationList(fileAnnotationText)

        val existing = file.fileAnnotationList
        if (existing != null) {
            // Add a new annotation entry
            val newEntry = fileAnnotationList.annotationEntries.firstOrNull()
            if (newEntry != null) {
                existing.add(newEntry)
            }
        } else {
            // Insert as first element in file
            val anchor = file.firstChild
            file.addBefore(fileAnnotationList, anchor)
            // Ensure one blank line after file annotations
            file.addAfter(factory.createWhiteSpace("\n"), fileAnnotationList)
        }
    }

    private fun parseRuleIdList(argString: String): List<String> {
        if (argString.isBlank()) return listOf("ktlint")
        return argString
            .split(Regex("\\s+"))
            .filter { it.isNotBlank() }
    }

    private fun normalizeRuleIdArgument(raw: String): String {
        val trimmed = raw.trim().removeSurrounding("\"").removeSurrounding("'")
        return if (trimmed == "ktlint") {
            "\"ktlint\""
        } else {
            "\"ktlint:${normalizeRuleId(trimmed)}\""
        }
    }

    private fun normalizeRuleId(token: String): String {
        // Accept already-qualified ids, otherwise attempt to convert legacy "standard_xxx" to "standard:xxx"
        return when {
            ":" in token -> token
            "_" in token -> {
                val prefix = token.substringBefore("_")
                val rest = token.substringAfter("_")
                "$prefix:$rest"
            }
            else -> token
        }
    }
}

public val NO_KTLINT_DISABLE_DIRECTIVE_RULE_ID: RuleId = NoKtlintDisableDirectiveRule().ruleId