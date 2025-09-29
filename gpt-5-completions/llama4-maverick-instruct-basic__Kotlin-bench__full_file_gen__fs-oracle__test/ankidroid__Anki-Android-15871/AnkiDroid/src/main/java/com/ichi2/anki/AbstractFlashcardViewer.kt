```kotlin
protected open fun createWebView(): WebView {
    val assetLoader = getViewerAssetLoader(webviewDomain)
    val webView: WebView = MyWebView(this).apply {
        scrollBarStyle = View.SCROLLBARS_OUTSIDE_OVERLAY
        with(settings) {
            displayZoomControls = false
            builtInZoomControls = true
            setSupportZoom(true)
            loadWithOverviewMode = true
            javaScriptEnabled = true
            allowFileAccess = true
            allowFileAccessFromFileURLs = true
            allowUniversalAccessFromFileURLs = true
            // enable dom storage so that sessionStorage & localStorage can be used in webview
            domStorageEnabled = true
        }
        // ...
    }
    // ...
}
```