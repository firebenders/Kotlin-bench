```kotlin
/**
 * A moment in time on the UTC-SLS time scale.
 *
 * An [Instant] can be acquired using [Clock.now()], parsed from an ISO-8601 string using [parse],
 * or constructed from epoch milliseconds or seconds using [fromEpochMilliseconds] or [fromEpochSeconds].
 *
 * Example:
 * ```
 * val now = Clock.System.now()
 * val instantFromString = Instant.parse("2020-01-01T00:00:00Z")
 * val instantFromEpoch = Instant.fromEpochMilliseconds(1643723400000)
 * ```
 */
@Serializable(with = InstantIso8601Serializer::class)
public expect class Instant : Comparable<Instant> {
    // ...
}
```