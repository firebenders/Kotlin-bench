```kotlin
/**
 * The date part of [LocalDateTime].
 *
 * This class represents dates without a reference to a particular time zone.
 * As such, these objects may denote different spans of time in different time zones: for someone in Berlin,
 * `2020-08-30` started and ended at different moments from those for someone in Tokyo.
 *
 * The arithmetic on [LocalDate] values is defined independently of the time zone (so `2020-08-30` plus one day
 * is `2020-08-31` everywhere): see various [LocalDate.plus] and [LocalDate.minus] functions, as well
 * as [LocalDate.periodUntil] and various other [*until][LocalDate.daysUntil] functions.
 *
 * Example:
 * ```
 * val today = Clock.System.todayIn(TimeZone.currentSystemDefault())
 * val tomorrow = today.plus(1, DateTimeUnit.DAY)
 * ```
 */
@Serializable(with = LocalDateIso8601Serializer::class)
public expect class LocalDate : Comparable<LocalDate> {
    // ...
}
```