/*
 * Copyright 2019-2022 JetBrains s.r.o. and contributors.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */
package kotlinx.datetime

import kotlinx.datetime.format.*
import kotlinx.datetime.format.ISO_DATETIME
import kotlinx.datetime.format.LocalDateTimeFormat
import kotlinx.datetime.serializers.LocalDateTimeIso8601Serializer
import kotlinx.serialization.Serializable
import kotlinx.datetime.internal.JSJoda.LocalDateTime as jtLocalDateTime

@Serializable(with = LocalDateTimeIso8601Serializer::class)
public actual class LocalDateTime internal constructor(internal val value: jtLocalDateTime) : Comparable<LocalDateTime> {

    public actual constructor(year: Int, monthNumber: Int, dayOfMonth: Int, hour: Int, minute: Int, second: Int, nanosecond: Int) :
            this(try {
                jsTry { jtLocalDateTime.of(year, monthNumber, dayOfMonth, hour, minute, second, nanosecond) }
            } catch (e: Throwable) {
                if (e.isJodaDateTimeException()) throw IllegalArgumentException(e)
                throw e
            })

    public actual constructor(year: Int, month: Month, dayOfMonth: Int, hour: Int, minute: Int, second: Int, nanosecond: Int) :
            this(year, month.number, dayOfMonth, hour, minute, second, nanosecond)

    public actual constructor(date: LocalDate, time: LocalTime) :
            this(jsTry { jtLocalDateTime.of(date.value, time.value) })

    public actual val year: Int get() = value.year()
    public actual val monthNumber: Int get() = value.monthValue()
    public actual val month: Month get() = value.month().toMonth()
    public actual val dayOfMonth: Int get() = value.dayOfMonth()
    public actual val dayOfWeek: DayOfWeek get() = value.dayOfWeek().toDayOfWeek()
    public actual val dayOfYear: Int get() = value.dayOfYear()

    public actual val hour: Int get() = value.hour()
    public actual val minute: Int get() = value.minute()
    public actual val second: Int get() = value.second()
    public actual val nanosecond: Int get() = value.nano().toInt()

    public actual val date: LocalDate get() = LocalDate(value.toLocalDate()) // cache?

    public actual val time: LocalTime get() = LocalTime(value.toLocalTime())

    override fun equals(other: Any?): Boolean =
            (this === other) || (other is LocalDateTime && (this.value === other.value || this.value.equals(other.value)))

    override fun hashCode(): Int = value.hashCode()

    actual override fun toString(): String = value.toString()

    actual override fun compareTo(other: LocalDateTime): Int = this.value.compareTo(other.value)

    public actual companion object {
        public actual fun parse(input: CharSequence, format: DateTimeFormat<LocalDateTime>): LocalDateTime =
            if (format === Formats.ISO) {
                parseIsoString(input.toString())
            } else {
                format.parse(input)
            }

        private fun parseIsoString(input: String): LocalDateTime {
            // Check if we have excessive leading zeroes that js-joda can't handle
            val normalizedInput = normalizeIsoDateTimeString(input)
            return try {
                jsTry { jtLocalDateTime.parse(normalizedInput) }.let(::LocalDateTime)
            } catch (e: Throwable) {
                if (e.isJodaDateTimeParseException()) throw DateTimeFormatException(e)
                throw e
            }
        }

        private fun normalizeIsoDateTimeString(input: String): String {
            // Pattern: [+|-]YYYY-MM-DD'T'HH:mm:ss[.nnnnnnnnn]
            // We need to handle cases like +00000000000002022-07-16T12:30:00
            val trimmed = input.trim()
            if (trimmed.isEmpty()) return input
            
            var pos = 0
            val isNegative = trimmed[0] == '-'
            val hasSign = trimmed[0] == '+' || trimmed[0] == '-'
            if (hasSign) pos = 1
            
            // Find where the year ends (either at '-' or 'T' for basic format)
            var yearEnd = pos
            while (yearEnd < trimmed.length && trimmed[yearEnd] != '-' && trimmed[yearEnd] != 'T') {
                yearEnd++
            }
            
            if (yearEnd == pos) return input // No year digits
            
            val yearStr = trimmed.substring(pos, yearEnd)
            
            // Check if year has excessive leading zeroes
            if (yearStr.length <= 4) {
                // No excessive zeroes or js-joda can handle it
                return input
            }
            
            // Remove excessive leading zeroes
            var firstNonZero = 0
            while (firstNonZero < yearStr.length - 1 && yearStr[firstNonZero] == '0') {
                firstNonZero++
            }
            
            // Keep at least 4 digits for the year
            val significantDigits = yearStr.length - firstNonZero
            val digitsToKeep = maxOf(4, significantDigits)
            val startPos = yearStr.length - digitsToKeep
            
            val normalizedYear = yearStr.substring(startPos)
            val restOfDateTime = trimmed.substring(yearEnd)
            
            return buildString {
                if (isNegative) append('-')
                else if (hasSign && normalizedYear != "0000") append('+')
                append(normalizedYear)
                append(restOfDateTime)
            }
        }

        @Deprecated("This overload is only kept for binary compatibility", level = DeprecationLevel.HIDDEN)
        public fun parse(isoString: String): LocalDateTime = parse(input = isoString)

        internal actual val MIN: LocalDateTime = LocalDateTime(jtLocalDateTime.MIN)
        internal actual val MAX: LocalDateTime = LocalDateTime(jtLocalDateTime.MAX)

        @Suppress("FunctionName")
        public actual fun Format(builder: DateTimeFormatBuilder.WithDateTime.() -> Unit): DateTimeFormat<LocalDateTime> =
            LocalDateTimeFormat.build(builder)
    }

    public actual object Formats {
        public actual val ISO: DateTimeFormat<LocalDateTime> = ISO_DATETIME
    }

}