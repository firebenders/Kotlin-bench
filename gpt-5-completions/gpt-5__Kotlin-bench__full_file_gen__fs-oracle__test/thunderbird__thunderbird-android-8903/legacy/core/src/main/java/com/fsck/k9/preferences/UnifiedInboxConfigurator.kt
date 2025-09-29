package com.fsck.k9.preferences

import app.k9mail.legacy.account.AccountManager
import com.fsck.k9.K9

/**
 * Configures the unified inbox after an account has been added.
 *
 * Previously this only enabled the Unified Inbox when more than one account
 * was present. That could delay the Unified Inbox appearing until app restart
 * due to UI refresh timing. We now enable it as soon as there is at least one
 * account, and only if it's not already enabled.
 */
class UnifiedInboxConfigurator(
    private val accountManager: AccountManager,
) {
    fun configureUnifiedInbox() {
        if (!K9.isShowUnifiedInbox && accountManager.getAccounts().isNotEmpty()) {
            K9.isShowUnifiedInbox = true
            K9.saveSettingsAsync()
        }
    }
}