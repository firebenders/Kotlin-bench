```kotlin
/**
 * The representation of a specific civil date and time without a reference to a particular time zone.
 *
 * This class does not describe specific *moments in time*, which are represented as [Instant] values.
 * Instead, its instances can be thought of as clock readings, something that an observer in a particular time zone
 * could witness.
 * For example, `2020-08-30T18:43` is not a *moment in time*, since someone in Berlin and someone in Tokyo would witness
 * this on their clocks at different times.
 *
 * The main purpose of this class is to provide human-readable representations of [Instant] values, or to transfer them
 * as data.
 *
 * Example:
 * ```
 * val localDateTime = LocalDateTime(2020, 8, 30, 18, 43)
 * val instant = localDateTime.toInstant(TimeZone.UTC)
 * ```
 */
@Serializable(with = LocalDateTimeIso8601Serializer::class)
public expect class LocalDateTime : Comparable<LocalDateTime> {
    // ...
}
```