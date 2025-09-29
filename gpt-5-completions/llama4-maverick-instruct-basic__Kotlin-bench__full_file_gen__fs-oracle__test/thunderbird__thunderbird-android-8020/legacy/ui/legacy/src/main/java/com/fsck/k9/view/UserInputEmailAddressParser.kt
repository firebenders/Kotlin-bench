package com.fsck.k9.view

import com.fsck.k9.mail.Address
import org.apache.james.mime4j.util.CharsetUtil

private val rfc5321MailboxRegex = Regex("^[^<>,;:\\\\\"\\s]+@([^<>,;:\\\\\"\\s]+\\.)+[a-zA-Z]{2,}\$")

/**
 * Used to parse name & email address pairs entered by the user.
 */
internal class UserInputEmailAddressParser {

    @Throws(InvalidEmailAddressException::class)
    fun parse(input: String): List<Address> {
        return Address.parseUnencoded(input)
            .mapNotNull { address ->
                when {
                    address.address.isNullOrBlank() || !isValidRfc5321Mailbox(address.address) -> null
                    address.isNonAsciiAddress() -> throw InvalidEmailAddressException(address.address)
                    else -> Address.parse(address.toEncodedString()).firstOrNull()
                }
            }
    }

    private fun isValidRfc5321Mailbox(address: String): Boolean {
        return rfc5321MailboxRegex.matches(address)
    }

    private fun Address.isNonAsciiAddress() = !CharsetUtil.isASCII(address)
}

internal class InvalidEmailAddressException(message: String) : Exception(message)