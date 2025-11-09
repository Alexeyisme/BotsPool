"""
PII detection utilities for identifying sensitive data
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    ADDRESS = "address"
    NAME = "name"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"


@dataclass
class PIIPattern:
    """Represents a PII detection pattern."""

    pii_type: PIIType
    pattern: str
    confidence: float
    description: str
    example: str


@dataclass
class PIIPatternConfig:
    """Configuration for PII pattern detection."""

    enable_email: bool = True
    enable_phone: bool = True
    enable_credit_card: bool = True
    enable_ssn: bool = True
    enable_address: bool = True
    enable_name: bool = True
    enable_ip_address: bool = True
    enable_date_of_birth: bool = True
    enable_passport: bool = True
    enable_driver_license: bool = True
    min_confidence: float = 0.7


class PIIDetector:
    """Detects PII in text data."""

    def __init__(self, config: Optional[PIIPatternConfig] = None):
        """
        Initialize the PII detector.

        Args:
            config: Configuration for PII detection
        """
        self.config = config or PIIPatternConfig()
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[PIIPattern]:
        """Build the list of PII detection patterns."""
        patterns = []

        if self.config.enable_email:
            patterns.extend(self._get_email_patterns())

        if self.config.enable_phone:
            patterns.extend(self._get_phone_patterns())

        if self.config.enable_credit_card:
            patterns.extend(self._get_credit_card_patterns())

        if self.config.enable_ssn:
            patterns.extend(self._get_ssn_patterns())

        if self.config.enable_address:
            patterns.extend(self._get_address_patterns())

        if self.config.enable_name:
            patterns.extend(self._get_name_patterns())

        if self.config.enable_ip_address:
            patterns.extend(self._get_ip_address_patterns())

        if self.config.enable_date_of_birth:
            patterns.extend(self._get_date_of_birth_patterns())

        if self.config.enable_passport:
            patterns.extend(self._get_passport_patterns())

        if self.config.enable_driver_license:
            patterns.extend(self._get_driver_license_patterns())

        return patterns

    def _get_email_patterns(self) -> List[PIIPattern]:
        """Get email detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.EMAIL,
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                confidence=0.95,
                description="Email address",
                example="user@example.com",
            )
        ]

    def _get_phone_patterns(self) -> List[PIIPattern]:
        """Get phone number detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                confidence=0.85,
                description="US phone number",
                example="(555) 123-4567",
            ),
            PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=r"\b\+?[1-9]\d{1,14}\b",
                confidence=0.75,
                description="International phone number",
                example="+1234567890",
            ),
        ]

    def _get_credit_card_patterns(self) -> List[PIIPattern]:
        """Get credit card detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.CREDIT_CARD,
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
                confidence=0.90,
                description="Credit card number",
                example="4111 1111 1111 1111",
            )
        ]

    def _get_ssn_patterns(self) -> List[PIIPattern]:
        """Get SSN detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.SSN,
                pattern=r"\b(?!000|666|9\d{2})\d{3}[-.\s]?(?!00)\d{2}[-.\s]?(?!0000)\d{4}\b",
                confidence=0.95,
                description="Social Security Number",
                example="123-45-6789",
            )
        ]

    def _get_address_patterns(self) -> List[PIIPattern]:
        """Get address detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.ADDRESS,
                pattern=r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b",
                confidence=0.80,
                description="Street address",
                example="123 Main Street",
            )
        ]

    def _get_name_patterns(self) -> List[PIIPattern]:
        """Get name detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.NAME,
                pattern=r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                confidence=0.70,
                description="Full name",
                example="John Doe",
            )
        ]

    def _get_ip_address_patterns(self) -> List[PIIPattern]:
        """Get IP address detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
                confidence=0.85,
                description="IPv4 address",
                example="192.168.1.1",
            ),
            PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
                confidence=0.85,
                description="IPv6 address",
                example="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            ),
        ]

    def _get_date_of_birth_patterns(self) -> List[PIIPattern]:
        """Get date of birth detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.DATE_OF_BIRTH,
                pattern=r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b",
                confidence=0.75,
                description="Date of birth (MM/DD/YYYY)",
                example="01/15/1990",
            )
        ]

    def _get_passport_patterns(self) -> List[PIIPattern]:
        """Get passport detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.PASSPORT,
                pattern=r"\b[A-Z]{1,2}\d{6,9}\b",
                confidence=0.80,
                description="Passport number",
                example="A1234567",
            )
        ]

    def _get_driver_license_patterns(self) -> List[PIIPattern]:
        """Get driver license detection patterns."""
        return [
            PIIPattern(
                pii_type=PIIType.DRIVER_LICENSE,
                pattern=r"\b[A-Z]\d{7,8}\b",
                confidence=0.80,
                description="Driver license number",
                example="D1234567",
            )
        ]

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in the given text.

        Args:
            text: Text to analyze for PII

        Returns:
            List[Dict[str, Any]]: List of detected PII with metadata
        """
        detected_pii = []

        for pattern in self.patterns:
            matches = re.finditer(pattern.pattern, text, re.IGNORECASE)

            for match in matches:
                if pattern.confidence >= self.config.min_confidence:
                    detected_pii.append(
                        {
                            "pii_type": pattern.pii_type.value,
                            "value": match.group(),
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": pattern.confidence,
                            "description": pattern.description,
                            "example": pattern.example,
                        }
                    )

        return detected_pii

    def detect_email(self, text: str) -> List[str]:
        """Detect email addresses in text."""
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return re.findall(email_pattern, text)

    def detect_phone(self, text: str) -> List[str]:
        """Detect phone numbers in text."""
        phone_pattern = (
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
        )
        return re.findall(phone_pattern, text)

    def detect_credit_card(self, text: str) -> List[str]:
        """Detect credit card numbers in text."""
        cc_pattern = r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
        return re.findall(cc_pattern, text)

    def detect_ssn(self, text: str) -> List[str]:
        """Detect SSNs in text."""
        ssn_pattern = (
            r"\b(?!000|666|9\d{2})\d{3}[-.\s]?(?!00)\d{2}[-.\s]?(?!0000)\d{4}\b"
        )
        return re.findall(ssn_pattern, text)

    def detect_address(self, text: str) -> List[str]:
        """Detect addresses in text."""
        address_pattern = r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b"
        return re.findall(address_pattern, text)


# Convenience functions
def detect_pii(
    text: str, config: Optional[PIIPatternConfig] = None
) -> List[Dict[str, Any]]:
    """Detect PII in text using the default detector."""
    detector = PIIDetector(config)
    return detector.detect_pii(text)


def detect_email(text: str) -> List[str]:
    """Detect email addresses in text."""
    detector = PIIDetector()
    return detector.detect_email(text)


def detect_phone(text: str) -> List[str]:
    """Detect phone numbers in text."""
    detector = PIIDetector()
    return detector.detect_phone(text)


def detect_credit_card(text: str) -> List[str]:
    """Detect credit card numbers in text."""
    detector = PIIDetector()
    return detector.detect_credit_card(text)


def detect_ssn(text: str) -> List[str]:
    """Detect SSNs in text."""
    detector = PIIDetector()
    return detector.detect_ssn(text)


def detect_address(text: str) -> List[str]:
    """Detect addresses in text."""
    detector = PIIDetector()
    return detector.detect_address(text)
