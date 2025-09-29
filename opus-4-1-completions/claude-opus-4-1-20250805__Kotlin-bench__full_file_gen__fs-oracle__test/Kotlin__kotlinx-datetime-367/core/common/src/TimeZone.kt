/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

@file:kotlin.jvm.JvmMultifileClass
@file:kotlin.jvm.JvmName("TimeZoneKt")

package kotlinx.datetime

import kotlinx.datetime.serializers.*
import kotlinx.serialization.Serializable

/**
 * A time zone, providing rules for converting between [Instant] and [LocalDateTime] values.
 *
 * A `TimeZone` defines how to interpret a [LocalDateTime] as an [Instant] (a specific moment in time)
 * and vice versa. It encapsulates the rules for UTC offset changes, including daylight saving time (DST)
 * transitions.
 *
 * ### Types of Time Zones
 *
 * There are two main types:
 * - **Region-based zones** (e.g., `"Europe/Berlin"`, `"America/New_York"`): These follow the rules defined
 *   in the IANA Time Zone Database, including historical changes and DST transitions.
 * - **Fixed-offset zones** (e.g., `"UTC+02:00"`, `"GMT-05:00"`): These maintain a constant offset from UTC.
 *   See [FixedOffsetTimeZone] for this special case.
 *
 * ### Obtaining Time Zones
 *
 * Time zones can be obtained in several ways:
 * ```
 * // System's current time zone
 * val systemTZ = TimeZone.currentSystemDefault()
 * 
 * // UTC time zone
 * val utc = TimeZone.UTC
 * 
 * // By IANA identifier
 * val berlin = TimeZone.of("Europe/Berlin")
 * 
 * // Fixed offset
 * val plus3 = TimeZone.of("+03:00")
 * ```
 *
 * ### Converting Between Instant and LocalDateTime
 *
 * The primary use of `TimeZone` is converting between absolute time ([Instant]) and civil time ([LocalDateTime]):
 * ```
 * val zone = TimeZone.of("America/New_York")
 * val instant = Clock.System.now()
 * 
 * // Convert instant to local time
 * val localDateTime = instant.toLocalDateTime(zone)
 * 
 * // Convert local time to instant
 * val instant2 = localDateTime.toInstant(zone)
 * ```
 *
 * ### Daylight Saving Time
 *
 * During DST transitions, some local times may not exist (spring forward) or may occur twice (fall back):
 * ```
 * val zone = TimeZone.of("America/New_York")
 * 
 * // During "spring forward", 2:30 AM doesn't exist
 * val nonExistent = LocalDateTime(2023, 3, 12, 2, 30)
 * val instant = nonExistent.toInstant(zone) // Uses the offset before transition
 * 
 * // During "fall back", 1:30 AM occurs twice
 * val ambiguous = LocalDateTime(2023, 11, 5, 1, 30)
 * val instant2 = ambiguous.toInstant(zone) // Uses the earlier occurrence
 * ```
 *
 * ### Available Time Zone IDs
 *
 * The set of available time zone IDs can be queried:
 * ```
 * val allZones = TimeZone.availableZoneIds
 * println("Available zones: ${allZones.size}")
 * ```
 *
 * ### Platform Specifics
 *
 * - **JVM**: Uses `java.time.ZoneId` internally
 * - **JS**: Limited to system time zone and fixed offsets by default; full support requires `@js-joda/timezone` npm dependency
 * - **Native**: Uses the IANA Time Zone Database
 *
 * @see Instant for absolute time representation
 * @see LocalDateTime for civil time representation
 * @see FixedOffsetTimeZone for zones with constant UTC offset
 */
@Serializable(with = TimeZoneSerializer::class)
public expect open class TimeZone {
    /**
     * The identifier of this time zone.
     *
     * This identifier can be used with [TimeZone.of] to obtain the same time zone.
     *
     * ### Examples
     * - For region-based zones: `"Europe/Berlin"`, `"America/New_York"`
     * - For fixed-offset zones: `"UTC"`, `"+02:00"`, `"GMT-05:00"`
     * - For system zones: the actual system zone ID
     *
     * @see TimeZone.of for parsing these identifiers
     */
    public val id: String

    // TODO: Declare and document toString/equals/hashCode

    public companion object {
        /**
         * Returns the current system's default time zone.
         *
         * The returned time zone is the one configured in the operating system.
         * Note that this can change during the lifetime of the application if the user
         * changes their system settings.
         *
         * ### Platform Behavior
         *
         * - **JVM**: Returns the JVM's default time zone (`java.time.ZoneId.systemDefault()`)
         * - **JS**: Returns the browser's or Node.js system time zone
         * - **Native**: Queries the operating system for the current time zone setting
         *
         * ### Example
         * ```
         * val systemZone = TimeZone.currentSystemDefault()
         * println("System time zone: ${systemZone.id}")
         * 
         * val now = Clock.System.now()
         * val localTime = now.toLocalDateTime(systemZone)
         * ```
         *
         * ### Caching
         *
         * The result may be cached, but the cache is invalidated when system settings change.
         * Multiple calls to this function may return the same instance or different instances
         * representing the same time zone.
         */
        public fun currentSystemDefault(): TimeZone

        /**
         * The fixed time zone with zero offset from UTC.
         *
         * This is a [FixedOffsetTimeZone] with an offset of zero hours, minutes, and seconds.
         * It's equivalent to `TimeZone.of("UTC")` or `TimeZone.of("Z")`.
         *
         * ### Example
         * ```
         * val instant = Clock.System.now()
         * val utcDateTime = instant.toLocalDateTime(TimeZone.UTC)
         * println("UTC time: $utcDateTime")
         * ```
         *
         * @see FixedOffsetTimeZone for other fixed-offset zones
         */
        public val UTC: FixedOffsetTimeZone

        /**
         * Returns a time zone with the specified [zoneId].
         *
         * ### Supported ID Formats
         *
         * The following formats are supported:
         * - **`Z`**, **`UTC`**, **`UT`**, or **`GMT`**: Returns [UTC]
         * - **Fixed offsets**: Strings starting with `+`, `-`, or followed by offset
         *   - Examples: `"+02:00"`, `"-05:00"`, `"GMT+03:00"`, `"UTC-04:30"`
         *   - Format: `±HH:mm` or `±HHmm` or `±HH`
         * - **Region IDs**: IANA Time Zone Database identifiers
         *   - Examples: `"Europe/Berlin"`, `"America/New_York"`, `"Asia/Tokyo"`
         *
         * ### Examples
         * ```
         * val utc = TimeZone.of("UTC")
         * val berlin = TimeZone.of("Europe/Berlin")
         * val fixedPlus3 = TimeZone.of("+03:00")
         * val gmtMinus5 = TimeZone.of("GMT-05:00")
         * ```
         *
         * ### Platform Specifics
         *
         * - **JVM**: Supports all IANA time zone IDs available in the JVM
         * - **JS**: Without additional dependencies, only supports UTC and system zone; 
         *   with `@js-joda/timezone`, supports all IANA zones
         * - **Native**: Supports all IANA time zone IDs from the bundled database
         *
         * @param zoneId the time zone identifier
         * @return the corresponding TimeZone
         * @throws IllegalTimeZoneException if [zoneId] has an invalid format or refers to an unknown zone
         * @see availableZoneIds for the list of all available zone IDs
         */
        public fun of(zoneId: String): TimeZone

        /**
         * Returns the set of all available time zone identifiers.
         *
         * This includes all IANA Time Zone Database region IDs that can be used with [TimeZone.of].
         * Fixed offset IDs (like `"+02:00"`) are not included in this set, but they are still valid
         * for use with [TimeZone.of].
         *
         * ### Example
         * ```
         * val zones = TimeZone.availableZoneIds
         * println("Total zones available: ${zones.size}")
         * 
         * // Find all zones for a specific region
         * val europeanZones = zones.filter { it.startsWith("Europe/") }
         * println("European zones: $europeanZones")
         * ```
         *
         * ### Platform Specifics
         *
         * - **JVM**: Returns all zones from `java.time.ZoneId.getAvailableZoneIds()`
         * - **JS**: Limited set without `@js-joda/timezone`; full set with the dependency
         * - **Native**: Returns zones from the bundled IANA database
         *
         * The returned set is immutable and may be cached.
         */
        public val availableZoneIds: Set<String>
    }

    /**
     * Converts this [Instant] to a [LocalDateTime] in this time zone.
     *
     * The returned [LocalDateTime] represents the same moment in time as this instant,
     * but expressed in the civil time components of this time zone.
     *
     * ### Example
     * ```
     * val zone = TimeZone.of("America/New_York")
     * val instant = Instant.parse("2023-06-15T10:00:00Z")
     * 
     * zone.run {
     *     val local = instant.toLocalDateTime()
     *     println(local) // Will show the time in New York
     * }
     * ```
     *
     * @receiver the instant to convert
     * @return the corresponding LocalDateTime in this time zone
     * @throws DateTimeArithmeticException if this instant is too large to fit in [LocalDateTime]
     * @see LocalDateTime.toInstant for the inverse operation
     */
    public fun Instant.toLocalDateTime(): LocalDateTime

    /**
     * Converts this [LocalDateTime] to an [Instant] in this time zone.
     *
     * ### Handling Ambiguous or Non-Existent Times
     *
     * Due to daylight saving time transitions, the conversion may be ambiguous:
     * - **Non-existent times** (spring forward): The local time doesn't exist.
     *   The conversion uses the offset before the transition.
     * - **Ambiguous times** (fall back): The local time occurs twice.
     *   The conversion uses the earlier occurrence (before the transition).
     *
     * ### Example
     * ```
     * val zone = TimeZone.of("America/New_York")
     * val localDateTime = LocalDateTime(2023, 6, 15, 14, 30)
     * 
     * zone.run {
     *     val instant = localDateTime.toInstant()
     *     println(instant) // The absolute moment this local time represents
     * }
     * ```
     *
     * @receiver the LocalDateTime to convert
     * @return the corresponding Instant
     * @see Instant.toLocalDateTime for the inverse operation
     */
    public fun LocalDateTime.toInstant(): Instant
}

/**
 * A time zone with a fixed offset from UTC that never changes.
 *
 * This is a special case of [TimeZone] that maintains a constant offset from UTC,
 * without any daylight saving time transitions or historical changes.
 *
 * ### Creating Fixed Offset Time Zones
 *
 * Fixed offset time zones can be created in several ways:
 * ```
 * // From UtcOffset
 * val offset = UtcOffset(hours = 3)
 * val zone1 = offset.asTimeZone()
 * 
 * // Using TimeZone.of with offset string
 * val zone2 = TimeZone.of("+03:00") as FixedOffsetTimeZone
 * 
 * // Special case: UTC
 * val utc = TimeZone.UTC // This is a FixedOffsetTimeZone
 * ```
 *
 * ### Use Cases
 *
 * Fixed offset time zones are useful when:
 * - Working with systems that don't observe DST
 * - Storing or transmitting timestamps with a specific offset
 * - Testing time-dependent code with predictable behavior
 *
 * ### Example
 * ```
 * val offset = UtcOffset(hours = 5, minutes = 30)
 * val zone = offset.asTimeZone()
 * 
 * val instant = Clock.System.now()
 * val localTime = instant.toLocalDateTime(zone)
 * 
 * // The offset is always the same
 * val offset1 = zone.offsetAt(instant)
 * val offset2 = zone.offsetAt(instant + 6.months)
 * assert(offset1 == offset2) // Always true for fixed offset zones
 * ```
 *
 * @see UtcOffset for creating offset values
 * @see TimeZone for the general time zone interface
 */
@Serializable(with = FixedOffsetTimeZoneSerializer::class)
public expect class FixedOffsetTimeZone : TimeZone {
    /**
     * Creates a fixed-offset time zone with the specified [offset] from UTC.
     *
     * ### Example
     * ```
     * val offset = UtcOffset(hours = 2)
     * val zone = FixedOffsetTimeZone(offset)
     * 
     * // The zone ID will be the offset string
     * println(zone.id) // "+02:00"
     * ```
     *
     * @param offset the constant offset from UTC
     */
    public constructor(offset: UtcOffset)

    /**
     * The constant offset from UTC that this time zone maintains.
     *
     * This offset never changes, regardless of the date or time.
     *
     * ### Example
     * ```
     * val zone = TimeZone.of("+05:30") as FixedOffsetTimeZone
     * println(zone.offset.totalSeconds) // 19800 (5.5 hours in seconds)
     * ```
     */
    public val offset: UtcOffset

    @Deprecated("Use offset.totalSeconds", ReplaceWith("offset.totalSeconds"))
    public val totalSeconds: Int
}

@Deprecated("Use FixedOffsetTimeZone of UtcOffset instead", ReplaceWith("FixedOffsetTimeZone"))
public typealias ZoneOffset = FixedOffsetTimeZone

/**
 * Returns the offset from UTC this time zone has at the specified [instant].
 *
 * For region-based time zones, the offset can vary depending on daylight saving time transitions
 * and historical changes. For [FixedOffsetTimeZone], the offset is always the same.
 *
 * ### Example
 * ```
 * val zone = TimeZone.of("America/New_York")
 * val summerInstant = Instant.parse("2023-07-15T12:00:00Z")
 * val winterInstant = Instant.parse("2023-01-15T12:00:00Z")
 * 
 * val summerOffset = zone.offsetAt(summerInstant) // UTC-4 (EDT)
 * val winterOffset = zone.offsetAt(winterInstant) // UTC-5 (EST)
 * ```
 *
 * @param instant the instant to find the offset for
 * @return the UTC offset at this instant
 * @see Instant.offsetIn for a convenience extension
 */
public expect fun TimeZone.offsetAt(instant: Instant): UtcOffset

/**
 * Converts this instant to a [LocalDateTime] in the specified [timeZone].
 *
 * This is equivalent to calling `timeZone.run { toLocalDateTime() }`.
 *
 * ### Example
 * ```
 * val instant = Clock.System.now()
 * 
 * val utcTime = instant.toLocalDateTime(TimeZone.UTC)
 * val localTime = instant.toLocalDateTime(TimeZone.currentSystemDefault())
 * val tokyoTime = instant.toLocalDateTime(TimeZone.of("Asia/Tokyo"))
 * 
 * // All represent the same moment, but with different local times
 * ```
 *
 * @param timeZone the time zone to use for conversion
 * @return the LocalDateTime in the specified time zone
 * @throws DateTimeArithmeticException if this instant is too large to fit in [LocalDateTime]
 * @see LocalDateTime.toInstant for the inverse operation
 */
public expect fun Instant.toLocalDateTime(timeZone: TimeZone): LocalDateTime

/**
 * Returns a civil date/time value that this instant has in the specified [UTC offset][offset].
 *
 * @see LocalDateTime.toInstant
 * @see Instant.offsetIn
 */
internal expect fun Instant.toLocalDateTime(offset: UtcOffset): LocalDateTime

/**
 * Returns the offset from UTC that the specified [timeZone] has at this instant.
 *
 * This is a convenience function equivalent to `timeZone.offsetAt(this)`.
 *
 * ### Example
 * ```
 * val instant = Clock.System.now()
 * val offset = instant.offsetIn(TimeZone.currentSystemDefault())
 * println("Current UTC offset: $offset")
 * ```
 *
 * @param timeZone the time zone to query
 * @return the UTC offset at this instant in the given time zone
 * @see TimeZone.offsetAt
 */
public fun Instant.offsetIn(timeZone: TimeZone): UtcOffset =
        timeZone.offsetAt(this)

/**
 * Converts this [LocalDateTime] to an [Instant] using the specified [timeZone].
 *
 * This is equivalent to calling `timeZone.run { toInstant() }`.
 *
 * ### Handling DST Transitions
 *
 * See [TimeZone.toInstant] for details on how ambiguous and non-existent times are handled.
 *
 * ### Example
 * ```
 * val localDateTime = LocalDateTime(2023, 6, 15, 14, 30)
 * 
 * val utcInstant = localDateTime.toInstant(TimeZone.UTC)
 * val nyInstant = localDateTime.toInstant(TimeZone.of("America/New_York"))
 * 
 * // These represent different moments in time
 * ```
 *
 * @param timeZone the time zone to use for conversion
 * @return the corresponding Instant
 * @see Instant.toLocalDateTime for the inverse operation
 */
public expect fun LocalDateTime.toInstant(timeZone: TimeZone): Instant

/**
 * Converts this [LocalDateTime] to an [Instant] using the specified UTC [offset].
 *
 * This performs a direct conversion without any DST considerations, as the offset is fixed.
 *
 * ### Example
 * ```
 * val localDateTime = LocalDateTime(2023, 6, 15, 14, 30)
 * val offset = UtcOffset(hours = 3)
 * 
 * val instant = localDateTime.toInstant(offset)
 * ```
 *
 * @param offset the UTC offset to use for conversion
 * @return the corresponding Instant
 * @see Instant.toLocalDateTime for the inverse operation
 */
public expect fun LocalDateTime.toInstant(offset: UtcOffset): Instant

/**
 * Returns an [Instant] that corresponds to the start of this date in the specified [timeZone].
 *
 * The "start of day" is usually midnight (00:00), but this is not always the case.
 * For example, due to daylight saving time transitions, a day might start at 01:00 if
 * the clock was moved forward from 23:59 to 01:00.
 *
 * ### Example
 * ```
 * val date = LocalDate(2023, 3, 26) // DST transition in Europe
 * val berlin = TimeZone.of("Europe/Berlin")
 * 
 * val startOfDay = date.atStartOfDayIn(berlin)
 * val localTime = startOfDay.toLocalDateTime(berlin)
 * // localTime.time might not be 00:00 if there was a DST transition
 * ```
 *
 * ### Comparison with Other Approaches
 *
 * This is more reliable than `date.atTime(0, 0).toInstant(timeZone)` because:
 * - It handles cases where midnight doesn't exist due to DST
 * - It correctly identifies the first valid moment of the day
 *
 * @param timeZone the time zone to determine the start of day
 * @return the instant at the start of this date in the given time zone
 */
public expect fun LocalDate.atStartOfDayIn(timeZone: TimeZone): Instant