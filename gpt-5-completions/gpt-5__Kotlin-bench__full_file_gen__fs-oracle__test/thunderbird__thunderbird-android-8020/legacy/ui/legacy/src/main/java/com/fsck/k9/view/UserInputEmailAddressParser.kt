package com.fsck.k9.view

import com.fsck.k9.mail.Address
import org.apache.james.mime4j.util.CharsetUtil

/**
 * Used to parse name & email address pairs entered by the user.
 *
 * TODO: Build a custom implementation that can deal with typical inputs from users who are not familiar with the
 *  RFC 5322 address-list syntax. See (ignored) tests in `UserInputEmailAddressParserTest`.
 */
internal class UserInputEmailAddressParser {

    @Throws(NonAsciiEmailAddressException::class)
    fun parse(input: String): List<Address> {
        return Address.parseUnencoded(input)
            .mapNotNull { address ->
                when {
                    address.isIncomplete() -> null
                    address.hasObviousSyntaxError() -> null
                    address.isNonAsciiAddress() -> throw NonAsciiEmailAddressException(address.address)
                    else -> Address.parse(address.toEncodedString()).firstOrNull()
                }
            }
    }

    private fun Address.isIncomplete() = hostname.isNullOrBlank()

    /**
     * Filter out addresses that contain obvious syntax errors that will never be valid RFC-5321 mailboxes.
     *
     * Example: "user@gmail.com/" (note the trailing slash) should be considered invalid.
     * This avoids attempting to send to invalid recipients and failing at the SMTP stage.
     */
    private fun Address.hasObviousSyntaxError(): Boolean {
        val addr = address.trim()

        // Trailing slash after the domain is not valid in an addr-spec.
        if (addr.endsWith('/')) return true

        // The parsed hostname should never contain a slash.
        if (hostname?.contains('/') == true) return true

        // Reject if hostname contains angle brackets or spaces which indicate parsing issues.
        if (hostname?.any { it == '<' || it == '>' || it == ' ' } == true) return true

        return false
    }

    private fun Address.isNonAsciiAddress() = !CharsetUtil.isASCII(address)
}

internal class NonAsciiEmailAddressException(message: String) : Exception(message)