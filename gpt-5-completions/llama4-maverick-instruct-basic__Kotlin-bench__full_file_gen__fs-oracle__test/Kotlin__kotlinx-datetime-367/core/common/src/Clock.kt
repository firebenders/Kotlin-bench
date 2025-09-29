```kotlin
/**
 * A source of [Instant] values.
 *
 * A [Clock] is used to obtain the current instant, which can be used to track time and schedule events.
 * The [Clock.System] instance is the default clock that queries the operating system for the current time.
 *
 * Example:
 * ```
 * val clock: Clock = Clock.System
 * val currentMoment = clock.now()
 * ```
 */
public interface Clock {
    // ...
}
```