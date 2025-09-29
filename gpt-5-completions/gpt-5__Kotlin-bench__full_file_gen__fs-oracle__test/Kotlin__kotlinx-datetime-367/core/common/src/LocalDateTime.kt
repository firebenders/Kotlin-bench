/*
 * Copyright 2019-2022 JetBrains s.r.o. and contributors.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

import kotlinx.datetime.LocalDate.Companion.parse
import kotlinx.datetime.format.*
import kotlinx.datetime.serializers.LocalDateTimeIso8601Serializer
import kotlinx.serialization.Serializable

/**
 * The representation of a specific civil date and time without a reference to a particular time zone.
 *
 * What it represents
 * - A calendar date with a wall-clock time (hour, minute, second, nanosecond) but no time-zone offset.
 * - Not a “moment in time” by itself. Convert with a [TimeZone] via [toInstant] to get an [Instant].
 *
 * How to acquire
 * - Parsing: [LocalDateTime.parse] (ISO by default) or a custom [LocalDateTime.Format].
 * - Construct from components or from [LocalDate] + [LocalTime].
 * - Decode an [Instant] for display: `instant.toLocalDateTime(tz)`.
 *
 * Typical usage
 * - Store scheduled, far-future civil times where local rules may change (keep the [TimeZone] separately).
 * - Present [Instant] values in user interfaces.
 *
 * Interop with platform types
 * - JVM: convert with `toJavaLocalDateTime()` / `toKotlinLocalDateTime()` extension functions.
 *
 * Gotchas
 * - Arithmetic is intentionally omitted because of DST transitions; see README and [Date + time arithmetic] section.
 * - Converting [LocalDateTime] to [Instant] requires a [TimeZone] and can be ambiguous or skip invalid times. The rules are:
 *   gap -> use earlier offset, overlap -> choose earlier instant.
 */
@Serializable(with = LocalDateTimeIso8601Serializer::class)
public expect class LocalDateTime : Comparable<LocalDateTime> {
    public companion object {

        /**
         * A shortcut for calling [DateTimeFormat.parse].
         *
         * Parses a string that represents a date/time value including date and time components
         * but without any time zone component and returns the parsed [LocalDateTime] value.
         *
         * If [format] is not specified, [Formats.ISO] is used.
         *
         * @throws IllegalArgumentException if the text cannot be parsed or the boundaries of [LocalDateTime] are
         * exceeded.
         */
        public fun parse(input: CharSequence, format: DateTimeFormat<LocalDateTime> = getIsoDateTimeFormat()): LocalDateTime

        /**
         * Creates a new format for parsing and formatting [LocalDateTime] values.
         *
         * Examples:
         * ```
         * // `2020-08-30 18:43:13`, using predefined date and time formats
         * LocalDateTime.Format { date(LocalDate.Formats.ISO); char(' '); time(LocalTime.Formats.ISO) }
         *
         * // `08/30 18:43:13`, using a custom format:
         * LocalDateTime.Format {
         *   monthNumber(); char('/'); dayOfMonth()
         *   char(' ')
         *   hour(); char(':'); minute()
         *   optional { char(':'); second() }
         * }
         * ```
         *
         * Only parsing and formatting of well-formed values is supported. If the input does not fit the boundaries
         * (for example, [dayOfMonth] is 31 for February), consider using [DateTimeComponents.Format] instead.
         *
         * There is a collection of predefined formats in [LocalDateTime.Formats].
         *
         * @throws IllegalArgumentException if parsing using this format is ambiguous.
         */
        @Suppress("FunctionName")
        public fun Format(builder: DateTimeFormatBuilder.WithDateTime.() -> Unit): DateTimeFormat<LocalDateTime>

        internal val MIN: LocalDateTime
        internal val MAX: LocalDateTime
    }

    /**
     * A collection of predefined formats for parsing and formatting [LocalDateTime] values.
     *
     * [LocalDateTime.Formats.ISO] is a popular predefined format.
     *
     * If predefined formats are not sufficient, use [LocalDateTime.Format] to create a custom
     * [kotlinx.datetime.format.DateTimeFormat] for [LocalDateTime] values.
     */
    public object Formats {
        /**
         * ISO 8601 extended format.
         *
         * Examples of date/time in ISO 8601 format:
         * - `2020-08-30T18:43`
         * - `+12020-08-30T18:43:00`
         * - `0000-08-30T18:43:00.5`
         * - `-0001-08-30T18:43:00.123456789`
         *
         * When formatting, seconds are always included, even if they are zero.
         * Fractional parts of the second are included if non-zero.
         *
         * Guaranteed to parse all strings that [LocalDateTime.toString] produces.
         */
        public val ISO: DateTimeFormat<LocalDateTime>
    }

    /**
     * Constructs a [LocalDateTime] instance from the given date and time components.
     *
     * The components [monthNumber] and [dayOfMonth] are 1-based.
     *
     * The supported ranges of components:
     * - [year] the range is platform dependent, but at least is enough to represent dates of all instants between
     *          [Instant.DISTANT_PAST] and [Instant.DISTANT_FUTURE]
     * - [monthNumber] `1..12`
     * - [dayOfMonth] `1..31`, the upper bound can be less, depending on the month
     * - [hour] `0..23`
     * - [minute] `0..59`
     * - [second] `0..59`
     * - [nanosecond] `0..999_999_999`
     *
     * @throws IllegalArgumentException if any parameter is out of range, or if [dayOfMonth] is invalid for the given [monthNumber] and
     * [year].
     */
    public constructor(
        year: Int,
        monthNumber: Int,
        dayOfMonth: Int,
        hour: Int,
        minute: Int,
        second: Int = 0,
        nanosecond: Int = 0
    )

    /**
     * Constructs a [LocalDateTime] instance from the given date and time components.
     *
     * The supported ranges of components:
     * - [year] the range is platform dependent, but at least is enough to represent dates of all instants between
     *          [Instant.DISTANT_PAST] and [Instant.DISTANT_FUTURE]
     * - [month] all values of the [Month] enum
     * - [dayOfMonth] `1..31`, the upper bound can be less, depending on the month
     * - [hour] `0..23`
     * - [minute] `0..59`
     * - [second] `0..59`
     * - [nanosecond] `0..999_999_999`
     *
     * @throws IllegalArgumentException if any parameter is out of range, or if [dayOfMonth] is invalid for the given [month] and
     * [year].
     */
    public constructor(
        year: Int,
        month: Month,
        dayOfMonth: Int,
        hour: Int,
        minute: Int,
        second: Int = 0,
        nanosecond: Int = 0
    )

    /**
     * Constructs a [LocalDateTime] instance by combining the given [date] and [time] parts.
     */
    public constructor(date: LocalDate, time: LocalTime)

    /** Returns the year component of the date. */
    public val year: Int

    /** Returns the number-of-month (1..12) component of the date. */
    public val monthNumber: Int

    /** Returns the month ([Month]) component of the date. */
    public val month: Month

    /** Returns the day-of-month component of the date. */
    public val dayOfMonth: Int

    /** Returns the day-of-week component of the date. */
    public val dayOfWeek: DayOfWeek

    /** Returns the day-of-year component of the date. */
    public val dayOfYear: Int

    /** Returns the hour-of-day time component of this date/time value. */
    public val hour: Int

    /** Returns the minute-of-hour time component of this date/time value. */
    public val minute: Int

    /** Returns the second-of-minute time component of this date/time value. */
    public val second: Int

    /** Returns the nanosecond-of-second time component of this date/time value. */
    public val nanosecond: Int

    /** Returns the date part of this date/time value. */
    public val date: LocalDate

    /** Returns the time part of this date/time value. */
    public val time: LocalTime

    /**
     * Compares `this` date/time value with the [other] date/time value.
     * Returns zero if this value is equal to the other,
     * a negative number if this value represents earlier civil time than the other,
     * and a positive number if this value represents later civil time than the other.
     */
    // TODO: add a note about pitfalls of comparing localdatetimes falling in the Autumn transition
    public override operator fun compareTo(other: LocalDateTime): Int

    /**
     * Converts this date/time value to the ISO 8601 string representation.
     *
     * For readability, if the time represents a round minute (without seconds or fractional seconds),
     * the string representation will not include seconds. Also, fractions of seconds will add trailing zeros to
     * the fractional part until its length is a multiple of three.
     *
     * Examples of output:
     * - `2020-08-30T18:43`
     * - `2020-08-30T18:43:00`
     * - `2020-08-30T18:43:00.500`
     * - `2020-08-30T18:43:00.123456789`
     *
     * @see LocalTime.toString for details of how the time part is formatted.
     * @see Formats.ISO for a very similar format. The difference is that [Formats.ISO] will always include seconds,
     * even if they are zero, and will not add trailing zeros to the fractional part of the second for readability.
     * @see parse for the dual operation: obtaining [LocalDateTime] from a string.
     * @see LocalDateTime.format for formatting using a custom format.
     */
    public override fun toString(): String
}

/**
 * Formats this value using the given [format].
 * Equivalent to calling [DateTimeFormat.format] on [format] with `this`.
 */
public fun LocalDateTime.format(format: DateTimeFormat<LocalDateTime>): String = format.format(this)

/**
 * @suppress
 */
@Deprecated("Removed to support more idiomatic code. See https://github.com/Kotlin/kotlinx-datetime/issues/339", ReplaceWith("LocalDateTime.parse(this)"), DeprecationLevel.WARNING)
public fun String.toLocalDateTime(): LocalDateTime = LocalDateTime.parse(this)

// workaround for https://youtrack.jetbrains.com/issue/KT-65484
internal fun getIsoDateTimeFormat() = LocalDateTime.Formats.ISO