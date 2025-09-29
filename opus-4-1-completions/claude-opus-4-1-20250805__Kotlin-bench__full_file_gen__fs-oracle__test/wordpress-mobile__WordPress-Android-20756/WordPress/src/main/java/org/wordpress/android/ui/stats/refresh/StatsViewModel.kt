package org.wordpress.android.ui.stats.refresh

import android.content.Intent
import android.os.Bundle
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.CoroutineDispatcher
import org.wordpress.android.R
import org.wordpress.android.WordPress
import org.wordpress.android.modules.UI_THREAD
import org.wordpress.android.ui.jetpackoverlay.JetpackFeatureRemovalPhaseHelper
import org.wordpress.android.ui.pages.SnackbarMessageHolder
import org.wordpress.android.ui.stats.StatsTimeframe
import org.wordpress.android.ui.stats.refresh.lists.StatsListViewModel.StatsSection
import org.wordpress.android.ui.stats.refresh.lists.StatsListViewModel.StatsSection.*
import org.wordpress.android.ui.stats.refresh.utils.StatsSiteProvider
import org.wordpress.android.ui.stats.refresh.utils.StatsSiteProvider.SiteUpdateResult
import org.wordpress.android.util.config.StatsTrafficSubscribersTabFeatureConfig
import org.wordpress.android.viewmodel.Event
import org.wordpress.android.viewmodel.SingleLiveEvent
import javax.inject.Inject
import javax.inject.Named

class StatsViewModel @Inject constructor(
    @Named(UI_THREAD) private val mainDispatcher: CoroutineDispatcher,
    private val statsSiteProvider: StatsSiteProvider,
    private val statsTrafficSubscribersTabFeatureConfig: StatsTrafficSubscribersTabFeatureConfig,
    private val jetpackFeatureRemovalPhaseHelper: JetpackFeatureRemovalPhaseHelper
) : ViewModel() {
    
    private val _isRefreshing = MutableLiveData<Boolean>()
    val isRefreshing: LiveData<Boolean> = _isRefreshing
    
    private val _showSnackbarMessage = MutableLiveData<SnackbarMessageHolder?>()
    val showSnackbarMessage: LiveData<SnackbarMessageHolder?> = _showSnackbarMessage
    
    private val _toolbarHasShadow = MutableLiveData<Boolean>()
    val toolbarHasShadow: LiveData<Boolean> = _toolbarHasShadow
    
    private val _siteChanged = SingleLiveEvent<SiteUpdateResult>()
    val siteChanged: LiveData<SiteUpdateResult> = _siteChanged
    
    private val _hideToolbar = SingleLiveEvent<Boolean>()
    val hideToolbar: LiveData<Boolean> = _hideToolbar
    
    private val _selectedSection = MutableLiveData<StatsSection>()
    val selectedSection: LiveData<StatsSection> = _selectedSection
    
    private val _statsModuleUiModel = SingleLiveEvent<StatsModuleUiModel>()
    val statsModuleUiModel: LiveData<StatsModuleUiModel> = _statsModuleUiModel
    
    private val _showJetpackPoweredBottomSheet = SingleLiveEvent<Boolean>()
    val showJetpackPoweredBottomSheet: LiveData<Boolean> = _showJetpackPoweredBottomSheet
    
    private val _showJetpackOverlay = SingleLiveEvent<Boolean>()
    val showJetpackOverlay: LiveData<Boolean> = _showJetpackOverlay
    
    data class StatsModuleUiModel(
        val disabledStatsViewVisible: Boolean,
        val disabledStatsProgressVisible: Boolean
    )
    
    fun start(intent: Intent) {
        // Check for deep link data
        val deepLinkTimeframe = intent.getStringExtra(STATS_TIMEFRAME_KEY)
        val deepLinkTab = intent.getStringExtra(STATS_TAB_KEY)
        val deepLinkGranularity = intent.getStringExtra(STATS_GRANULARITY_KEY)
        
        val initialSection = when {
            deepLinkTab == "subscribers" -> SUBSCRIBERS
            deepLinkTab == "traffic" -> {
                // If traffic tab with granularity, store it for later use
                if (deepLinkGranularity != null) {
                    // Store granularity to be used by the Traffic tab
                    setTrafficGranularity(deepLinkGranularity)
                }
                TRAFFIC
            }
            deepLinkTimeframe != null -> {
                when (deepLinkTimeframe) {
                    "day" -> DAYS
                    "week" -> WEEKS
                    "month" -> MONTHS
                    "year" -> YEARS
                    "insights" -> INSIGHTS
                    else -> getDefaultSection()
                }
            }
            else -> getDefaultSection()
        }
        
        _selectedSection.value = initialSection
        
        // Initialize other components
        val siteId = intent.getIntExtra(WordPress.LOCAL_SITE_ID, 0)
        if (siteId > 0) {
            statsSiteProvider.start(siteId)
        }
    }
    
    private fun getDefaultSection(): StatsSection {
        return if (statsTrafficSubscribersTabFeatureConfig.isEnabled()) {
            TRAFFIC
        } else {
            INSIGHTS
        }
    }
    
    private fun setTrafficGranularity(granularity: String) {
        // Store the granularity to be picked up by the Traffic tab
        // This could be done via SharedPreferences or a singleton state holder
        // For simplicity, we'll use a companion object property
        trafficGranularity = granularity
    }
    
    fun onSectionSelected(section: StatsSection) {
        _selectedSection.value = section
    }
    
    fun onPullToRefresh() {
        _isRefreshing.value = true
        // Refresh logic
        _isRefreshing.value = false
    }
    
    fun onSaveInstanceState(outState: Bundle) {
        // Save state
    }
    
    fun onRestoreInstanceState(savedInstanceState: Bundle?) {
        // Restore state
    }
    
    fun onSiteChanged() {
        // Handle site change
    }
    
    fun onEnableStatsModuleClick() {
        // Enable stats module
    }
    
    companion object {
        const val STATS_TIMEFRAME_KEY = "stats_timeframe"
        const val STATS_TAB_KEY = "stats_tab"
        const val STATS_GRANULARITY_KEY = "stats_granularity"
        
        // Temporary storage for traffic granularity
        var trafficGranularity: String? = null
    }
}