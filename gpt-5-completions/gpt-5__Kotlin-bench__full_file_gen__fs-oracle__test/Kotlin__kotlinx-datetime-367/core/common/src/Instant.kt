/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

import kotlinx.datetime.format.*
import kotlinx.datetime.internal.*
import kotlinx.datetime.serializers.InstantIso8601Serializer
import kotlinx.serialization.Serializable
import kotlin.time.*

/**
 * A moment in time.
 *
 * What it represents
 * - A specific, globally-unique point on the UTC‑SLS time scale (smeared leap seconds).
 * - It is independent of time zones and calendars. Use [LocalDateTime] with a [TimeZone] for human-readable display.
 *
 * Time scale
 * - `Instant` uses the UTC‑SLS (smeared leap second) time scale. Positive/negative leap seconds are “smeared”
 *   over the last 1000 seconds of the day with a leap second. This means there are no instants with second=60.
 *
 * How to acquire
 * - [Clock.now] to get the current moment ([Clock.System] uses the OS clock).
 * - [Instant.parse] from an ISO‑8601 string with an explicit UTC offset.
 * - [Instant.fromEpochMilliseconds] or [Instant.fromEpochSeconds] from Unix/POSIX time.
 *
 * Typical usage
 * - Arithmetic with [Duration] or calendar-aware arithmetic with [DateTimeUnit] and a [TimeZone].
 * - Convert to local date/time: [toLocalDateTime] (requires a [TimeZone]) or [format] for strings.
 *
 * Interop with platform types
 * - JVM: interoperability with java.time:
 *   - Use the extension functions typically named `toJavaInstant()` and `toKotlinInstant()` (provided in the JVM artifact)
 *     to convert between `kotlinx.datetime.Instant` and `java.time.Instant`.
 * - JS: maps to js-joda `Instant` internally.
 * - Native: backed by the library’s own implementation.
 *
 * Gotchas
 * - Do not store far-future scheduled events as `Instant` if the local wall time matters; keep [LocalDateTime] plus [TimeZone].
 * - Converting the same wall time across DST transitions requires a [TimeZone] and can be ambiguous or skip times.
 *
 * Examples
 * ```
 * val now = Clock.System.now()
 * val utc = TimeZone.UTC
 * println(now.toString()) // ISO-8601 with 'Z'
 * println(now.toLocalDateTime(utc))
 *
 * val inTwoDaysBerlin = now.plus(2, DateTimeUnit.DAY, TimeZone.of("Europe/Berlin"))
 * ```
 */
@Serializable(with = InstantIso8601Serializer::class)
public expect class Instant : Comparable<Instant> {

    /**
     * The number of seconds from the epoch instant `1970-01-01T00:00:00Z` rounded down to a [Long] number.
     *
     * The difference between the rounded number of seconds and the actual number of seconds
     * is returned by [nanosecondsOfSecond] property expressed in nanoseconds.
     *
     * Note that this number doesn't include leap seconds added or removed since the epoch.
     *
     * @see Instant.fromEpochSeconds
     */
    public val epochSeconds: Long

    /**
     * The number of nanoseconds by which this instant is later than [epochSeconds] from the epoch instant.
     *
     * The value is always positive and lies in the range `0..999_999_999`.
     *
     * @see Instant.fromEpochSeconds
     */
    public val nanosecondsOfSecond: Int

    /**
     * Returns the number of milliseconds from the epoch instant `1970-01-01T00:00:00Z`.
     *
     * Any fractional part of millisecond is rounded down to the whole number of milliseconds.
     *
     * If the result does not fit in [Long], returns [Long.MAX_VALUE] for a positive result or [Long.MIN_VALUE] for a negative result.
     *
     * @see Instant.fromEpochMilliseconds
     */
    public fun toEpochMilliseconds(): Long

    /**
     * Returns an instant that is the result of adding the specified [duration] to this instant.
     *
     * If the [duration] is positive, the returned instant is later than this instant.
     * If the [duration] is negative, the returned instant is earlier than this instant.
     *
     * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
     */
    public operator fun plus(duration: Duration): Instant

    /**
     * Returns an instant that is the result of subtracting the specified [duration] from this instant.
     *
     * If the [duration] is positive, the returned instant is earlier than this instant.
     * If the [duration] is negative, the returned instant is later than this instant.
     *
     * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
     */
    public operator fun minus(duration: Duration): Instant

    // questionable
    /**
     * Returns the [Duration] between two instants: [other] and `this`.
     *
     * The duration returned is positive if this instant is later than the other,
     * and negative if this instant is earlier than the other.
     *
     * The result is never clamped, but note that for instants that are far apart,
     * the value returned may represent the duration between them inexactly due to the loss of precision.
     */
    public operator fun minus(other: Instant): Duration

    /**
     * Compares `this` instant with the [other] instant.
     * Returns zero if this instant represents the same moment as the other (i.e. equal to other),
     * a negative number if this instant is earlier than the other,
     * and a positive number if this instant is later than the other.
     */
    public override operator fun compareTo(other: Instant): Int

    /**
     * Converts this instant to the ISO-8601 string representation.
     *
     * The representation uses the UTC-SLS time scale, instead of UTC.
     * In practice, this means that leap second handling will not be readjusted to the UTC.
     * Leap seconds will not be added or skipped, so it is impossible to acquire a string
     * where the component for seconds is 60, and for any day, it's possible to observe 23:59:59.
     *
     * @see Instant.parse
     * @see DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET for a very similar format. The difference is that
     * [DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET] will not add trailing zeros for readability to the
     * fractional part of the second.
     */
    public override fun toString(): String


    public companion object {
        @Deprecated("Use Clock.System.now() instead", ReplaceWith("Clock.System.now()", "kotlinx.datetime.Clock"), level = DeprecationLevel.ERROR)
        public fun now(): Instant

        /**
         * Returns an [Instant] that is [epochMilliseconds] number of milliseconds from the epoch instant `1970-01-01T00:00:00Z`.
         *
         * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
         *
         * @see Instant.toEpochMilliseconds
         */
        public fun fromEpochMilliseconds(epochMilliseconds: Long): Instant

        /**
         * Returns an [Instant] that is the [epochSeconds] number of seconds from the epoch instant `1970-01-01T00:00:00Z`
         * and the [nanosecondAdjustment] number of nanoseconds from the whole second.
         *
         * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
         */
        public fun fromEpochSeconds(epochSeconds: Long, nanosecondAdjustment: Long = 0): Instant

        /**
         * Returns an [Instant] that is the [epochSeconds] number of seconds from the epoch instant `1970-01-01T00:00:00Z`
         * and the [nanosecondAdjustment] number of nanoseconds from the whole second.
         *
         * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
         */
        public fun fromEpochSeconds(epochSeconds: Long, nanosecondAdjustment: Int): Instant

        /**
         * A shortcut for calling [DateTimeFormat.parse], followed by [DateTimeComponents.toInstantUsingOffset].
         *
         * Parses a string that represents an instant including date and time components and a mandatory
         * time zone offset and returns the parsed [Instant] value.
         *
         * The string is considered to represent time on the UTC-SLS time scale instead of UTC.
         * In practice, this means that, even if there is a leap second on the given day, it will not affect how the
         * time is parsed, even if it's in the last 1000 seconds of the day.
         * Instead, even if there is a negative leap second on the given day, 23:59:59 is still considered valid time.
         * 23:59:60 is invalid on UTC-SLS, so parsing it will fail.
         *
         * If the format is not specified, [DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET] is used.
         *
         * @throws IllegalArgumentException if the text cannot be parsed or the boundaries of [Instant] are exceeded.
         *
         * @see Instant.toString for formatting using the default format.
         * @see Instant.format for formatting using a custom format.
         */
        public fun parse(
            input: CharSequence,
            format: DateTimeFormat<DateTimeComponents> = DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET
        ): Instant

        /**
         * An instant value that is far in the past.
         *
         * All instants in the range `DISTANT_PAST..DISTANT_FUTURE` can be [converted][Instant.toLocalDateTime] to
         * [LocalDateTime] without exceptions on all supported platforms.
         */
        public val DISTANT_PAST: Instant // -100001-12-31T23:59:59.999999999Z

        /**
         * An instant value that is far in the future.
         *
         * All instants in the range `DISTANT_PAST..DISTANT_FUTURE` can be [converted][Instant.toLocalDateTime] to
         * [LocalDateTime] without exceptions on all supported platforms.
         */
        public val DISTANT_FUTURE: Instant // +100000-01-01T00:00:00Z

        internal val MIN: Instant
        internal val MAX: Instant
    }
}

/** Returns true if the instant is [Instant.DISTANT_PAST] or earlier. */
public val Instant.isDistantPast: Boolean
    get() = this <= Instant.DISTANT_PAST

/** Returns true if the instant is [Instant.DISTANT_FUTURE] or later. */
public val Instant.isDistantFuture: Boolean
    get() = this >= Instant.DISTANT_FUTURE

/**
 * @suppress
 */
@Deprecated("Removed to support more idiomatic code. See https://github.com/Kotlin/kotlinx-datetime/issues/339", ReplaceWith("Instant.parse(this)"), DeprecationLevel.WARNING)
public fun String.toInstant(): Instant = Instant.parse(this)

/**
 * Returns an instant that is the result of adding components of [DateTimePeriod] to this instant. The components are
 * added in the order from the largest units to the smallest, i.e. from years to nanoseconds.
 *
 * @throws DateTimeArithmeticException if this value or the results of intermediate computations are too large to fit in
 * [LocalDateTime].
 */
public expect fun Instant.plus(period: DateTimePeriod, timeZone: TimeZone): Instant

/**
 * Returns an instant that is the result of subtracting components of [DateTimePeriod] from this instant. The components
 * are subtracted in the order from the largest units to the smallest, i.e. from years to nanoseconds.
 *
 * @throws DateTimeArithmeticException if this value or the results of intermediate computations are too large to fit in
 * [LocalDateTime].
 */
public fun Instant.minus(period: DateTimePeriod, timeZone: TimeZone): Instant =
    /* An overflow can happen for any component, but we are only worried about nanoseconds, as having an overflow in
    any other component means that `plus` will throw due to the minimum value of the numeric type overflowing the
    platform-specific limits. */
    if (period.totalNanoseconds != Long.MIN_VALUE) {
        val negatedPeriod = with(period) { buildDateTimePeriod(-totalMonths, -days, -totalNanoseconds) }
        plus(negatedPeriod, timeZone)
    } else {
        val negatedPeriod = with(period) { buildDateTimePeriod(-totalMonths, -days, -(totalNanoseconds+1)) }
        plus(negatedPeriod, timeZone).plus(1, DateTimeUnit.NANOSECOND)
    }

/**
 * Returns a [DateTimePeriod] representing the difference between `this` and [other] instants.
 *
 * The components of [DateTimePeriod] are calculated so that adding it to `this` instant results in the [other] instant.
 *
 * All components of the [DateTimePeriod] returned are:
 * - positive or zero if this instant is earlier than the other,
 * - negative or zero if this instant is later than the other,
 * - exactly zero if this instant is equal to the other.
 *
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 *     Or (only on the JVM) if the number of months between the two dates exceeds an Int.
 */
public expect fun Instant.periodUntil(other: Instant, timeZone: TimeZone): DateTimePeriod

/**
 * Returns the whole number of the specified date or time [units][unit] between `this` and [other] instants
 * in the specified [timeZone].
 *
 * The value returned is:
 * - positive or zero if this instant is earlier than the other,
 * - negative or zero if this instant is later than the other,
 * - zero if this instant is equal to the other.
 *
 * If the result does not fit in [Long], returns [Long.MAX_VALUE] for a positive result or [Long.MIN_VALUE] for a negative result.
 *
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 */
public expect fun Instant.until(other: Instant, unit: DateTimeUnit, timeZone: TimeZone): Long

/**
 * Returns the whole number of the specified time [units][unit] between `this` and [other] instants.
 *
 * The value returned is:
 * - positive or zero if this instant is earlier than the other,
 * - negative or zero if this instant is later than the other,
 * - zero if this instant is equal to the other.
 *
 * If the result does not fit in [Long], returns [Long.MAX_VALUE] for a positive result or [Long.MIN_VALUE] for a negative result.
 */
public fun Instant.until(other: Instant, unit: DateTimeUnit.TimeBased): Long =
    try {
        multiplyAddAndDivide(other.epochSeconds - epochSeconds,
            NANOS_PER_ONE.toLong(),
            (other.nanosecondsOfSecond - nanosecondsOfSecond).toLong(),
            unit.nanoseconds)
    } catch (e: ArithmeticException) {
        if (this < other) Long.MAX_VALUE else Long.MIN_VALUE
    }

/**
 * Returns the number of whole days between two instants in the specified [timeZone].
 *
 * If the result does not fit in [Int], returns [Int.MAX_VALUE] for a positive result or [Int.MIN_VALUE] for a negative result.
 *
 * @see Instant.until
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 */
public fun Instant.daysUntil(other: Instant, timeZone: TimeZone): Int =
        until(other, DateTimeUnit.DAY, timeZone).clampToInt()

/**
 * Returns the number of whole months between two instants in the specified [timeZone].
 *
 * If the result does not fit in [Int], returns [Int.MAX_VALUE] for a positive result or [Int.MIN_VALUE] for a negative result.
 *
 * @see Instant.until
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 */
public fun Instant.monthsUntil(other: Instant, timeZone: TimeZone): Int =
        until(other, DateTimeUnit.MONTH, timeZone).clampToInt()

/**
 * Returns the number of whole years between two instants in the specified [timeZone].
 *
 * If the result does not fit in [Int], returns [Int.MAX_VALUE] for a positive result or [Int.MIN_VALUE] for a negative result.
 *
 * @see Instant.until
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 */
public fun Instant.yearsUntil(other: Instant, timeZone: TimeZone): Int =
        until(other, DateTimeUnit.YEAR, timeZone).clampToInt()

/**
 * Returns a [DateTimePeriod] representing the difference between [other] and `this` instants.
 *
 * The components of [DateTimePeriod] are calculated so that adding it back to the `other` instant results in this instant.
 *
 * All components of the [DateTimePeriod] returned are:
 * - negative or zero if this instant is earlier than the other,
 * - positive or zero if this instant is later than the other,
 * - exactly zero if this instant is equal to the other.
 *
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 *   Or (only on the JVM) if the number of months between the two dates exceeds an Int.
 * @see Instant.periodUntil
 */
public fun Instant.minus(other: Instant, timeZone: TimeZone): DateTimePeriod =
        other.periodUntil(this, timeZone)


/**
 * Returns an instant that is the result of adding one [unit] to this instant
 * in the specified [timeZone].
 *
 * The returned instant is later than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
@Deprecated("Use the plus overload with an explicit number of units", ReplaceWith("this.plus(1, unit, timeZone)"))
public expect fun Instant.plus(unit: DateTimeUnit, timeZone: TimeZone): Instant

/**
 * Returns an instant that is the result of subtracting one [unit] from this instant
 * in the specified [timeZone].
 *
 * The returned instant is earlier than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
@Deprecated("Use the minus overload with an explicit number of units", ReplaceWith("this.minus(1, unit, timeZone)"))
public fun Instant.minus(unit: DateTimeUnit, timeZone: TimeZone): Instant =
    plus(-1, unit, timeZone)

/**
 * Returns an instant that is the result of adding one [unit] to this instant.
 *
 * The returned instant is later than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
@Deprecated("Use the plus overload with an explicit number of units", ReplaceWith("this.plus(1, unit)"))
public fun Instant.plus(unit: DateTimeUnit.TimeBased): Instant =
    plus(1L, unit)

/**
 * Returns an instant that is the result of subtracting one [unit] from this instant.
 *
 * The returned instant is earlier than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
@Deprecated("Use the minus overload with an explicit number of units", ReplaceWith("this.minus(1, unit)"))
public fun Instant.minus(unit: DateTimeUnit.TimeBased): Instant =
    plus(-1L, unit)

/**
 * Returns an instant that is the result of adding the [value] number of the specified [unit] to this instant
 * in the specified [timeZone].
 *
 * If the [value] is positive, the returned instant is later than this instant.
 * If the [value] is negative, the returned instant is earlier than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
public expect fun Instant.plus(value: Int, unit: DateTimeUnit, timeZone: TimeZone): Instant

/**
 * Returns an instant that is the result of subtracting the [value] number of the specified [unit] from this instant
 * in the specified [timeZone].
 *
 * If the [value] is positive, the returned instant is earlier than this instant.
 * If the [value] is negative, the returned instant is later than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
public expect fun Instant.minus(value: Int, unit: DateTimeUnit, timeZone: TimeZone): Instant

/**
 * Returns an instant that is the result of adding the [value] number of the specified [unit] to this instant.
 *
 * If the [value] is positive, the returned instant is later than this instant.
 * If the [value] is negative, the returned instant is earlier than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
public fun Instant.plus(value: Int, unit: DateTimeUnit.TimeBased): Instant =
    plus(value.toLong(), unit)

/**
 * Returns an instant that is the result of subtracting the [value] number of the specified [unit] from this instant.
 *
 * If the [value] is positive, the returned instant is earlier than this instant.
 * If the [value] is negative, the returned instant is later than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
public fun Instant.minus(value: Int, unit: DateTimeUnit.TimeBased): Instant =
    minus(value.toLong(), unit)

/**
 * Returns an instant that is the result of adding the [value] number of the specified [unit] to this instant
 * in the specified [timeZone].
 *
 * If the [value] is positive, the returned instant is later than this instant.
 * If the [value] is negative, the returned instant is earlier than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
public expect fun Instant.plus(value: Long, unit: DateTimeUnit, timeZone: TimeZone): Instant

/**
 * Returns an instant that is the result of subtracting the [value] number of the specified [unit] from this instant
 * in the specified [timeZone].
 *
 * If the [value] is positive, the returned instant is earlier than this instant.
 * If the [value] is negative, the returned instant is later than this instant.
 *
 * @throws DateTimeArithmeticException if this value or the result is too large to fit in [LocalDateTime].
 */
public fun Instant.minus(value: Long, unit: DateTimeUnit, timeZone: TimeZone): Instant =
    if (value != Long.MIN_VALUE) {
        plus(-value, unit, timeZone)
    } else {
        plus(-(value + 1), unit, timeZone).plus(1, unit, timeZone)
    }

/**
 * Returns an instant that is the result of adding the [value] number of the specified [unit] to this instant.
 *
 * If the [value] is positive, the returned instant is later than this instant.
 * If the [value] is negative, the returned instant is earlier than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
public expect fun Instant.plus(value: Long, unit: DateTimeUnit.TimeBased): Instant

/**
 * Returns an instant that is the result of subtracting the [value] number of the specified [unit] from this instant.
 *
 * If the [value] is positive, the returned instant is earlier than this instant.
 * If the [value] is negative, the returned instant is later than this instant.
 *
 * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
 */
public fun Instant.minus(value: Long, unit: DateTimeUnit.TimeBased): Instant =
    if (value != Long.MIN_VALUE) {
        plus(-value, unit)
    } else {
        plus(-(value + 1), unit).plus(1, unit)
    }

/**
 * Returns the whole number of the specified date or time [units][unit] between [other] and `this` instants
 * in the specified [timeZone].
 *
 * The value returned is negative or zero if this instant is earlier than the other,
 * and positive or zero if this instant is later than the other.
 *
 * If the result does not fit in [Long], returns [Long.MAX_VALUE] for a positive result or [Long.MIN_VALUE] for a negative result.
 *
 * @throws DateTimeArithmeticException if `this` or [other] instant is too large to fit in [LocalDateTime].
 * @see Instant.until
 */
public fun Instant.minus(other: Instant, unit: DateTimeUnit, timeZone: TimeZone): Long =
        other.until(this, unit, timeZone)

/**
 * Returns the whole number of the specified time [units][unit] between [other] and `this` instants.
 *
 * The value returned is negative or zero if this instant is earlier than the other,
 * and positive or zero if this instant is later than the other.
 *
 * If the result does not fit in [Long], returns [Long.MAX_VALUE] for a positive result or [Long.MIN_VALUE] for a negative result.
 *
 * @see Instant.until
 */
public fun Instant.minus(other: Instant, unit: DateTimeUnit.TimeBased): Long =
    other.until(this, unit)

/**
 * Formats this value using the given [format] using the given [offset].
 *
 * Equivalent to calling [DateTimeFormat.format] on [format] and using [DateTimeComponents.setDateTimeOffset] in
 * the lambda.
 *
 * [DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET] is a format very similar to the one used by [toString].
 * The only difference is that [Instant.toString] adds trailing zeros to the fraction-of-second component so that the
 * number of digits after a dot is a multiple of three.
 */
public fun Instant.format(format: DateTimeFormat<DateTimeComponents>, offset: UtcOffset = UtcOffset.ZERO): String {
    val instant = this
    return format.format { setDateTimeOffset(instant, offset) }
}

internal const val DISTANT_PAST_SECONDS = -3217862419201
internal const val DISTANT_FUTURE_SECONDS = 3093527980800