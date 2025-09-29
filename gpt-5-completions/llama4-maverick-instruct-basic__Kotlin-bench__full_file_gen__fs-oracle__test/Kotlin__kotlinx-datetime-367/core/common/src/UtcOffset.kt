```kotlin
/**
 * An offset from UTC.
 *
 * Examples of these values:
 * - `Z`, an offset of zero;
 * - `+05`, plus five hours;
 * - `-02`, minus two hours;
 * - `+03:30`, plus three hours and thirty minutes;
 * - `+01:23:45`, plus one hour, 23 minutes, and 45 seconds.
 *
 * Example:
 * ```
 * val utcOffset = UtcOffset(hours = 3, minutes = 30)
 * val instant = Clock.System.now()
 * val localDateTime = instant.toLocalDateTime(utcOffset.asTimeZone())
 * ```
 */
@Serializable(with = UtcOffsetSerializer::class)
public expect class UtcOffset {
    // ...
}
```