/*
 * Copyright 2019-2020 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime

import kotlinx.datetime.format.*
import kotlinx.datetime.serializers.LocalDateIso8601Serializer
import kotlinx.serialization.Serializable
import kotlinx.datetime.internal.JSJoda.LocalDate as jtLocalDate
import kotlinx.datetime.internal.JSJoda.ChronoUnit as jtChronoUnit

@Serializable(with = LocalDateIso8601Serializer::class)
public actual class LocalDate internal constructor(internal val value: jtLocalDate) : Comparable<LocalDate> {
    public actual companion object {

        public actual fun parse(
            input: CharSequence,
            format: DateTimeFormat<LocalDate>
        ): LocalDate = if (format === Formats.ISO) {
            parseIsoString(input.toString())
        } else {
            format.parse(input)
        }

        private fun parseIsoString(input: String): LocalDate {
            // Check if we have excessive leading zeroes that js-joda can't handle
            val normalizedInput = normalizeIsoDateString(input)
            return try {
                jsTry { jtLocalDate.parse(normalizedInput) }.let(::LocalDate)
            } catch (e: Throwable) {
                if (e.isJodaDateTimeParseException()) throw DateTimeFormatException(e)
                throw e
            }
        }

        private fun normalizeIsoDateString(input: String): String {
            // Pattern: [+|-]YYYY-MM-DD
            // We need to handle cases like +00000000000002022-07-16
            val trimmed = input.trim()
            if (trimmed.isEmpty()) return input
            
            var pos = 0
            val isNegative = trimmed[0] == '-'
            val hasSign = trimmed[0] == '+' || trimmed[0] == '-'
            if (hasSign) pos = 1
            
            // Find where the year ends (either at '-' or end of string for basic format)
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
            val restOfDate = trimmed.substring(yearEnd)
            
            return buildString {
                if (isNegative) append('-')
                else if (hasSign && normalizedYear != "0000") append('+')
                append(normalizedYear)
                append(restOfDate)
            }
        }

        @Deprecated("This overload is only kept for binary compatibility", level = DeprecationLevel.HIDDEN)
        public fun parse(isoString: String): LocalDate = parse(input = isoString)

        internal actual val MIN: LocalDate = LocalDate(jtLocalDate.MIN)
        internal actual val MAX: LocalDate = LocalDate(jtLocalDate.MAX)

        public actual fun fromEpochDays(epochDays: Int): LocalDate = try {
            LocalDate(jsTry { jtLocalDate.ofEpochDay(epochDays) })
        } catch (e: Throwable) {
            if (e.isJodaDateTimeException()) throw IllegalArgumentException(e)
            throw e
        }

        @Suppress("FunctionName")
        public actual fun Format(block: DateTimeFormatBuilder.WithDate.() -> Unit): DateTimeFormat<LocalDate> =
            LocalDateFormat.build(block)
    }

    public actual object Formats {
        public actual val ISO: DateTimeFormat<LocalDate> get() = ISO_DATE

        public actual val ISO_BASIC: DateTimeFormat<LocalDate> = ISO_DATE_BASIC
    }

    public actual constructor(year: Int, monthNumber: Int, dayOfMonth: Int) :
            this(try {
                jsTry { jtLocalDate.of(year, monthNumber, dayOfMonth) }
            } catch (e: Throwable) {
                if (e.isJodaDateTimeException()) throw IllegalArgumentException(e)
                throw e
            })

    public actual constructor(year: Int, month: Month, dayOfMonth: Int) : this(year, month.number, dayOfMonth)

    public actual val year: Int get() = value.year()
    public actual val monthNumber: Int get() = value.monthValue()
    public actual val month: Month get() = value.month().toMonth()
    public actual val dayOfMonth: Int get() = value.dayOfMonth()
    public actual val dayOfWeek: DayOfWeek get() = value.dayOfWeek().toDayOfWeek()
    public actual val dayOfYear: Int get() = value.dayOfYear()

    override fun equals(other: Any?): Boolean =
            (this === other) || (other is LocalDate && (this.value === other.value || this.value.equals(other.value)))

    override fun hashCode(): Int = value.hashCode()

    actual override fun toString(): String = value.toString()

    actual override fun compareTo(other: LocalDate): Int = this.value.compareTo(other.value)

    public actual fun toEpochDays(): Int = value.toEpochDay().toInt()
}

@Deprecated("Use the plus overload with an explicit number of units", ReplaceWith("this.plus(1, unit)"))
public actual fun LocalDate.plus(unit: DateTimeUnit.DateBased): LocalDate = plusNumber(1, unit)
public actual fun LocalDate.plus(value: Int, unit: DateTimeUnit.DateBased): LocalDate = plusNumber(value, unit)
public actual fun LocalDate.minus(value: Int, unit: DateTimeUnit.DateBased): LocalDate = plusNumber(-value, unit)
public actual fun LocalDate.plus(value: Long, unit: DateTimeUnit.DateBased): LocalDate = plusNumber(value, unit)

private fun LocalDate.plusNumber(value: Number, unit: DateTimeUnit.DateBased): LocalDate =
        try {
            when (unit) {
                is DateTimeUnit.DayBased -> jsTry { this.value.plusDays((value.toDouble() * unit.days).toInt()) }
                is DateTimeUnit.MonthBased -> jsTry { this.value.plusMonths((value.toDouble() * unit.months).toInt()) }
            }.let(::LocalDate)
        } catch (e: Throwable) {
            if (!e.isJodaDateTimeException() && !e.isJodaArithmeticException()) throw e
            throw DateTimeArithmeticException("The result of adding $value of $unit to $this is out of LocalDate range.", e)
        }


public actual operator fun LocalDate.plus(period: DatePeriod): LocalDate = try {
    with(period) {
        return@with value
                .run { if (totalMonths != 0) jsTry { plusMonths(totalMonths) } else this }
                .run { if (days != 0) jsTry { plusDays(days) } else this }

    }.let(::LocalDate)
} catch (e: Throwable) {
    if (e.isJodaDateTimeException() || e.isJodaArithmeticException()) throw DateTimeArithmeticException(e)
    throw e
}



public actual fun LocalDate.periodUntil(other: LocalDate): DatePeriod {
    var startD = this.value
    val endD = other.value
    val months = startD.until(endD, jtChronoUnit.MONTHS).toInt(); startD = jsTry { startD.plusMonths(months) }
    val days = startD.until(endD, jtChronoUnit.DAYS).toInt()

    return DatePeriod(totalMonths = months, days)
}

public actual fun LocalDate.until(other: LocalDate, unit: DateTimeUnit.DateBased): Int = when(unit) {
    is DateTimeUnit.MonthBased -> monthsUntil(other) / unit.months
    is DateTimeUnit.DayBased -> daysUntil(other) / unit.days
}

public actual fun LocalDate.daysUntil(other: LocalDate): Int =
        this.value.until(other.value, jtChronoUnit.DAYS).toInt()

public actual fun LocalDate.monthsUntil(other: LocalDate): Int =
        this.value.until(other.value, jtChronoUnit.MONTHS).toInt()

public actual fun LocalDate.yearsUntil(other: LocalDate): Int =
        this.value.until(other.value, jtChronoUnit.YEARS).toInt()