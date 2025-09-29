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
     * https://wordpress.com/stats/subscribers/$site
     * https://wordpress.com/stats/traffic/$granularity/$site
     * where timeframe, granularity and site are optional
     * or
     * wordpress://stats
     * wordpress://stats/subscribers
     * wordpress://stats/traffic/$granularity
     */
    override fun buildNavigateAction(uri: UriWrapper): NavigateAction {
        val pathSegments = uri.pathSegments
        val isAppLink = uri.host == STATS_PATH
        val startIndex = if (isAppLink) 0 else 1 // Skip "stats" segment for wordpress.com URLs
        
        return when {
            jetpackFeatureRemovalPhaseHelper.shouldShowStaticPage() -> OpenJetpackStaticPosterView
            else -> {
                // Check if this is a subscribers or traffic deep link
                val firstSegment = pathSegments.getOrNull(startIndex)
                when (firstSegment) {
                    SUBSCRIBERS_PATH -> {
                        val site = pathSegments.getOrNull(startIndex + 1)?.toSite()
                        if (site != null) {
                            OpenStatsForSiteAndTimeframe(site, StatsTimeframe.SUBSCRIBERS)
                        } else {
                            OpenStatsForTimeframe(StatsTimeframe.SUBSCRIBERS)
                        }
                    }
                    TRAFFIC_PATH -> {
                        // For traffic, check if there's a granularity specified
                        val granularity = pathSegments.getOrNull(startIndex + 1)?.toStatsTimeframe()
                        val site = if (granularity != null) {
                            pathSegments.getOrNull(startIndex + 2)?.toSite()
                        } else {
                            pathSegments.getOrNull(startIndex + 1)?.toSite()
                        }
                        
                        when {
                            site != null && granularity != null -> {
                                // Traffic with specific granularity and site
                                OpenStatsForSiteAndTimeframe(site, StatsTimeframe.TRAFFIC_WITH_GRANULARITY(granularity))
                            }
                            site != null -> {
                                // Traffic with site but no granularity
                                OpenStatsForSiteAndTimeframe(site, StatsTimeframe.TRAFFIC)
                            }
                            granularity != null -> {
                                // Traffic with granularity but no site
                                OpenStatsForTimeframe(StatsTimeframe.TRAFFIC_WITH_GRANULARITY(granularity))
                            }
                            else -> {
                                // Just traffic tab
                                OpenStatsForTimeframe(StatsTimeframe.TRAFFIC)
                            }
                        }
                    }
                    else -> {
                        // Original logic for regular stats deep links
                        val length = pathSegments.size
                        val site = pathSegments.getOrNull(length - 1)?.toSite()
                        val statsTimeframe = pathSegments.getOrNull(length - 2)?.toStatsTimeframe()
                        when {
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
                }
            }
        }
    }

    /**
     * Returns true if the URI should be handled by StatsLinkHandler.
     * The handled links are `https://wordpress.com/stats/...` and `wordpress://stats...`
     */
    override fun shouldHandleUrl(uri: UriWrapper): Boolean {
        return (uri.host == HOST_WORDPRESS_COM &&
                uri.pathSegments.firstOrNull() == STATS_PATH) || uri.host == STATS_PATH
    }

    override fun stripUrl(uri: UriWrapper): String {
        return buildString {
            val offset = if (uri.host == STATS_PATH) {
                append(APPLINK_SCHEME)
                0
            } else {
                append("$HOST_WORDPRESS_COM/")
                1
            }
            append(STATS_PATH)
            val pathSegments = uri.pathSegments
            val size = pathSegments.size
            
            // Check if this is a subscribers or traffic link
            val firstSegment = pathSegments.getOrNull(offset)
            when (firstSegment) {
                SUBSCRIBERS_PATH -> {
                    append("/$SUBSCRIBERS_PATH")
                    val hasSiteUrl = pathSegments.getOrNull(offset + 1) != null
                    if (hasSiteUrl) {
                        append("/$SITE_DOMAIN")
                    }
                }
                TRAFFIC_PATH -> {
                    append("/$TRAFFIC_PATH")
                    val granularity = pathSegments.getOrNull(offset + 1)?.toStatsTimeframe()
                    if (granularity != null) {
                        append("/${pathSegments[offset + 1]}")
                        val hasSiteUrl = pathSegments.getOrNull(offset + 2) != null
                        if (hasSiteUrl) {
                            append("/$SITE_DOMAIN")
                        }
                    } else {
                        val hasSiteUrl = pathSegments.getOrNull(offset + 1) != null
                        if (hasSiteUrl) {
                            append("/$SITE_DOMAIN")
                        }
                    }
                }
                else -> {
                    // Original logic
                    val statsTimeframe = if (size > offset) pathSegments.getOrNull(offset) else null
                    val hasSiteUrl = if (size > offset + 1) pathSegments.getOrNull(offset + 1) != null else false
                    if (statsTimeframe != null) {
                        append("/$statsTimeframe")
                    }
                    if (hasSiteUrl) {
                        append("/$SITE_DOMAIN")
                    }
                }
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
            else -> null
        }
    }

    companion object {
        private const val STATS_PATH = "stats"
        private const val SUBSCRIBERS_PATH = "subscribers"
        private const val TRAFFIC_PATH = "traffic"
    }
}