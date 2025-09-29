```kotlin
private fun setupWebView(savedInstanceState: Bundle?) {
    CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
    with(webView) {
        webViewClient = onCreateWebViewClient(savedInstanceState)
        webChromeClient = onCreateWebChromeClient()
        scrollBarStyle = View.SCROLLBARS_OUTSIDE_OVERLAY
        with(settings) {
            javaScriptEnabled = true
            loadWithOverviewMode = true
            builtInZoomControls = true
            displayZoomControls = false
            allowFileAccess = true
            allowFileAccessFromFileURLs = true
            allowUniversalAccessFromFileURLs = true
            domStorageEnabled = true
        }
        // ...
    }
    // ...
}
```