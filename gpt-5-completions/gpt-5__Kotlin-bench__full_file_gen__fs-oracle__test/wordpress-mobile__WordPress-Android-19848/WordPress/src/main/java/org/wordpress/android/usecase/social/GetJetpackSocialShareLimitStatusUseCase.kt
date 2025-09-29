package org.wordpress.android.usecase.social

import org.wordpress.android.fluxc.model.SiteModel
import org.wordpress.android.fluxc.store.SiteStore
import org.wordpress.android.fluxc.store.SiteStore.FetchedJetpackSocialResult
import org.wordpress.android.util.extensions.doesNotContain
import javax.inject.Inject

class GetJetpackSocialShareLimitStatusUseCase @Inject constructor(
    private val siteStore: SiteStore,
) {
    /**
     * Determines whether Jetpack Social share limits should be shown for the given site.
     *
     * Share limits should NOT be shown for:
     * - WordPress.com hosted sites
     * - Atomic (WordPress.com-hosted) sites
     *
     * They may be shown for self-hosted Jetpack sites that don't include the specific "social-shares-1000"
     * active feature (i.e., limits apply).
     */
    suspend fun execute(siteModel: SiteModel): ShareLimit {
        // Do not show share limits for WP.com-hosted or Atomic sites
        val isNonAtomicSelfHosted = !siteModel.isHostedAtWPCom && !siteModel.isWPComAtomic

        // Only enable share limits if the site is eligible and doesn't explicitly include the 1000-shares feature
        val isShareLimitEnabled =
            isNonAtomicSelfHosted &&
                (siteModel.planActiveFeatures?.split(",")?.doesNotContain(FEATURE_SOCIAL_SHARES_1000) != false)

        val result = siteStore.fetchJetpackSocial(siteModel)
        return if (isShareLimitEnabled && result is FetchedJetpackSocialResult.Success) {
            with(result.jetpackSocial) {
                ShareLimit.Enabled(
                    shareLimit = shareLimit,
                    publicizedCount = publicizedCount,
                    sharedPostsCount = sharedPostsCount,
                    sharesRemaining = sharesRemaining,
                )
            }
        } else {
            ShareLimit.Disabled
        }
    }
}

sealed interface ShareLimit {
    data class Enabled(
        val shareLimit: Int,
        val publicizedCount: Int,
        val sharedPostsCount: Int,
        val sharesRemaining: Int,
    ) : ShareLimit

    object Disabled : ShareLimit
}

private const val FEATURE_SOCIAL_SHARES_1000 = "social-shares-1000"