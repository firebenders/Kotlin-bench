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

    @Throws(NonAsciiEmailAddressException::class, InvalidEmailAddressException::class)
    fun parse(input: String): List<Address> {
        return Address.parseUnencoded(input)
            .mapNotNull { address ->
                when {
                    address.isIncomplete() -> null
                    address.isNonAsciiAddress() -> throw NonAsciiEmailAddressException(address.address)
                    !address.isValidRfc5321Address() -> throw InvalidEmailAddressException(address.address)
                    else -> Address.parse(address.toEncodedString()).firstOrNull()
                }
            }
    }

    private fun Address.isIncomplete() = hostname.isNullOrBlank()

    private fun Address.isNonAsciiAddress() = !CharsetUtil.isASCII(address)
    
    /**
     * Validates that the email address conforms to RFC-5321 requirements.
     * This method checks for common invalid patterns that users might accidentally enter.
     */
    private fun Address.isValidRfc5321Address(): Boolean {
        val email = address ?: return false
        
        // Trim whitespace to handle accidental spaces
        val trimmedEmail = email.trim()
        if (trimmedEmail != email) {
            // Email contained leading/trailing whitespace
            return false
        }
        
        // Check for invalid trailing characters that are common user errors
        if (email.endsWith('/') || email.endsWith('\\') || 
            email.endsWith(',') || email.endsWith(';')) {
            return false
        }
        
        // Check for spaces within the email address (not allowed)
        if (email.contains(' ') || email.contains('\t') || 
            email.contains('\n') || email.contains('\r')) {
            return false
        }
        
        // Basic structure validation
        val atIndex = email.lastIndexOf('@')
        if (atIndex <= 0 || atIndex == email.length - 1) {
            return false
        }
        
        val localPart = email.substring(0, atIndex)
        val domainPart = email.substring(atIndex + 1)
        
        // Validate local part
        if (!isValidLocalPart(localPart)) {
            return false
        }
        
        // Validate domain part
        if (!isValidDomainPart(domainPart)) {
            return false
        }
        
        return true
    }
    
    /**
     * Validates the domain part of an email address according to RFC-5321.
     * Domain should only contain letters, digits, hyphens, and dots.
     */
    private fun isValidDomainPart(domain: String): Boolean {
        if (domain.isEmpty()) return false
        
        // Check for invalid characters in domain
        // Domain can only contain alphanumeric characters, dots, and hyphens
        for (char in domain) {
            if (!char.isLetterOrDigit() && char != '.' && char != '-') {
                return false
            }
        }
        
        // Domain should not start or end with a dot or hyphen
        if (domain.startsWith('.') || domain.endsWith('.') || 
            domain.startsWith('-') || domain.endsWith('-')) {
            return false
        }
        
        // Check for consecutive dots
        if (domain.contains("..")) {
            return false
        }
        
        // Each label (part between dots) should not be empty and 
        // should not start or end with hyphen
        val labels = domain.split('.')
        for (label in labels) {
            if (label.isEmpty()) {
                return false
            }
            if (label.startsWith('-') || label.endsWith('-')) {
                return false
            }
        }
        
        // Domain should have at least one dot (e.g., gmail.com)
        // This helps catch common typos
        if (!domain.contains('.')) {
            return false
        }
        
        return true
    }
    
    /**
     * Validates the local part of an email address.
     * The local part has more lenient rules but we check for obviously invalid characters.
     */
    private fun isValidLocalPart(localPart: String): Boolean {
        if (localPart.isEmpty()) return false
        
        // Check for obviously invalid characters that should never appear in local part
        val invalidChars = setOf(
            ' ', '\t', '\n', '\r',  // Whitespace characters
            '<', '>',                // Angle brackets (unless quoted)
            '[', ']',                // Square brackets (unless in specific context)
            '\\',                    // Backslash (unless escaping)
            ','                      // Comma (separator in address lists)
        )
        
        // Simple check without considering quoted strings or escaped characters
        // For a more complete implementation, we'd need to handle quoted strings properly
        for (char in localPart) {
            if (char in invalidChars) {
                // Check if this might be in a quoted string (basic check)
                if (!localPart.startsWith('"') || !localPart.endsWith('"')) {
                    return false
                }
            }
        }
        
        // Local part should not start or end with a dot
        if (localPart.startsWith('.') || localPart.endsWith('.')) {
            return false
        }
        
        // Check for consecutive dots (not allowed)
        if (localPart.contains("..")) {
            return false
        }
        
        return true
    }
}

internal class NonAsciiEmailAddressException(message: String) : Exception(message)
internal class InvalidEmailAddressException(message: String) : Exception(message)