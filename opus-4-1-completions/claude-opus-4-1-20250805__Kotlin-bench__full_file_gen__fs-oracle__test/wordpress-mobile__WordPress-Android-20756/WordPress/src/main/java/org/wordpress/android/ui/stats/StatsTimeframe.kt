package org.wordpress.android.ui.stats

import androidx.annotation.StringRes
import org.wordpress.android.R

enum class StatsTimeframe(@StringRes val titleRes: Int) {
    DAY(R.string.stats_timeframe_days),
    WEEK(R.string.stats_timeframe_weeks),
    MONTH(R.string.stats_timeframe_months),
    YEAR(R.string.stats_timeframe_years),
    INSIGHTS(R.string.stats_insights),
    TRAFFIC(R.string.stats_traffic),
    SUBSCRIBERS(R.string.stats_subscribers);
    
    /**
     * Special case for traffic tab with a specific granularity.
     * This allows deep linking to the traffic tab with a pre-selected time period.
     */
    data class TRAFFIC_WITH_GRANULARITY(val granularity: StatsTimeframe) : StatsTimeframe(R.string.stats_traffic) {
        init {
            require(granularity in listOf(DAY, WEEK, MONTH, YEAR)) {
                "Granularity must be DAY, WEEK, MONTH, or YEAR"
            }
        }
    }
    
    companion object {
        fun from(value: String): StatsTimeframe? {
            return values().find { it.name.equals(value, ignoreCase = true) }
        }
    }
}