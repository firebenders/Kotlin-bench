/*
 * Copyright 2025 JetBrains s.r.o.
 * Use of this source code is governed by the Apache 2.0 License that can be found in the LICENSE.txt file.
 */

package kotlinx.datetime.internal.format

internal fun Char.isAsciiDigit(): Boolean = this in '0'..'9'