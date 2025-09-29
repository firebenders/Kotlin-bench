package org.wordpress.android.ui.deeplinks.handlers

import org.wordpress.android.fluxc.model.SiteModel
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction.OpenStats
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction.OpenStatsForSite
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction.OpenStatsForSiteAndTimeframe
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction.OpenStatsForTimeframe
import org.wordpress.android.ui.deeplinks.DeepLinkNavigator.NavigateAction.OpenJetpackStaticPosterView
import org.wordpress.android.ui.deeplinks.DeepLinkUriUtils
import org.wordpress.android.ui.deeplinks.DeepLinkingIntentReceiverViewModel.Companion.APPLINK_SCHEME
import org.wordpress.android.ui.deeplinks.DeepLinkingIntentReceiverViewModel.Companion.HOST_WORDPRESS_COM
import org.wordpress.android.ui.deeplinks.DeepLinkingIntentReceiverViewModel.Companion.SITE_DOMAIN
import org.wordpress.android.ui.jetpackoverlay.JetpackFeatureRemovalPhaseHelper
import org.wordpress.android.ui.stats.StatsTimeframe
import org.wordpress.android.util.UriWrapper
import javax.inject.Inject

class StatsLinkHandler
@Inject constructor(
    private val deepLinkUriUtils: DeepLinkUriUtils,
    private val jetpackFeatureRemovalPhaseHelper: JetpackFeatureRemovalPhaseHelper
) : DeepLinkHandler {
    /**
     * Builds navigate action from URL like:
     * https://wordpress.com/stats/$timeframe/$site
     * where timeframe and site are optional
     * or
     * https://wordpress.com/stats/traffic/$timeframe/$site
     * or
     * https://wordpress.com/stats/subscribers/$site
     * or
     * wordpress://stats
     *
     * Note: For "traffic" links, the granularity is provided as $timeframe (day|week|month|year).
     * For "subscribers" links there is no timeframe and we will just navigate to stats. The UI layer
     * will route to the correct tab based on the original URI.
     */
    override fun buildNavigateAction(uri: UriWrapper): NavigateAction {
        val pathSegments = uri.pathSegments
        val length = pathSegments.size

        // We support both "stats/$timeframe/$site" and "stats/traffic/$timeframe/$site".
        // In both cases, the timeframe is the second-to-last segment and the site is the last segment.
        val site = pathSegments.getOrNull(length - 1)?.toSite()
        val statsTimeframe = pathSegments.getOrNull(length - 2)?.toStatsTimeframe()

        return when {
            jetpackFeatureRemovalPhaseHelper.shouldShowStaticPage() -> OpenJetpackStaticPosterView
            site != null && statsTimeframe != null -> {
                OpenStatsForSiteAndTimeframe(site, statsTimeframe)
            }
            site != null -> {
                OpenStatsForSite(site)
            }
            statsTimeframe != null -> {
                OpenStatsForTimeframe(statsTimeframe)
            }
            else -> {
                // In other cases, launch stats with the current selected site.
                OpenStats
            }
        }
    }

    /**
     * Returns true if the URI should be handled by StatsLinkHandler.
     * The handled links are:
     *  - https://wordpress.com/stats/day/$site
     *  - https://wordpress.com/stats/traffic/day/$site
     *  - https://wordpress.com/stats/subscribers/$site
     *  - wordpress://stats
     */
    override fun shouldHandleUrl(uri: UriWrapper): Boolean {
        return (uri.host == HOST_WORDPRESS_COM &&
                uri.pathSegments.firstOrNull() == STATS_PATH) || uri.host == STATS_PATH
    }

    override fun stripUrl(uri: UriWrapper): String {
        return buildString {
            val isAppLink = uri.host == STATS_PATH
            val offset = if (isAppLink) {
                append(APPLINK_SCHEME)
                0
            } else {
                append("$HOST_WORDPRESS_COM/")
                1
            }
            append(STATS_PATH)

            val pathSegments = uri.pathSegments
            val size = pathSegments.size

            // Determine if this is a /stats/traffic/... link so that we can normalize correctly.
            val firstAfterStats = if (size > offset) pathSegments.getOrNull(offset) else null
            val isTraffic = firstAfterStats == TRAFFIC_PATH
            val statsTimeframe = when {
                isTraffic -> if (size > offset + 1) pathSegments.getOrNull(offset + 1) else null
                else -> firstAfterStats
            }
            val hasSiteUrl = when {
                isTraffic -> if (size > offset + 2) pathSegments.getOrNull(offset + 2) != null else false
                else -> if (size > offset + 1) pathSegments.getOrNull(offset + 1) != null else false
            }

            if (isTraffic) {
                append("/$TRAFFIC_PATH")
            }
            if (statsTimeframe != null) {
                append("/$statsTimeframe")
            }
            if (hasSiteUrl) {
                append("/$SITE_DOMAIN")
            }
        }
    }

    /**
     * Converts HOST name of a site to SiteModel. It finds the Site in the current local sites and matches the name
     * to the host.
     */
    private fun String.toSite(): SiteModel? {
        return deepLinkUriUtils.hostToSite(this)
    }

    private fun String.toStatsTimeframe(): StatsTimeframe? {
        return when (this) {
            "day" -> StatsTimeframe.DAY
            "week" -> StatsTimeframe.WEEK
            "month" -> StatsTimeframe.MONTH
            "year" -> StatsTimeframe.YEAR
            "insights" -> StatsTimeframe.INSIGHTS
            // "traffic" and "subscribers" are not timeframes. They are handled at UI level.
            else -> null
        }
    }

    companion object {
        private const val STATS_PATH = "stats"
        private const val TRAFFIC_PATH = "traffic"
    }
}