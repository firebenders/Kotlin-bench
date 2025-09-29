class ControlsSettingsFragment : SettingsFragment() {
    override fun initSubscreen() {
        val context = requireContext()
        val commandMappingCategory = requirePreference<PreferenceCategory>(R.string.controls_command_mapping_cat_key)

        val categories = ViewerCommandCategory.values().associateWith { category ->
            PreferenceCategory(context).apply {
                title = context.getString(category.displayStringResource)
                key = "category_${category.name}"
            }
        }

        for (command in ViewerCommand.values()) {
            val preference = ControlPreference(commandMappingCategory.context).apply {
                setTitle(command.resourceId)
                key = command.preferenceKey
                setDefaultValue(command.defaultValue.toPreferenceString())
            }
            categories[command.category]?.addPreference(preference) ?: commandMappingCategory.addPreference(preference)
        }

        categories.values.forEach { commandMappingCategory.addPreference(it) }
    }
}