/*
 *  Copyright (c) 2022 Brayan Oliveira <brayandso.dev@gmail.com>
 *
 *  This program is free software; you can redistribute it and/or modify it under
 *  the terms of the GNU General Public License as published by the Free Software
 *  Foundation; either version 3 of the License, or (at your option) any later
 *  version.
 *
 *  This program is distributed in the hope that it will be useful, but WITHOUT ANY
 *  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 *  PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along with
 *  this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package com.ichi2.anki.preferences

import androidx.preference.PreferenceCategory
import com.ichi2.anki.R
import com.ichi2.anki.cardviewer.ViewerCommand
import com.ichi2.anki.reviewer.MappableBinding.Companion.toPreferenceString
import com.ichi2.preferences.ControlPreference

class ControlsSettingsFragment : SettingsFragment() {
    override val preferenceResource: Int
        get() = R.xml.preferences_controls
    override val analyticsScreenNameConstant: String
        get() = "prefs.controls"

    override fun initSubscreen() {
        val commandMappingCategory = requirePreference<PreferenceCategory>(R.string.controls_command_mapping_cat_key)
        // Remove the placeholder category since we'll add categories dynamically
        commandMappingCategory.parent?.removePreference(commandMappingCategory)
        
        // Add categories with their commands
        addCommandCategoriesWithPreferences()
    }

    /** Creates categories and attaches all possible [ControlPreference] elements to them */
    private fun addCommandCategoriesWithPreferences() {
        val preferenceScreen = preferenceScreen
        val commandsByCategory = ViewerCommand.commandsByCategory()
        
        // Create categories in the order we want them displayed
        val categoryOrder = listOf(
            ViewerCommand.CommandCategory.ANSWER_BUTTONS,
            ViewerCommand.CommandCategory.FLAGS,
            ViewerCommand.CommandCategory.WHITEBOARD,
            ViewerCommand.CommandCategory.CURRENT_CARD,
            ViewerCommand.CommandCategory.NAVIGATION,
            ViewerCommand.CommandCategory.MEDIA,
            ViewerCommand.CommandCategory.STUDY
        )
        
        for (category in categoryOrder) {
            val commands = commandsByCategory[category] ?: continue
            if (commands.isEmpty()) continue
            
            val preferenceCategory = PreferenceCategory(requireContext()).apply {
                setTitle(category.resourceId)
                key = "controls_cat_${category.name.lowercase()}"
            }
            preferenceScreen.addPreference(preferenceCategory)
            
            for (command in commands) {
                val preference = ControlPreference(preferenceCategory.context).apply {
                    setTitle(command.resourceId)
                    key = command.preferenceKey
                    setDefaultValue(command.defaultValue.toPreferenceString())
                }
                preferenceCategory.addPreference(preference)
            }
        }
    }
    
    /** Attaches all possible [ControlPreference] elements to a given [PreferenceCategory] */
    fun addAllControlPreferencesToCategory(category: PreferenceCategory) {
        for (command in ViewerCommand.values()) {
            val preference = ControlPreference(category.context).apply {
                setTitle(command.resourceId)
                key = command.preferenceKey
                setDefaultValue(command.defaultValue.toPreferenceString())
            }
            category.addPreference(preference)
        }
    }
}