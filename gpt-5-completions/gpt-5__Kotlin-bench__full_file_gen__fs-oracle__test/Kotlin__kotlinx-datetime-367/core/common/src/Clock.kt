/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

import kotlin.time.*

/**
 * A source of [Instant] values.
 *
 * What it represents
 * - A Clock abstracts the notion of "current moment" in physical time. The instants it produces are on the same
 *   UTC-SLS time scale as [Instant] itself.
 *
 * How to acquire
 * - Use [Clock.System] to query the operating system clock.
 * - Provide your own implementation for tests or deterministic behavior (for example, a clock that always returns
 *   a fixed instant or advances in a controlled way).
 * - Pass a [Clock] to APIs that need "now" to make your code testable.
 *
 * Typical usage
 * - Get the current moment: `val now = Clock.System.now()`
 * - Convert to local components for a particular time zone: `now.toLocalDateTime(TimeZone.currentSystemDefault())`
 * - Measure elapsed wall-clock time with [asTimeSource] when you need "time since now" semantics resilient to jumps.
 *
 * Notes and gotchas
 * - Wall-clock time can change due to system adjustments (NTP, user, DST changes are handled in time zone conversion).
 *   If you need a strictly monotonic time source for performance measurements, use Kotlin's [TimeSource.Monotonic]
 *   from kotlin.time instead. Use [Clock.asTimeSource] only when you want elapsed wall-clock time anchored at a real instant.
 *
 * Related types
 * - [Instant] (the values produced by this clock)
 * - [TimeZone] (for converting instants to human-readable local date/time)
 */
public interface Clock {
    /**
     * Returns the [Instant] corresponding to the current time, according to this clock.
     *
     * Example:
     * ```
     * val now: Instant = Clock.System.now()
     * val berlin = TimeZone.of("Europe/Berlin")
     * val local = now.toLocalDateTime(berlin)
     * println("It's $local in Berlin")
     * ```
     */
    public fun now(): Instant

    /**
     * The [Clock] instance that queries the operating system as its source of knowledge of time.
     *
     * Characteristics
     * - Uses the platform wall clock; values can jump forward or backward if the system time is adjusted.
     * - Produces instants on the UTC-SLS time scale.
     *
     * Interop
     * - On the JVM, it uses the same underlying clock as java.time when converting to platform types.
     */
    public object System : Clock {
        override fun now(): Instant = @Suppress("DEPRECATION_ERROR") Instant.now()
    }

    public companion object {

    }
}

/**
 * Returns the current date at the given [time zone][timeZone], according to [this Clock][this].
 *
 * The result depends on the time zone and can differ between zones at the same physical instant.
 *
 * Example:
 * ```
 * val tz = TimeZone.of("America/Los_Angeles")
 * val todayInLa: LocalDate = Clock.System.todayIn(tz)
 * ```
 */
public fun Clock.todayIn(timeZone: TimeZone): LocalDate =
    now().toLocalDateTime(timeZone).date

/**
 * Returns a [TimeSource] that uses this [Clock] to mark a time instant and to find the amount of time elapsed since that mark.
 *
 * Use this when you need elapsed wall-clock time anchored to a real [Instant], but do not require strict monotonicity.
 * If you need monotonic elapsed time for performance measurement, prefer [TimeSource.Monotonic].
 *
 * Example:
 * ```
 * val ts = Clock.System.asTimeSource()
 * val mark = ts.markNow()
 * // ... do something tied to wall-clock ...
 * println("Elapsed (wall clock): ${mark.elapsedNow()}")
 * ```
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