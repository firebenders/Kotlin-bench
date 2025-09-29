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
 * An `Instant` represents a specific point on the timeline, independent of any time zone or calendar system.
 * It's defined as a number of seconds and nanoseconds since the Unix epoch (1970-01-01T00:00:00Z).
 *
 * ### Time Scale
 *
 * `Instant` uses the UTC-SLS (Coordinated Universal Time with Smoothed Leap Seconds) time scale.
 * This means leap seconds are "smeared" over the last 1000 seconds of the day when they occur,
 * rather than creating a discontinuity. This ensures that time always moves forward monotonically.
 *
 * ### Obtaining Instances
 *
 * Instants can be obtained in several ways:
 * ```
 * // Current moment
 * val now = Clock.System.now()
 * 
 * // From epoch milliseconds
 * val instant1 = Instant.fromEpochMilliseconds(1234567890123)
 * 
 * // From epoch seconds
 * val instant2 = Instant.fromEpochSeconds(1234567890, nanosecondAdjustment = 123456789)
 * 
 * // Parsing ISO-8601 string
 * val instant3 = Instant.parse("2023-01-15T12:30:45.123Z")
 * ```
 *
 * ### Converting to Local Time
 *
 * To interpret an instant as a human-readable date and time, convert it using a time zone:
 * ```
 * val instant = Clock.System.now()
 * val localDateTime = instant.toLocalDateTime(TimeZone.currentSystemDefault())
 * println("Local time: ${localDateTime.date} ${localDateTime.time}")
 * ```
 *
 * ### Arithmetic Operations
 *
 * Instants support arithmetic with [Duration]:
 * ```
 * val instant = Clock.System.now()
 * val tomorrow = instant + 24.hours
 * val yesterday = instant - 24.hours
 * val difference = tomorrow - instant // Returns a Duration
 * ```
 *
 * For calendar-based arithmetic (adding months, years), use [DateTimePeriod]:
 * ```
 * val instant = Clock.System.now()
 * val nextMonth = instant.plus(1, DateTimeUnit.MONTH, TimeZone.UTC)
 * ```
 *
 * ### Platform Specifics
 *
 * - **JVM**: Wraps `java.time.Instant`
 * - **JS**: Uses millisecond precision internally
 * - **Native**: Custom implementation with nanosecond precision
 *
 * ### Range Limitations
 *
 * The supported range of instants is platform-dependent but guaranteed to include at least:
 * - From [Instant.DISTANT_PAST]: `-100001-12-31T23:59:59.999999999Z`
 * - To [Instant.DISTANT_FUTURE]: `+100000-01-01T00:00:00Z`
 *
 * @see Clock.System.now for obtaining the current instant
 * @see LocalDateTime for civil date-time representation
 * @see TimeZone for converting between instant and local time
 */
@Serializable(with = InstantIso8601Serializer::class)
public expect class Instant : Comparable<Instant> {

    /**
     * The number of seconds from the Unix epoch instant `1970-01-01T00:00:00Z`.
     *
     * The value is rounded towards negative infinity if the actual instant includes fractional seconds.
     * Use [nanosecondsOfSecond] to get the fractional part.
     *
     * ### Example
     * ```
     * val instant = Instant.parse("2023-01-15T12:30:45.123456789Z")
     * println(instant.epochSeconds) // Number of whole seconds since 1970-01-01T00:00:00Z
     * println(instant.nanosecondsOfSecond) // 123456789
     * ```
     *
     * Note that this number doesn't include leap seconds added or removed since the epoch.
     *
     * @see Instant.fromEpochSeconds for the inverse operation
     * @see nanosecondsOfSecond for the fractional part
     */
    public val epochSeconds: Long

    /**
     * The number of nanoseconds by which this instant is later than [epochSeconds] from the epoch instant.
     *
     * The value is always positive and lies in the range `0..999_999_999`.
     *
     * ### Example
     * ```
     * val instant = Instant.fromEpochSeconds(1234567890, nanosecondAdjustment = 123456789)
     * println(instant.epochSeconds) // 1234567890
     * println(instant.nanosecondsOfSecond) // 123456789
     * ```
     *
     * @see Instant.fromEpochSeconds for constructing instants from components
     */
    public val nanosecondsOfSecond: Int

    /**
     * Returns the number of milliseconds from the Unix epoch instant `1970-01-01T00:00:00Z`.
     *
     * Any fractional part of millisecond is rounded towards negative infinity.
     *
     * If the result does not fit in [Long], returns [Long.MAX_VALUE] for instants after the epoch
     * or [Long.MIN_VALUE] for instants before the epoch.
     *
     * ### Example
     * ```
     * val instant = Clock.System.now()
     * val millis = instant.toEpochMilliseconds()
     * 
     * // Round-trip conversion (may lose nanosecond precision)
     * val restored = Instant.fromEpochMilliseconds(millis)
     * ```
     *
     * @see Instant.fromEpochMilliseconds for the inverse operation
     */
    public fun toEpochMilliseconds(): Long

    /**
     * Returns an instant that is the result of adding the specified [duration] to this instant.
     *
     * If the [duration] is positive, the returned instant is later than this instant.
     * If the [duration] is negative, the returned instant is earlier than this instant.
     *
     * ### Example
     * ```
     * val now = Clock.System.now()
     * val inOneHour = now + 1.hours
     * val yesterday = now + (-24).hours
     * ```
     *
     * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
     *
     * @param duration the duration to add, can be negative
     * @return the instant after adding the duration
     */
    public operator fun plus(duration: Duration): Instant

    /**
     * Returns an instant that is the result of subtracting the specified [duration] from this instant.
     *
     * If the [duration] is positive, the returned instant is earlier than this instant.
     * If the [duration] is negative, the returned instant is later than this instant.
     *
     * ### Example
     * ```
     * val now = Clock.System.now()
     * val oneHourAgo = now - 1.hours
     * val tomorrow = now - (-24).hours
     * ```
     *
     * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
     *
     * @param duration the duration to subtract, can be negative
     * @return the instant after subtracting the duration
     */
    public operator fun minus(duration: Duration): Instant

    /**
     * Returns the [Duration] between two instants: [other] and `this`.
     *
     * The duration returned is positive if this instant is later than the other,
     * and negative if this instant is earlier than the other.
     *
     * ### Example
     * ```
     * val start = Clock.System.now()
     * // ... perform some operation ...
     * val end = Clock.System.now()
     * val elapsed = end - start
     * println("Operation took: $elapsed")
     * ```
     *
     * The result is never clamped, but note that for instants that are far apart,
     * the value returned may represent the duration between them inexactly due to the loss of precision.
     *
     * @param other the instant to subtract from this one
     * @return the duration between the instants
     */
    public operator fun minus(other: Instant): Duration

    /**
     * Compares this instant with the [other] instant.
     * 
     * Returns zero if this instant represents the same moment as the other,
     * a negative number if this instant is earlier than the other,
     * and a positive number if this instant is later than the other.
     *
     * ### Example
     * ```
     * val instant1 = Instant.parse("2023-01-15T12:00:00Z")
     * val instant2 = Instant.parse("2023-01-15T13:00:00Z")
     * 
     * if (instant1 < instant2) {
     *     println("instant1 is earlier")
     * }
     * ```
     *
     * @param other the instant to compare with
     * @return the comparison result
     */
    public override operator fun compareTo(other: Instant): Int

    /**
     * Converts this instant to the ISO-8601 string representation.
     *
     * The format is: `yyyy-MM-ddTHH:mm:ss[.SSS]Z` where:
     * - `yyyy` is the year (may include a sign for years outside 0000-9999)
     * - `MM` is the month (01-12)
     * - `dd` is the day (01-31)
     * - `HH` is the hour (00-23)
     * - `mm` is the minute (00-59)
     * - `ss` is the second (00-59)
     * - `SSS` is the fractional second (included only if non-zero, padded to multiples of 3)
     * - `Z` indicates UTC
     *
     * ### Example
     * ```
     * val instant = Clock.System.now()
     * println(instant.toString()) // e.g., "2023-01-15T12:30:45.123Z"
     * ```
     *
     * The representation uses the UTC-SLS time scale. Leap seconds will not result in
     * a seconds value of 60.
     *
     * @see Instant.parse for the inverse operation
     * @see DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET for a similar format
     */
    public override fun toString(): String


    public companion object {
        @Deprecated("Use Clock.System.now() instead", ReplaceWith("Clock.System.now()", "kotlinx.datetime.Clock"), level = DeprecationLevel.ERROR)
        public fun now(): Instant

        /**
         * Creates an [Instant] from the number of milliseconds since the Unix epoch.
         *
         * The Unix epoch is `1970-01-01T00:00:00Z`.
         *
         * ### Example
         * ```
         * val millis = System.currentTimeMillis() // On JVM
         * val instant = Instant.fromEpochMilliseconds(millis)
         * 
         * // Round-trip conversion
         * val original = Clock.System.now()
         * val converted = Instant.fromEpochMilliseconds(original.toEpochMilliseconds())
         * // Note: may lose nanosecond precision
         * ```
         *
         * The return value is clamped to the platform-specific boundaries for [Instant] if the result exceeds them.
         *
         * @param epochMilliseconds the number of milliseconds since 1970-01-01T00:00:00Z
         * @return the corresponding instant
         * @see toEpochMilliseconds for the inverse operation
         */
        public fun fromEpochMilliseconds(epochMilliseconds: Long): Instant

        /**
         * Creates an [Instant] from the number of seconds and nanoseconds since the Unix epoch.
         *
         * ### Example
         * ```
         * val instant = Instant.fromEpochSeconds(1234567890, nanosecondAdjustment = 123456789)
         * // Equivalent to: Instant.fromEpochSeconds(1234567890, 123456789)
         * 
         * // Can also handle nanoseconds exceeding 999,999,999
         * val instant2 = Instant.fromEpochSeconds(1000, nanosecondAdjustment = 1_500_000_000L)
         * // Results in 1001 seconds and 500,000,000 nanoseconds
         * ```
         *
         * @param epochSeconds the number of seconds since 1970-01-01T00:00:00Z
         * @param nanosecondAdjustment the nanosecond adjustment, can be outside 0..999,999,999
         * @return the corresponding instant
         */
        public fun fromEpochSeconds(epochSeconds: Long, nanosecondAdjustment: Long = 0): Instant

        /**
         * Creates an [Instant] from the number of seconds and nanoseconds since the Unix epoch.
         *
         * This is a convenience overload for when the nanosecond adjustment fits in an [Int].
         *
         * @param epochSeconds the number of seconds since 1970-01-01T00:00:00Z
         * @param nanosecondAdjustment the nanosecond adjustment (0..999,999,999)
         * @return the corresponding instant
         */
        public fun fromEpochSeconds(epochSeconds: Long, nanosecondAdjustment: Int): Instant

        /**
         * Parses an ISO-8601 instant string and returns the parsed [Instant] value.
         *
         * The string must include date, time, and UTC offset components.
         * The format is generally: `yyyy-MM-ddTHH:mm:ss[.SSS]Z` or with an offset like `+01:00`.
         *
         * ### Example
         * ```
         * val instant1 = Instant.parse("2023-01-15T12:30:45Z")
         * val instant2 = Instant.parse("2023-01-15T12:30:45.123456789Z")
         * val instant3 = Instant.parse("2023-01-15T14:30:45+02:00")
         * ```
         *
         * The string is interpreted on the UTC-SLS time scale. Leap seconds (like `23:59:60`)
         * are not supported and will cause parsing to fail.
         *
         * @param input the string to parse
         * @param format the format to use for parsing (defaults to ISO-8601)
         * @return the parsed instant
         * @throws IllegalArgumentException if the string cannot be parsed or is out of range
         * @see toString for formatting
         */
        public fun parse(
            input: CharSequence,
            format: DateTimeFormat<DateTimeComponents> = DateTimeComponents.Formats.ISO_DATE_TIME_OFFSET
        ): Instant

        /**
         * An instant value that is far in the past.
         *
         * This is defined as `-100001-12-31T23:59:59.999999999Z`.
         *
         * All instants in the range `DISTANT_PAST..DISTANT_FUTURE` can be [converted][Instant.toLocalDateTime] to
         * [LocalDateTime] without exceptions on all supported platforms.
         *
         * ### Example
         * ```
         * val veryOldDate = Instant.DISTANT_PAST
         * val dateTime = veryOldDate.toLocalDateTime(TimeZone.UTC)
         * println(dateTime) // -100001-12-31T23:59:59.999999999
         * ```
         */
        public val DISTANT_PAST: Instant

        /**
         * An instant value that is far in the future.
         *
         * This is defined as `+100000-01-01T00:00:00Z`.
         *
         * All instants in the range `DISTANT_PAST..DISTANT_FUTURE` can be [converted][Instant.toLocalDateTime] to
         * [LocalDateTime] without exceptions on all supported platforms.
         *
         * ### Example
         * ```
         * val farFuture = Instant.DISTANT_FUTURE
         * val dateTime = farFuture.toLocalDateTime(TimeZone.UTC)
         * println(dateTime) // +100000-01-01T00:00:00
         * ```
         */
        public val DISTANT_FUTURE: Instant

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