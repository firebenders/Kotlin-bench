package org.wordpress.android.ui.bloggingprompts

import org.wordpress.android.models.ReaderTag
import org.wordpress.android.models.ReaderTagType
import org.wordpress.android.ui.reader.utils.ReaderUtilsWrapper
import javax.inject.Inject

class BloggingPromptsPostTagProvider @Inject constructor(
    private val readerUtilsWrapper: ReaderUtilsWrapper,
) {
    fun promptIdTag(
        tagUrl: String
    ): String {
        // Extract the tag from the URL
        val extractedTag = readerUtilsWrapper.getTagFromTagUrl(tagUrl)
        
        // If we get a valid tag, use it directly
        // This ensures each daily prompt gets its unique tag (e.g., dailyprompt-2024-01-15)
        if (extractedTag.isNotBlank()) {
            return extractedTag
        }
        
        // Try to extract daily prompt tag from the URL pattern
        // Handle URLs like /tag/dailyprompt-YYYY-MM-DD/
        val dailyPromptPattern = Regex("dailyprompt-\\d{4}-\\d{2}-\\d{2}")
        val matchResult = dailyPromptPattern.find(tagUrl)
        if (matchResult != null) {
            return matchResult.value
        }
        
        // Only fall back to generic tag if we can't extract anything specific
        return BLOGGING_PROMPT_TAG
    }

    fun promptIdSearchReaderTag(
        tagUrl: String
    ): ReaderTag {
        val tagName = promptIdTag(tagUrl)
        // Create a unique ReaderTag for each prompt to ensure proper pagination
        return ReaderTag(
            tagName,
            tagName,
            tagName,
            null,
            ReaderTagType.FOLLOWED
        )
    }

    companion object {
        const val BLOGGING_PROMPT_TAG = "dailyprompt"
        const val BLOGANUARY_TAG = "bloganuary"
    }
}