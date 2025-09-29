// Remove or comment out the custom LocalActivity
// val LocalActivity = staticCompositionLocalOf<ComponentActivity> {
//     error("No value for LocalActivity provided")
// }

// fun ComponentActivity.setActivityContent(
//     parent: CompositionContext? = null,
//     content: @Composable () -> Unit,
// ) {
//     setContent(parent) {
//         CompositionLocalProvider(LocalActivity provides this, content = content)
//     }
// }