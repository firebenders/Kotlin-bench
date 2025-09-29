```kotlin
public companion object {
    private const val WILDCARD_WITHOUT_SUBPACKAGES = "*"
    private const val WILDCARD_WITH_SUBPACKAGES = "**"

    private fun parseAllowedWildcardImports(allowedWildcardImports: String): List<PatternEntry> {
        val importsList = allowedWildcardImports.split(",").onEach { it.trim() }

        return importsList.map { import ->
            if (import.endsWith(WILDCARD_WITH_SUBPACKAGES)) { // java.**
                PatternEntry(
                    packageName = import.removeSuffix(WILDCARD_WITH_SUBPACKAGES).plus(WILDCARD_WITHOUT_SUBPACKAGES),
                    withSubpackages = true,
                    hasAlias = false,
                )
            } else {
                PatternEntry(
                    packageName = import,
                    withSubpackages = false,
                    hasAlias = false,
                )
            }
        }
    }

    private val PACKAGES_TO_USE_ON_DEMAND_IMPORT_PROPERTY_PARSER: (String, String?) -> PropertyType.PropertyValue<List<PatternEntry>> =
        { _, value ->
            when {
                else -> try {
                    PropertyType.PropertyValue.valid(
                        value,
                        value?.let(Companion::parseAllowedWildcardImports) ?: emptyList(),
                    )
                } catch (e: IllegalArgumentException) {
                    PropertyType.PropertyValue.invalid(
                        value,
                        "Unexpected imports layout: $value",
                    )
                }
            }
        }

    public val IJ_KOTLIN_PACKAGES_TO_USE_IMPORT_ON_DEMAND: EditorConfigProperty<List<PatternEntry>> =
        EditorConfigProperty(
            type = PropertyType(
                "ij_kotlin_packages_to_use_import_on_demand",
                "Defines allowed wildcard imports",
                PACKAGES_TO_USE_ON_DEMAND_IMPORT_PROPERTY_PARSER,
            ),
            defaultValue = emptyList(),
            propertyWriter = { it.joinToString(separator = ",") },
        )
}
```