```kotlin
fun Context.getViewerAssetLoader(domain: String): WebViewAssetLoader {
    val mediaDir = CollectionHelper.getMediaDirectory(this)
    return WebViewAssetLoader.Builder()
        .setHttpAllowed(true)
        .setDomain(domain)
        .addPathHandler("/") { path: String ->
            try {
                val file = File(mediaDir, path)
                val inputStream = FileInputStream(file)
                WebResourceResponse(guessMimeType(path), null, inputStream)
            } catch (e: Exception) {
                Timber.d("File not found: %s", path)
                null
            }
        }
        .build()
}
```