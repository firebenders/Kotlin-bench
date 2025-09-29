/*
 *  Copyright (c) 2023 Brayan Oliveira <brayandso.dev@gmail.com>
 *
 *  This program is free software; you can redistribute it and/or modify it under
 *  the terms of the GNU General Public License as published by the Free Software
 *  Foundation; either version 3 of the License, or (at your option) any later
 *  version.
 *
 *  This program is distributed in the hope that it will be useful, but WITHOUT ANY
 *  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 *  PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along with
 *  this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package com.ichi2.anki

import android.content.Context
import android.webkit.WebResourceResponse
import androidx.webkit.WebViewAssetLoader
import com.ichi2.utils.AssetHelper.guessMimeType
import timber.log.Timber
import java.io.ByteArrayInputStream
import java.io.File
import java.io.FileInputStream

fun Context.getViewerAssetLoader(domain: String): WebViewAssetLoader {
    val mediaDir = CollectionHelper.getMediaDirectory(this)
    return WebViewAssetLoader.Builder()
        .setHttpAllowed(true)
        .setDomain(domain)
        .addPathHandler("/") { path: String ->
            if (path == "favicon.ico") {
                return@addPathHandler WebResourceResponse(null, null, ByteArrayInputStream(ByteArray(0)))
            }
            try {
                val file = File(mediaDir, path)
                val inputStream = FileInputStream(file)
                // Ensure SVG files are served with the correct MIME type
                val mimeType = when {
                    path.endsWith(".svg", ignoreCase = true) -> "image/svg+xml"
                    else -> guessMimeType(path)
                }
                WebResourceResponse(mimeType, null, inputStream)
            } catch (e: Exception) {
                Timber.d("File not found: %s", path)
                null
            }
        }
        .build()
}