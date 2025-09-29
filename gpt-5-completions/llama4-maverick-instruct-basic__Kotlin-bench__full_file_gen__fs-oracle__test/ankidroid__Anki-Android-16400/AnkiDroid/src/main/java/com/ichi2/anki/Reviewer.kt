```kotlin
// ...
private lateinit var autoAdvance: AutomaticAnswer
// ...

override fun onCollectionLoaded(col: Collection) {
    super.onCollectionLoaded(col)
    // ...
    autoAdvance = AutomaticAnswer.createInstance(this, preferences, col)
    // ...
}

override fun executeCommand(which: ViewerCommand, fromGesture: Gesture?): Boolean {
    when (which) {
        // ...
        ViewerCommand.TOGGLE_AUTO_ADVANCE -> {
            autoAdvance.toggle()
            refreshActionBar()
            return true
        }
        // ...
    }
}

override fun onCreateOptionsMenu(menu: Menu): Boolean {
    // ...
    menu.findItem(R.id.action_toggle_auto_advance).apply {
        val autoAdvanceEnabled = autoAdvance.isEnabled()
        title = getString(if (autoAdvanceEnabled) R.string.disable_auto_advance else R.string.enable_auto_advance)
        isVisible = true
    }
    // ...
}
```