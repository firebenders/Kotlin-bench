## How do I suppress errors for a line/block/file?

!!! tip
    Suppressing a `ktlint` violation is meant primarily as an escape latch for the rare cases when **ktlint** is not able to produce the correct result. Please report any such instances using [GitHub Issues](https://github.com/pinterest/ktlint/issues)).

To disable a specific rule you'll need the rule identifier which is displayed at the end of the lint error.

An error can be suppressed using:

* EOL comments
* @Suppress annotations

=== "[:material-heart:](#) Suppress annotation"

    ```kotlin
    // Suppressing all rules for the entire file
    @file:Suppress("ktlint")

    // Suppress a single rule (with id 'rule-id', defined in rule set with id 'rule-set-id') from the annotated construct
    @Suppress("ktlint:rule-set-id:rule-id")
    class Foo {}

    // Suppress multiple rules for the annotated construct
    @Suppress("ktlint:standard:no-wildcard-imports", "ktlint:custom-rule-set-id:custom-rule-id")
    import foo.*

    // Suppress all rules for the annotated construct
    @Suppress("ktlint")
    import foo.*
    ```
=== "[:material-heart:](#) EOL comments"

    ```kotlin
    // Suppress a single rule for the commented line
    import foo.* // ktlint-disable standard_no-wildcard-imports

    // Suppress multiple rules for the commented line
    import foo.* // ktlint-disable standard_no-wildcard-imports standard_other-rule-id

    // Suppress all rules for the commented line
    import foo.* // ktlint-disable
    ```
!!! warning
    From a consistency perspective seen, it might be best to **not** mix the (EOL) comment style with the annotation style in the same project.