```kotlin
/**
 * A time zone, provides the conversion between [Instant] and [LocalDateTime] values
 * using a collection of rules specifying which [LocalDateTime] value corresponds to each [Instant].
 *
 * Example:
 * ```
 * val timeZone = TimeZone.of("Europe/Berlin")
 * val instant = Clock.System.now()
 * val localDateTime = instant.toLocalDateTime(timeZone)
 * ```
 */
@Serializable(with = TimeZoneSerializer::class)
public expect open class TimeZone {
    // ...
}
```