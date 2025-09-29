package com.fsck.k9

import app.k9mail.legacy.account.Account
import app.k9mail.legacy.account.Account.FolderMode
import com.fsck.k9.helper.Utility
import com.fsck.k9.mail.FolderClass
import com.fsck.k9.preferences.Storage
import com.fsck.k9.preferences.StorageEditor
import timber.log.Timber

class AccountPreferenceSerializer {
    
    fun loadAccount(account: Account, storage: Storage) {
        val accountUuid = account.uuid
        
        // Load basic account settings
        account.storeUri = storage.getString("$accountUuid.storeUri", null)
        account.transportUri = storage.getString("$accountUuid.transportUri", null)
        account.description = storage.getString("$accountUuid.description", null)
        account.alwaysBcc = storage.getString("$accountUuid.alwaysBcc", null)
        account.identities = loadIdentities(accountUuid, storage)
        
        // Load folder settings
        account.autoExpandFolderName = storage.getString("$accountUuid.autoExpandFolderName", null)
        account.inboxFolderName = storage.getString("$accountUuid.inboxFolderName", null)
        account.draftsFolderName = storage.getString("$accountUuid.draftsFolderName", null)
        account.sentFolderName = storage.getString("$accountUuid.sentFolderName", null)
        account.trashFolderName = storage.getString("$accountUuid.trashFolderName", null)
        account.archiveFolderName = storage.getString("$accountUuid.archiveFolderName", null)
        account.spamFolderName = storage.getString("$accountUuid.spamFolderName", null)
        
        // Load folder selection modes - IMPORTANT: preserve these during import
        val draftsFolderSelection = storage.getString("$accountUuid.draftsFolderSelection", null)
        if (draftsFolderSelection != null) {
            account.draftsFolderSelection = FolderMode.valueOf(draftsFolderSelection)
        }
        
        val sentFolderSelection = storage.getString("$accountUuid.sentFolderSelection", null)
        if (sentFolderSelection != null) {
            account.sentFolderSelection = FolderMode.valueOf(sentFolderSelection)
        }
        
        val trashFolderSelection = storage.getString("$accountUuid.trashFolderSelection", null)
        if (trashFolderSelection != null) {
            account.trashFolderSelection = FolderMode.valueOf(trashFolderSelection)
        }
        
        val archiveFolderSelection = storage.getString("$accountUuid.archiveFolderSelection", null)
        if (archiveFolderSelection != null) {
            account.archiveFolderSelection = FolderMode.valueOf(archiveFolderSelection)
        }
        
        val spamFolderSelection = storage.getString("$accountUuid.spamFolderSelection", null)
        if (spamFolderSelection != null) {
            account.spamFolderSelection = FolderMode.valueOf(spamFolderSelection)
        }
        
        // Load display settings
        account.displayCount = storage.getInt("$accountUuid.displayCount", K9.DEFAULT_VISIBLE_LIMIT)
        account.isNotifyNewMail = storage.getBoolean("$accountUuid.notifyNewMail", false)
        account.folderNotifyNewMailMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderNotifyNewMailMode", FolderMode.ALL.name)!!
        )
        account.isNotifyContactsMailOnly = storage.getBoolean("$accountUuid.notifyContactsMailOnly", false)
        account.isIgnoreChatMessages = storage.getBoolean("$accountUuid.ignoreChatMessages", false)
        
        // Load sync settings
        account.folderDisplayMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderDisplayMode", FolderMode.NOT_SECOND_CLASS.name)!!
        )
        account.folderSyncMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderSyncMode", FolderMode.FIRST_CLASS.name)!!
        )
        account.folderPushMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderPushMode", FolderMode.FIRST_CLASS.name)!!
        )
        account.folderTargetMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderTargetMode", FolderMode.NOT_SECOND_CLASS.name)!!
        )
        
        // Load other settings
        account.isNotifySelfNewMail = storage.getBoolean("$accountUuid.notifySelfNewMail", true)
        account.isNotifySync = storage.getBoolean("$accountUuid.notifyMailCheck", false)
        account.deletePolicy = Account.DeletePolicy.valueOf(
            storage.getString("$accountUuid.deletePolicy", Account.DeletePolicy.NEVER.name)!!
        )
        account.compressionType = Account.CompressionType.valueOf(
            storage.getString("$accountUuid.compressionType", Account.CompressionType.NO_COMPRESSION.name)!!
        )
        
        account.chipColor = storage.getInt("$accountUuid.chipColor", 0)
        account.isEnabled = storage.getBoolean("$accountUuid.enabled", true)
        account.isMarkMessageAsReadOnView = storage.getBoolean("$accountUuid.markMessageAsReadOnView", true)
        account.isMarkMessageAsReadOnDelete = storage.getBoolean("$accountUuid.markMessageAsReadOnDelete", true)
        account.isAlwaysShowCcBcc = storage.getBoolean("$accountUuid.alwaysShowCcBcc", false)
        
        // Load message format settings
        account.messageFormat = Account.MessageFormat.valueOf(
            storage.getString("$accountUuid.messageFormat", Account.MessageFormat.HTML.name)!!
        )
        account.isMessageFormatAuto = storage.getBoolean("$accountUuid.messageFormatAuto", false)
        account.isMessageReadReceipt = storage.getBoolean("$accountUuid.messageReadReceipt", false)
        account.quoteStyle = Account.QuoteStyle.valueOf(
            storage.getString("$accountUuid.quoteStyle", Account.QuoteStyle.PREFIX.name)!!
        )
        account.quotePrefix = storage.getString("$accountUuid.quotePrefix", ">")
        account.isDefaultQuotedTextShown = storage.getBoolean("$accountUuid.defaultQuotedTextShown", true)
        account.isReplyAfterQuote = storage.getBoolean("$accountUuid.replyAfterQuote", false)
        account.isStripSignature = storage.getBoolean("$accountUuid.stripSignature", true)
        
        account.maxPushFolders = storage.getInt("$accountUuid.maxPushFolders", 10)
        account.isGoToUnreadMessageSearch = storage.getBoolean("$accountUuid.goToUnreadMessageSearch", false)
        account.isSubscribedFoldersOnly = storage.getBoolean("$accountUuid.subscribedFoldersOnly", false)
        account.maximumPolledMessageAge = storage.getInt("$accountUuid.maximumPolledMessageAge", -1)
        account.maximumAutoDownloadMessageSize = storage.getInt("$accountUuid.maximumAutoDownloadMessageSize", 32768)
        account.automaticCheckIntervalMinutes = storage.getInt("$accountUuid.automaticCheckIntervalMinutes", Account.INTERVAL_MINUTES_NEVER)
        account.idleRefreshMinutes = storage.getInt("$accountUuid.idleRefreshMinutes", 24)
        account.isPushPollOnConnect = storage.getBoolean("$accountUuid.pushPollOnConnect", true)
        account.displayCount = storage.getInt("$accountUuid.displayCount", K9.DEFAULT_VISIBLE_LIMIT)
        account.latestOldMessageSeenTime = storage.getLong("$accountUuid.latestOldMessageSeenTime", 0)
        
        account.isNotifyNewMail = storage.getBoolean("$accountUuid.notifyNewMail", false)
        account.folderNotifyNewMailMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderNotifyNewMailMode", FolderMode.ALL.name)!!
        )
        account.isNotifyContactsMailOnly = storage.getBoolean("$accountUuid.notifyContactsMailOnly", false)
        account.isIgnoreChatMessages = storage.getBoolean("$accountUuid.ignoreChatMessages", false)
        
        account.isSortAscending = storage.getBoolean("$accountUuid.sortAscending", false)
        val sortTypeString = storage.getString("$accountUuid.sortType", null)
        if (sortTypeString != null) {
            account.sortType = Account.SortType.valueOf(sortTypeString)
        }
        
        val showPicturesValue = storage.getString("$accountUuid.showPictures", null)
        if (showPicturesValue != null) {
            account.showPictures = Account.ShowPictures.valueOf(showPicturesValue)
        }
        
        account.notificationSetting.isRingEnabled = storage.getBoolean("$accountUuid.ring", true)
        account.notificationSetting.ringtone = storage.getString("$accountUuid.ringtone", null)
        account.notificationSetting.isLedEnabled = storage.getBoolean("$accountUuid.led", true)
        account.notificationSetting.ledColor = storage.getInt("$accountUuid.ledColor", 0)
        account.notificationSetting.isVibrateEnabled = storage.getBoolean("$accountUuid.vibrate", false)
        account.notificationSetting.vibratePattern = storage.getInt("$accountUuid.vibratePattern", 0)
        account.notificationSetting.vibrateTimes = storage.getInt("$accountUuid.vibrateTimes", 5)
        
        account.folderDisplayMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderDisplayMode", FolderMode.NOT_SECOND_CLASS.name)!!
        )
        account.folderSyncMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderSyncMode", FolderMode.FIRST_CLASS.name)!!
        )
        account.folderPushMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderPushMode", FolderMode.FIRST_CLASS.name)!!
        )
        account.folderTargetMode = FolderMode.valueOf(
            storage.getString("$accountUuid.folderTargetMode", FolderMode.NOT_SECOND_CLASS.name)!!
        )
        
        account.isSearchByDefault = storage.getBoolean("$accountUuid.searchByDefault", false)
        account.isSortAscending = storage.getBoolean("$accountUuid.sortAscending", false)
        
        account.expungePolicy = Account.Expunge.valueOf(
            storage.getString("$accountUuid.expungePolicy", Account.Expunge.EXPUNGE_IMMEDIATELY.name)!!
        )
        account.isSyncRemoteDeletions = storage.getBoolean("$accountUuid.syncRemoteDeletions", true)
        
        val localStorageProviderValue = storage.getString("$accountUuid.localStorageProvider", null)
        if (localStorageProviderValue != null) {
            account.localStorageProviderId = localStorageProviderValue
        }
        
        loadFolderClasses(account, storage)
        
        // Load OAuth settings if present
        account.oAuthState = storage.getString("$accountUuid.oAuthState", null)
        
        // Load account number
        val accountNumber = storage.getInt("$accountUuid.accountNumber", Account.UNASSIGNED_ACCOUNT_NUMBER)
        if (accountNumber != Account.UNASSIGNED_ACCOUNT_NUMBER) {
            account.accountNumber = accountNumber
        }
    }
    
    fun save(editor: StorageEditor, storage: Storage, account: Account) {
        val accountUuid = account.uuid
        
        if (!storage.getString("accountUuids", "").contains(accountUuid)) {
            var accountUuids = storage.getString("accountUuids", "")
            accountUuids += (if (accountUuids.isNotEmpty()) "," else "") + accountUuid
            editor.putString("accountUuids", accountUuids)
        }
        
        editor.putString("$accountUuid.storeUri", account.storeUri)
        editor.putString("$accountUuid.transportUri", account.transportUri)
        editor.putString("$accountUuid.description", account.description)
        editor.putString("$accountUuid.alwaysBcc", account.alwaysBcc)
        saveIdentities(account, storage, editor)
        
        // Save folder settings
        editor.putString("$accountUuid.autoExpandFolderName", account.autoExpandFolderName)
        editor.putString("$accountUuid.inboxFolderName", account.inboxFolderName)
        editor.putString("$accountUuid.draftsFolderName", account.draftsFolderName)
        editor.putString("$accountUuid.sentFolderName", account.sentFolderName)
        editor.putString("$accountUuid.trashFolderName", account.trashFolderName)
        editor.putString("$accountUuid.archiveFolderName", account.archiveFolderName)
        editor.putString("$accountUuid.spamFolderName", account.spamFolderName)
        
        // Save folder selection modes - IMPORTANT: preserve these during export
        editor.putString("$accountUuid.draftsFolderSelection", account.draftsFolderSelection.name)
        editor.putString("$accountUuid.sentFolderSelection", account.sentFolderSelection.name)
        editor.putString("$accountUuid.trashFolderSelection", account.trashFolderSelection.name)
        editor.putString("$accountUuid.archiveFolderSelection", account.archiveFolderSelection.name)
        editor.putString("$accountUuid.spamFolderSelection", account.spamFolderSelection.name)
        
        // Save display settings
        editor.putInt("$accountUuid.displayCount", account.displayCount)
        editor.putBoolean("$accountUuid.notifyNewMail", account.isNotifyNewMail)
        editor.putString("$accountUuid.folderNotifyNewMailMode", account.folderNotifyNewMailMode.name)
        editor.putBoolean("$accountUuid.notifyContactsMailOnly", account.isNotifyContactsMailOnly)
        editor.putBoolean("$accountUuid.ignoreChatMessages", account.isIgnoreChatMessages)
        
        // Save sync settings
        editor.putString("$accountUuid.folderDisplayMode", account.folderDisplayMode.name)
        editor.putString("$accountUuid.folderSyncMode", account.folderSyncMode.name)
        editor.putString("$accountUuid.folderPushMode", account.folderPushMode.name)
        editor.putString("$accountUuid.folderTargetMode", account.folderTargetMode.name)
        
        // Save other settings
        editor.putBoolean("$accountUuid.notifySelfNewMail", account.isNotifySelfNewMail)
        editor.putBoolean("$accountUuid.notifyMailCheck", account.isNotifySync)
        editor.putString("$accountUuid.deletePolicy", account.deletePolicy.name)
        editor.putString("$accountUuid.compressionType", account.compressionType.name)
        
        editor.putInt("$accountUuid.chipColor", account.chipColor)
        editor.putBoolean("$accountUuid.enabled", account.isEnabled)
        editor.putBoolean("$accountUuid.markMessageAsReadOnView", account.isMarkMessageAsReadOnView)
        editor.putBoolean("$accountUuid.markMessageAsReadOnDelete", account.isMarkMessageAsReadOnDelete)
        editor.putBoolean("$accountUuid.alwaysShowCcBcc", account.isAlwaysShowCcBcc)
        
        // Save message format settings
        editor.putString("$accountUuid.messageFormat", account.messageFormat.name)
        editor.putBoolean("$accountUuid.messageFormatAuto", account.isMessageFormatAuto)
        editor.putBoolean("$accountUuid.messageReadReceipt", account.isMessageReadReceipt)
        editor.putString("$accountUuid.quoteStyle", account.quoteStyle.name)
        editor.putString("$accountUuid.quotePrefix", account.quotePrefix)
        editor.putBoolean("$accountUuid.defaultQuotedTextShown", account.isDefaultQuotedTextShown)
        editor.putBoolean("$accountUuid.replyAfterQuote", account.isReplyAfterQuote)
        editor.putBoolean("$accountUuid.stripSignature", account.isStripSignature)
        
        editor.putInt("$accountUuid.maxPushFolders", account.maxPushFolders)
        editor.putBoolean("$accountUuid.goToUnreadMessageSearch", account.isGoToUnreadMessageSearch)
        editor.putBoolean("$accountUuid.subscribedFoldersOnly", account.isSubscribedFoldersOnly)
        editor.putInt("$accountUuid.maximumPolledMessageAge", account.maximumPolledMessageAge)
        editor.putInt("$accountUuid.maximumAutoDownloadMessageSize", account.maximumAutoDownloadMessageSize)
        editor.putInt("$accountUuid.automaticCheckIntervalMinutes", account.automaticCheckIntervalMinutes)
        editor.putInt("$accountUuid.idleRefreshMinutes", account.idleRefreshMinutes)
        editor.putBoolean("$accountUuid.pushPollOnConnect", account.isPushPollOnConnect)
        editor.putLong("$accountUuid.latestOldMessageSeenTime", account.latestOldMessageSeenTime)
        
        editor.putBoolean("$accountUuid.sortAscending", account.isSortAscending)
        editor.putString("$accountUuid.sortType", account.sortType.name)
        editor.putString("$accountUuid.showPictures", account.showPictures.name)
        
        editor.putBoolean("$accountUuid.ring", account.notificationSetting.isRingEnabled)
        account.notificationSetting.ringtone?.let { ringtone ->
            editor.putString("$accountUuid.ringtone", ringtone)
        } ?: editor.remove("$accountUuid.ringtone")
        editor.putBoolean("$accountUuid.led", account.notificationSetting.isLedEnabled)
        editor.putInt("$accountUuid.ledColor", account.notificationSetting.ledColor)
        editor.putBoolean("$accountUuid.vibrate", account.notificationSetting.isVibrateEnabled)
        editor.putInt("$accountUuid.vibratePattern", account.notificationSetting.vibratePattern)
        editor.putInt("$accountUuid.vibrateTimes", account.notificationSetting.vibrateTimes)
        
        editor.putBoolean("$accountUuid.searchByDefault", account.isSearchByDefault)
        editor.putString("$accountUuid.expungePolicy", account.expungePolicy.name)
        editor.putBoolean("$accountUuid.syncRemoteDeletions", account.isSyncRemoteDeletions)
        
        editor.putString("$accountUuid.localStorageProvider", account.localStorageProviderId)
        
        saveFolderClasses(account, editor)
        
        // Save OAuth state if present
        account.oAuthState?.let { oAuthState ->
            editor.putString("$accountUuid.oAuthState", oAuthState)
        } ?: editor.remove("$accountUuid.oAuthState")
        
        // Save account number
        editor.putInt("$accountUuid.accountNumber", account.accountNumber)
    }
    
    fun delete(editor: StorageEditor, storage: Storage, account: Account) {
        val accountUuid = account.uuid
        
        // Remove account UUID from the list
        val accountUuids = storage.getString("accountUuids", "")
        val newAccountUuids = accountUuids.split(",")
            .filter { it != accountUuid }
            .joinToString(",")
        editor.putString("accountUuids", newAccountUuids)
        
        // Remove all account-specific settings
        val keysToRemove = storage.all.keys.filter { it.startsWith("$accountUuid.") }
        keysToRemove.forEach { key ->
            editor.remove(key)
        }
    }
    
    fun move(editor: StorageEditor, account: Account, storage: Storage, newPosition: Int) {
        val accountUuids = storage.getString("accountUuids", "")
        val uuidList = accountUuids.split(",").toMutableList()
        
        val oldPosition = uuidList.indexOf(account.uuid)
        if (oldPosition == -1 || oldPosition == newPosition) {
            return
        }
        
        uuidList.removeAt(oldPosition)
        uuidList.add(newPosition, account.uuid)
        
        val newAccountUuids = uuidList.joinToString(",")
        editor.putString("accountUuids", newAccountUuids)
    }
    
    fun loadDefaults(account: Account) {
        account.displayCount = K9.DEFAULT_VISIBLE_LIMIT
        account.isNotifyNewMail = false
        account.folderNotifyNewMailMode = FolderMode.ALL
        account.isNotifyContactsMailOnly = false
        account.isIgnoreChatMessages = false
        account.isNotifySelfNewMail = true
        account.isNotifySync = false
        account.isMarkMessageAsReadOnView = true
        account.isMarkMessageAsReadOnDelete = true
        account.isAlwaysShowCcBcc = false
        
        account.messageFormat = Account.MessageFormat.HTML
        account.isMessageFormatAuto = false
        account.isMessageReadReceipt = false
        account.quoteStyle = Account.QuoteStyle.PREFIX
        account.quotePrefix = ">"
        account.isDefaultQuotedTextShown = true
        account.isReplyAfterQuote = false
        account.isStripSignature = true
        
        account.deletePolicy = Account.DeletePolicy.NEVER
        account.compressionType = Account.CompressionType.NO_COMPRESSION
        account.folderDisplayMode = FolderMode.NOT_SECOND_CLASS
        account.folderSyncMode = FolderMode.FIRST_CLASS
        account.folderPushMode = FolderMode.FIRST_CLASS
        account.folderTargetMode = FolderMode.NOT_SECOND_CLASS
        
        account.isSearchByDefault = false
        account.isSortAscending = false
        account.sortType = Account.SortType.SORT_DATE
        account.showPictures = Account.ShowPictures.NEVER
        
        account.chipColor = 0
        account.isGoToUnreadMessageSearch = false
        account.isSubscribedFoldersOnly = false
        account.maximumPolledMessageAge = -1
        account.maximumAutoDownloadMessageSize = 32768
        account.automaticCheckIntervalMinutes = Account.INTERVAL_MINUTES_NEVER
        account.idleRefreshMinutes = 24
        account.isPushPollOnConnect = true
        account.expungePolicy = Account.Expunge.EXPUNGE_IMMEDIATELY
        account.isSyncRemoteDeletions = true
        account.maxPushFolders = 10
        account.isEnabled = true
        
        // Set default folder selections to AUTOMATIC
        account.draftsFolderSelection = FolderMode.AUTOMATIC
        account.sentFolderSelection = FolderMode.AUTOMATIC
        account.trashFolderSelection = FolderMode.AUTOMATIC
        account.archiveFolderSelection = FolderMode.AUTOMATIC
        account.spamFolderSelection = FolderMode.AUTOMATIC
        
        account.localStorageProviderId = StorageManager.InternalStorageProvider.ID
        
        // Initialize notification settings with defaults
        account.notificationSetting.isRingEnabled = true
        account.notificationSetting.ringtone = null
        account.notificationSetting.isLedEnabled = true
        account.notificationSetting.ledColor = 0
        account.notificationSetting.isVibrateEnabled = false
        account.notificationSetting.vibratePattern = 0
        account.notificationSetting.vibrateTimes = 5
    }
    
    private fun loadIdentities(accountUuid: String, storage: Storage): MutableList<Identity> {
        val identities = mutableListOf<Identity>()
        var ident = 0
        var gotOne = false
        do {
            gotOne = false
            val name = storage.getString("$accountUuid.identities.$ident.name", null)
            val email = storage.getString("$accountUuid.identities.$ident.email", null)
            val signatureUse = storage.getBoolean("$accountUuid.identities.$ident.signatureUse", true)
            val signature = storage.getString("$accountUuid.identities.$ident.signature", null)
            val description = storage.getString("$accountUuid.identities.$ident.description", null)
            val replyTo = storage.getString("$accountUuid.identities.$ident.replyTo", null)
            if (email != null) {
                val identity = Identity(
                    name = name,
                    email = email,
                    signatureUse = signatureUse,
                    signature = signature,
                    description = description,
                    replyTo = replyTo
                )
                identities.add(identity)
                gotOne = true
            }
            ident++
        } while (gotOne)
        
        if (identities.isEmpty()) {
            val name = storage.getString("$accountUuid.name", null)
            val email = storage.getString("$accountUuid.email", null)
            val signatureUse = storage.getBoolean("$accountUuid.signatureUse", true)
            val signature = storage.getString("$accountUuid.signature", null)
            val identity = Identity(
                name = name,
                email = email,
                signatureUse = signatureUse,
                signature = signature,
                description = email,
                replyTo = null
            )
            identities.add(identity)
        }
        
        return identities
    }
    
    private fun saveIdentities(account: Account, storage: Storage, editor: StorageEditor) {
        val accountUuid = account.uuid
        
        // Remove existing identities
        var ident = 0
        var gotOne = false
        do {
            gotOne = false
            val email = storage.getString("$accountUuid.identities.$ident.email", null)
            if (email != null) {
                editor.remove("$accountUuid.identities.$ident.name")
                editor.remove("$accountUuid.identities.$ident.email")
                editor.remove("$accountUuid.identities.$ident.signatureUse")
                editor.remove("$accountUuid.identities.$ident.signature")
                editor.remove("$accountUuid.identities.$ident.description")
                editor.remove("$accountUuid.identities.$ident.replyTo")
                gotOne = true
            }
            ident++
        } while (gotOne)
        
        // Save identities
        account.identities.forEachIndexed { index, identity ->
            editor.putString("$accountUuid.identities.$index.name", identity.name)
            editor.putString("$accountUuid.identities.$index.email", identity.email)
            editor.putBoolean("$accountUuid.identities.$index.signatureUse", identity.signatureUse)
            editor.putString("$accountUuid.identities.$index.signature", identity.signature)
            editor.putString("$accountUuid.identities.$index.description", identity.description)
            identity.replyTo?.let {
                editor.putString("$accountUuid.identities.$index.replyTo", it)
            }
        }
        
        // Remove legacy identity settings
        editor.remove("$accountUuid.name")
        editor.remove("$accountUuid.email")
        editor.remove("$accountUuid.signatureUse")
        editor.remove("$accountUuid.signature")
    }
    
    private fun loadFolderClasses(account: Account, storage: Storage) {
        val accountUuid = account.uuid
        
        for ((folderServerId, folderClass) in FolderClass.values()) {
            val key = "$accountUuid.folderClass.$folderServerId"
            val value = storage.getString(key, null)
            if (value != null) {
                try {
                    account.setFolderClass(folderServerId, FolderClass.valueOf(value))
                } catch (e: IllegalArgumentException) {
                    Timber.w(e, "Unable to parse folder class for $folderServerId")
                }
            }
        }
    }
    
    private fun saveFolderClasses(account: Account, editor: StorageEditor) {
        val accountUuid = account.uuid
        
        for ((folderServerId, folderClass) in account.folderClasses) {
            val key = "$accountUuid.folderClass.$folderServerId"
            editor.putString(key, folderClass.name)
        }
    }
}