```markdown
## No wildcard imports

No wildcard imports except imports listed in `.editorconfig` property `ij_kotlin_packages_to_use_import_on_demand`.

!!! warning

    To allow wildcard imports like `java.util.*`, add property below to your `.editorconfig`:
    ```editorconfig
    [*.{kt,kts}]
    ij_kotlin_packages_to_use_import_on_demand = java.util.*
    ```
    To disallow all wildcard imports, set the property to `nothing`:
    ```editorconfig
    [*.{kt,kts}]
    ij_kotlin_packages_to_use_import_on_demand = nothing
    ```

Rule id: `no-wildcard-imports`
```