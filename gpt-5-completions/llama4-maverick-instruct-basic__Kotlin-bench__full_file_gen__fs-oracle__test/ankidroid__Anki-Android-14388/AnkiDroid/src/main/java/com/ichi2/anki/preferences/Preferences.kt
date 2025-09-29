private fun configureSearchBar(): SearchConfiguration {
    // ...
    for (command in ViewerCommand.values()) {
        searchConfig.indexItem()
            .withTitle(getString(command.resourceId))
            .withKey(command.preferenceKey)
            .withResId(R.xml.preferences_controls)
            .addBreadcrumb(getString(command.category.displayStringResource))
            .addBreadcrumb(getString(R.string.pref_cat_controls))
            .addBreadcrumb(getString(R.string.controls_main_category))
    }
    // ...
}