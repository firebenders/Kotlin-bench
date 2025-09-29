package com.pinterest.ktlint.rule.engine.internal

import com.pinterest.ktlint.logger.api.initKtLintKLogger
import com.pinterest.ktlint.rule.engine.core.api.RuleId
import com.pinterest.ktlint.rule.engine.core.api.editorconfig.EditorConfig
import com.pinterest.ktlint.rule.engine.core.util.safeAs
import mu.KotlinLogging
import org.jetbrains.kotlin.com.intellij.lang.ASTNode
import org.jetbrains.kotlin.com.intellij.psi.PsiElement
import org.jetbrains.kotlin.psi.KtAnnotated
import org.jetbrains.kotlin.psi.KtAnnotationEntry
import org.jetbrains.kotlin.psi.ValueArgument
import org.jetbrains.kotlin.psi.psiUtil.endOffset
import org.jetbrains.kotlin.psi.psiUtil.startOffset

/**
 * Detects if given `ruleId` at given `offset` is suppressed.
 */
internal typealias SuppressionLocator = (offset: Int, ruleId: RuleId) -> Boolean

internal object SuppressionLocatorBuilder {
    /**
     * No suppression is detected. Always returns `false`.
     */
    private val NO_SUPPRESSION: SuppressionLocator = { _, _ -> false }

    private val LOGGER = KotlinLogging.logger {}.initKtLintKLogger()

    /**
     * Mapping of non-ktlint annotations to ktlint-annotation so that ktlint rules will be suppressed automatically
     * when specific non-ktlint annotations are found. The prevents that developers have to specify multiple annotations
     * for the same violation.
     */
    private val SUPPRESS_ANNOTATION_RULE_MAP =
        mapOf(
            // It would have been nice if the official rule id's as defined in the Rules themselves could have been used here. But that would
            // introduce a circular dependency between the ktlint-rule-engine and the ktlint-ruleset-standard modules.
            "EnumEntryName" to RuleId("standard:enum-entry-name-case"),
            "RemoveCurlyBracesFromTemplate" to RuleId("standard:string-template"),
            "ClassName" to RuleId("standard:class-naming"),
            "FunctionName" to RuleId("standard:function-naming"),
            "PackageName" to RuleId("standard:package-name"),
            "PropertyName" to RuleId("standard:property-naming"),
        )
    private val SUPPRESS_ANNOTATIONS = setOf("Suppress", "SuppressWarnings")
    private val SUPPRESS_ALL_KTLINT_RULES_RULE_ID = RuleId("ktlint:suppress-all-rules")

    /**
     * Builds [SuppressionLocator] for given [rootNode] of AST tree.
     */
    fun buildSuppressedRegionsLocator(
        rootNode: ASTNode,
        editorConfig: EditorConfig,
    ): SuppressionLocator {
        val hintsList = collect(rootNode, FormatterTags.from(editorConfig))
        return if (hintsList.isEmpty()) {
            NO_SUPPRESSION
        } else {
            toSuppressedRegionsLocator(hintsList)
        }
    }

    private fun toSuppressedRegionsLocator(hintsList: List<SuppressionHint>): SuppressionLocator =
        { offset, ruleId ->
            hintsList
                .filter { offset in it.range }
                .any { hint -> hint.disabledRuleIds.isEmpty() || hint.disabledRuleIds.contains(ruleId) }
        }

    private fun collect(
        rootNode: ASTNode,
        formatterTags: FormatterTags,
    ): List<SuppressionHint> {
        val suppressionHints = ArrayList<SuppressionHint>()
        val formatterTagSuppressionHints = mutableListOf<FormatterTagSuppressionHint>()
        
        rootNode.collect { node ->
            // Only handle formatter tags (not ktlint-disable/enable)
            node
                .takeIf { it is org.jetbrains.kotlin.com.intellij.psi.PsiComment }
                ?.createSuppressionHintFromFormatterTag(formatterTags)
                ?.let { formatterTagSuppressionHints.add(it) }

            // Extract all Suppress annotations and create SuppressionHints
            node
                .psi
                .safeAs<KtAnnotated>()
                ?.createSuppressionHintFromAnnotations()
                ?.let { suppressionHints.add(it) }
        }

        return suppressionHints.plus(
            formatterTagSuppressionHints.toSuppressionHints(rootNode),
        )
    }

    private fun ASTNode.collect(block: (node: ASTNode) -> Unit) {
        block(this)
        this
            .getChildren(null)
            .forEach { it.collect(block) }
    }

    private fun ASTNode.createSuppressionHintFromFormatterTag(formatterTags: FormatterTags): FormatterTagSuppressionHint? {
        val trimmedText = text.removePrefix("//").removePrefix("/*").removeSuffix("*/").trim()
        return when {
            trimmedText == formatterTags.formatterTagOff -> {
                FormatterTagSuppressionHint(
                    this,
                    FormatterTagSuppressionHint.Type.BLOCK_START,
                )
            }
            trimmedText == formatterTags.formatterTagOn -> {
                FormatterTagSuppressionHint(
                    this,
                    FormatterTagSuppressionHint.Type.BLOCK_END,
                )
            }
            else -> null
        }
    }

    private fun MutableList<FormatterTagSuppressionHint>.toSuppressionHints(rootNode: ASTNode): MutableList<SuppressionHint> {
        val suppressionHints = mutableListOf<SuppressionHint>()
        val openFormatterTags = mutableListOf<FormatterTagSuppressionHint>()
        
        forEach { formatterTagHint ->
            when (formatterTagHint.type) {
                FormatterTagSuppressionHint.Type.BLOCK_START -> {
                    openFormatterTags.add(formatterTagHint)
                }
                FormatterTagSuppressionHint.Type.BLOCK_END -> {
                    openFormatterTags.removeLastOrNull()?.let { openHint ->
                        suppressionHints.add(
                            SuppressionHint(
                                IntRange(openHint.node.startOffset, formatterTagHint.node.startOffset - 1),
                                emptySet(), // Formatter tags suppress all rules
                            ),
                        )
                    }
                }
            }
        }
        
        // Handle unclosed formatter tags
        suppressionHints.addAll(
            openFormatterTags.map {
                SuppressionHint(
                    IntRange(it.node.startOffset, rootNode.textLength),
                    emptySet(), // Formatter tags suppress all rules
                )
            },
        )
        
        return suppressionHints
    }

    /**
     * Creates [SuppressionHint] from annotations of given [PsiElement]. Returns null if no targetAnnotations are
     * present or no mapping exists between annotations' values and ktlint rules
     */
    private fun PsiElement.createSuppressionHintFromAnnotations(): SuppressionHint? =
        (this as? KtAnnotated)?.let { ktAnnotated ->
            ktAnnotated
                .annotationEntries
                .filter {
                    it.calleeExpression
                        ?.constructorReferenceExpression
                        ?.getReferencedName() in SUPPRESS_ANNOTATIONS
                }.flatMap(KtAnnotationEntry::getValueArguments)
                .mapNotNull { it.toRuleId(SUPPRESS_ANNOTATION_RULE_MAP) }
                .let { suppressedRuleIds ->
                    when {
                        suppressedRuleIds.isEmpty() -> null
                        suppressedRuleIds.contains(SUPPRESS_ALL_KTLINT_RULES_RULE_ID) ->
                            SuppressionHint(
                                IntRange(ktAnnotated.startOffset, ktAnnotated.endOffset),
                                emptySet(),
                            )

                        else ->
                            SuppressionHint(
                                IntRange(ktAnnotated.startOffset, ktAnnotated.endOffset),
                                suppressedRuleIds.toSet(),
                            )
                    }
                }
        }

    private fun ValueArgument.toRuleId(annotationValueToRuleMapping: Map<String, RuleId>): RuleId? =
        getArgumentExpression()
            ?.text
            ?.removeSurrounding("\"")
            ?.let { argumentExpressionText ->
                when {
                    argumentExpressionText == "ktlint" -> {
                        // Disable all rules
                        SUPPRESS_ALL_KTLINT_RULES_RULE_ID
                    }
                    argumentExpressionText.startsWith("ktlint:") -> {
                        // Disable specific rule
                        argumentExpressionText
                            .removePrefix("ktlint:")
                            .let { createRuleIdOrNull(it) }
                    }
                    else -> {
                        // Disable specific rule if the annotation value is mapped to a specific rule
                        annotationValueToRuleMapping[argumentExpressionText]
                    }
                }
            }

    private fun createRuleIdOrNull(ruleId: String): RuleId? =
        try {
            // For backwards compatibility the suppression hints have to be prefixed with the standard rule set id when the rule id is
            // not prefixed with any rule set id.
            RuleId
                .prefixWithStandardRuleSetIdWhenMissing(ruleId)
                .let { RuleId(it) }
        } catch (illegalArgumentException: IllegalArgumentException) {
            // Ktlint should not terminate with an exception in case the code being scanned contains a suppression for a non-existing rule.
            // Instead, a warning should be printed and the invalid reference is to be ignored. The original ruleId is printed in the
            // warning message so that user will not go searching for the fully qualified rule id while the code actually contained an
            // unqualified ruleId.
            LOGGER.warn {
                """
                Can not suppress rule with id '$ruleId'. Please check and fix references to this rule in your code.
                    Underlying cause: ${illegalArgumentException.message}
                """.trimIndent()
            }
            null
        }

    /**
     * @param range zero-based range of lines where lint errors should be suppressed
     * @param disabledRuleIds empty set means "all"
     */
    private data class SuppressionHint(
        val range: IntRange,
        val disabledRuleIds: Set<RuleId> = emptySet(),
    )

    private data class FormatterTagSuppressionHint(
        val node: ASTNode,
        val type: Type,
    ) {
        enum class Type {
            BLOCK_START,
            BLOCK_END,
        }
    }
}