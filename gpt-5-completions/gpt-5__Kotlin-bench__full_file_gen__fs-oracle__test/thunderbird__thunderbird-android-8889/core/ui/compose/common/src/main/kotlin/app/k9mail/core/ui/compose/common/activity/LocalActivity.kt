package app.k9mail.core.ui.compose.common.activity

import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionContext

fun ComponentActivity.setActivityContent(
    parent: CompositionContext? = null,
    content: @Composable () -> Unit,
) {
    setContent(parent, content)
}