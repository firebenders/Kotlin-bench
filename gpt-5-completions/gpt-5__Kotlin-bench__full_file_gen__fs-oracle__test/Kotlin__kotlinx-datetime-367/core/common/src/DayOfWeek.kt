/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

/**
 * The enumeration class representing the days of the week (ISO‑8601).
 *
 * What it represents
 * - Seven days of the ISO‑8601 week, from [MONDAY] to [SUNDAY].
 *
 * Acquisition
 * - From a [LocalDate] via [LocalDate.dayOfWeek].
 * - From an ISO day number via the factory [DayOfWeek].
 * - When parsing text with [kotlinx.datetime.format] (see [DateTimeFormatBuilder.WithDate.dayOfWeek]).
 *
 * Usage
 * - Get the ISO day number via [isoDayNumber] (Monday is 1, Sunday is 7).
 * - Switch on the day of week in calendar logic.
 *
 * Example:
 * ```
 * val date = LocalDate(2024, 1, 1)
 * val dow = date.dayOfWeek // TUESDAY
 * println("ISO day number is ${dow.isoDayNumber}") // 2
 * ```
 */
public expect enum class DayOfWeek {
    MONDAY,
    TUESDAY,
    WEDNESDAY,
    THURSDAY,
    FRIDAY,
    SATURDAY,
    SUNDAY;
}

/**
 * The ISO-8601 number of the given day of the week. Monday is 1, Sunday is 7.
 */
public val DayOfWeek.isoDayNumber: Int get() = ordinal + 1

/**
 * Returns the [DayOfWeek] instance for the given ISO-8601 week day number. Monday is 1, Sunday is 7.
 *
 * @throws IllegalArgumentException if [isoDayNumber] is outside 1..7.
 */
public fun DayOfWeek(isoDayNumber: Int): DayOfWeek {
    require(isoDayNumber in 1..7) { "Expected ISO day-of-week number in 1..7, got $isoDayNumber" }
    return DayOfWeek.entries[isoDayNumber - 1]
}