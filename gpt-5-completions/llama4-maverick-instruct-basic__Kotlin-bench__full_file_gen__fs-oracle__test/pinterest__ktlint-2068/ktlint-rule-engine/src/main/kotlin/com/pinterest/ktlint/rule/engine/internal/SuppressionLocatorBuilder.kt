private fun ASTNode.createSuppressionHintFromEolComment(formatterTags: FormatterTags): CommentSuppressionHint? =
    text
        .removePrefix("//")
        .trim()
        .split(" ")
        .takeIf { it.isNotEmpty() }
        ?.takeIf { it[0] == formatterTags.formatterTagOff }
        ?.let { parts ->
            CommentSuppressionHint(
                this,
                HashSet(parts.tailToRuleIds()),
                EOL,
            )
        }

private fun ASTNode.createSuppressionHintFromBlockComment(formatterTags: FormatterTags): CommentSuppressionHint? =
    text
        .removePrefix("/*")
        .removeSuffix("*/")
        .trim()
        .split(" ")
        .takeIf { it.isNotEmpty() }
        ?.let { parts ->
            if (parts[0] == formatterTags.formatterTagOff) {
                CommentSuppressionHint(
                    this,
                    HashSet(parts.tailToRuleIds()),
                    BLOCK_START,
                )
            } else if (parts[0] == formatterTags.formatterTagOn) {
                CommentSuppressionHint(
                    this,
                    HashSet(parts.tailToRuleIds()),
                    BLOCK_END,
                )
            } else {
                null
            }
        }