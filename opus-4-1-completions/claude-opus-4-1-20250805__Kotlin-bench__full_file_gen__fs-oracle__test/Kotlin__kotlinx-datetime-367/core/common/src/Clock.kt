/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

import kotlin.time.*

/**
 * A source of [Instant] values.
 *
 * A `Clock` provides access to the current instant. The most common implementation is [Clock.System],
 * which uses the system's real-time clock. Custom implementations can be created for testing purposes
 * or to provide alternative time sources.
 *
 * ### Obtaining a Clock
 *
 * The primary way to obtain a `Clock` is through [Clock.System]:
 * ```
 * val clock = Clock.System
 * val currentTime = clock.now()
 * ```
 *
 * ### Custom Implementations
 *
 * For testing, you can create a custom `Clock` implementation:
 * ```
 * class TestClock(private var instant: Instant) : Clock {
 *     override fun now(): Instant = instant
 *     fun advance(duration: Duration) { instant += duration }
 * }
 * ```
 *
 * ### Platform Specifics
 *
 * - **JVM**: Uses `java.time.Clock.systemUTC()` internally
 * - **JS**: Uses `Date.now()` internally
 * - **Native**: Uses platform-specific system time APIs
 *
 * ### Time Scale
 *
 * All `Clock` implementations return instants on the UTC-SLS time scale, which handles leap seconds
 * through "smearing" rather than discrete jumps.
 *
 * @see Clock.System for the default system clock
 * @see Instant for the time values returned by clocks
 */
public interface Clock {
    /**
     * Returns the [Instant] corresponding to the current time, according to this clock.
     *
     * The returned instant represents a specific moment in time on the UTC-SLS time scale.
     * Multiple calls to this function may return the same value if called in quick succession,
     * depending on the resolution of the underlying clock implementation.
     *
     * ### Example
     * ```
     * val clock = Clock.System
     * val instant1 = clock.now()
     * // ... some time passes ...
     * val instant2 = clock.now()
     * val elapsed = instant2 - instant1
     * ```
     *
     * @return the current instant according to this clock
     */
    public fun now(): Instant

    /**
     * The system clock instance that queries the operating system's real-time clock.
     *
     * This clock represents "wall clock" time and advances at the same rate as real time.
     * The exact instant returned depends on the system's time settings and may jump backwards
     * or forwards if the system time is adjusted.
     *
     * ### Platform Implementation Details
     *
     * - **JVM**: Equivalent to `java.time.Clock.systemUTC()`
     * - **JS**: Uses JavaScript's `Date.now()`
     * - **Native**: Uses platform-specific system calls (e.g., `clock_gettime` on POSIX systems)
     *
     * ### Example
     * ```
     * val currentTime = Clock.System.now()
     * println("Current time: $currentTime")
     * 
     * // Get today's date in a specific time zone
     * val today = Clock.System.todayIn(TimeZone.currentSystemDefault())
     * ```
     *
     * ### Considerations
     *
     * - The resolution varies by platform (typically milliseconds to nanoseconds)
     * - System time adjustments affect the values returned
     * - For testing, consider injecting a `Clock` interface rather than using `System` directly
     */
    public object System : Clock {
        override fun now(): Instant = @Suppress("DEPRECATION_ERROR") Instant.now()
    }

    public companion object {

    }
}

/**
 * Returns the current date at the given [time zone][timeZone], according to this [Clock].
 *
 * The returned date is calculated by converting the current instant to a local date-time
 * in the specified time zone and extracting the date component.
 *
 * ### Example
 * ```
 * val clock = Clock.System
 * 
 * // Get today's date in UTC
 * val todayUtc = clock.todayIn(TimeZone.UTC)
 * 
 * // Get today's date in the system's default time zone
 * val todayLocal = clock.todayIn(TimeZone.currentSystemDefault())
 * 
 * // These may be different dates if it's near midnight
 * if (todayUtc != todayLocal) {
 *     println("It's already tomorrow in some time zone!")
 * }
 * ```
 *
 * @param timeZone the time zone to use for determining the current date
 * @return the current date in the specified time zone
 * @see TimeZone for available time zones
 * @see LocalDate for the returned date type
 */
public fun Clock.todayIn(timeZone: TimeZone): LocalDate =
    now().toLocalDateTime(timeZone).date

/**
 * Returns a [TimeSource] that uses this [Clock] to mark a time instant and to find the amount of time elapsed since that mark.
 *
 * This allows a `Clock` to be used with Kotlin's duration measurement APIs.
 *
 * ### Example
 * ```
 * val timeSource = Clock.System.asTimeSource()
 * val mark = timeSource.markNow()
 * 
 * // ... perform some operation ...
 * 
 * val elapsed = mark.elapsedNow()
 * println("Operation took: $elapsed")
 * ```
 *
 * @return a TimeSource that uses this Clock for time measurements
 */
@ExperimentalTime
public fun Clock.asTimeSource(): TimeSource.WithComparableMarks = object : TimeSource.WithComparableMarks {
    override fun markNow(): ComparableTimeMark = InstantTimeMark(now(), this@asTimeSource)
}

@ExperimentalTime
private class InstantTimeMark(private val instant: Instant, private val clock: Clock) : ComparableTimeMark {
    override fun elapsedNow(): Duration = saturatingDiff(clock.now(), instant)

    override fun plus(duration: Duration): ComparableTimeMark = InstantTimeMark(instant.saturatingAdd(duration), clock)
    override fun minus(duration: Duration): ComparableTimeMark = InstantTimeMark(instant.saturatingAdd(-duration), clock)

    override fun minus(other: ComparableTimeMark): Duration {
        if (other !is InstantTimeMark || other.clock != this.clock) {
            throw IllegalArgumentException("Subtracting or comparing time marks from different time sources is not possible: $this and $other")
        }
        return saturatingDiff(this.instant, other.instant)
    }

    override fun equals(other: Any?): Boolean {
        return other is InstantTimeMark && this.clock == other.clock && this.instant == other.instant
    }

    override fun hashCode(): Int = instant.hashCode()

    override fun toString(): String = "InstantTimeMark($instant, $clock)"

    private fun Instant.isSaturated() = this == Instant.MAX || this == Instant.MIN
    private fun Instant.saturatingAdd(duration: Duration): Instant {
        if (isSaturated()) {
            if (duration.isInfinite() && duration.isPositive() != this.isDistantFuture) {
                throw IllegalArgumentException("Summing infinities of different signs")
            }
            return this
        }
        return this + duration
    }
    private fun saturatingDiff(instant1: Instant, instant2: Instant): Duration = when {
        instant1 == instant2 ->
            Duration.ZERO
        instant1.isSaturated() || instant2.isSaturated() ->
            (instant1 - instant2) * Double.POSITIVE_INFINITY
        else ->
            instant1 - instant2
    }
}

@Deprecated("Use Clock.todayIn instead", ReplaceWith("this.todayIn(timeZone)"), DeprecationLevel.WARNING)
public fun Clock.todayAt(timeZone: TimeZone): LocalDate = todayIn(timeZone)