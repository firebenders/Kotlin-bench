/***************************************************************************************
 * Copyright (c) 2022 Ankitects Pty Ltd <http://apps.ankiweb.net>                       *
 *                                                                                      *
 * This program is free software; you can redistribute it and/or modify it under        *
 * the terms of the GNU General Public License as published by the Free Software        *
 * Foundation; either version 3 of the License, or (at your option) any later           *
 * version.                                                                             *
 *                                                                                      *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY      *
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A      *
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.             *
 *                                                                                      *
 * You should have received a copy of the GNU General Public License along with         *
 * this program.  If not, see <http://www.gnu.org/licenses/>.                           *
 ****************************************************************************************/

package com.ichi2.anki

import android.content.Intent
import androidx.fragment.app.FragmentActivity
import anki.collection.OpChangesOnly
import com.ichi2.anki.CollectionManager.withCol
import com.ichi2.libanki.buildSearchString
import com.ichi2.libanki.importAnkiPackageRaw
import com.ichi2.libanki.importCsvRaw
import com.ichi2.libanki.undoableOp

suspend fun importJsonFileRaw(input: ByteArray): ByteArray {
    val output = withCol { importAnkiPackageRaw(input) }
    val changes = OpChangesOnly.parseFrom(output)
    undoableOp { changes }
    return output
}

suspend fun importCsvRaw(input: ByteArray): ByteArray {
    val output = withCol { importCsvRaw(input) }
    val changes = OpChangesOnly.parseFrom(output)
    undoableOp { changes }
    return output
}

// ... rest of the BackendImporting.kt file