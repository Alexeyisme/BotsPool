"""
Data anonymization utilities for protecting PII
"""

import re
import hashlib
import random
import string
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class AnonymizationMethod(Enum):
    """Methods for anonymizing data."""

    MASK = "mask"
    HASH = "hash"
    REPLACE = "replace"
    REMOVE = "remove"
    ENCRYPT = "encrypt"


@dataclass
class AnonymizationConfig:
    """Configuration for data anonymization."""

    method: AnonymizationMethod = AnonymizationMethod.MASK
    mask_char: str = "*"
    preserve_length: bool = True
    preserve_format: bool = True
    hash_algorithm: str = "sha256"
    salt: Optional[str] = None


@dataclass
class AnonymizationResult:
    """Result of data anonymization."""

    original_value: str
    anonymized_value: str
    method_used: AnonymizationMethod
    confidence: float
    metadata: Dict[str, Any]


class DataAnonymizer:
    """Anonymizes sensitive data using various methods."""

    def __init__(self, config: Optional[AnonymizationConfig] = None):
        """
        Initialize the data anonymizer.

        Args:
            config: Configuration for anonymization
        """
        self.config = config or AnonymizationConfig()
        self._name_cache = {}
        self._email_cache = {}
        self._phone_cache = {}

    def anonymize_data(self, data: Any, pii_type: str) -> Any:
        """
        Anonymize data based on its type.

        Args:
            data: Data to anonymize
            pii_type: Type of PII (email, phone, name, etc.)

        Returns:
            Any: Anonymized data
        """
        if isinstance(data, str):
            return self._anonymize_string(data, pii_type)
        elif isinstance(data, dict):
            return self._anonymize_dict(data)
        elif isinstance(data, list):
            return self._anonymize_list(data)
        else:
            return data

    def _anonymize_string(self, text: str, pii_type: str) -> str:
        """Anonymize a string based on PII type."""
        if pii_type == "email":
            return self.anonymize_email(text)
        elif pii_type == "phone":
            return self.anonymize_phone(text)
        elif pii_type == "name":
            return self.anonymize_name(text)
        elif pii_type == "address":
            return self.anonymize_address(text)
        elif pii_type == "ssn":
            return self.anonymize_ssn(text)
        elif pii_type == "credit_card":
            return self.anonymize_credit_card(text)
        else:
            return self.mask_data(text)

    def _anonymize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize a dictionary."""
        anonymized = {}
        for key, value in data.items():
            # Check if key suggests PII
            pii_type = self._detect_pii_type_from_key(key)
            anonymized[key] = self.anonymize_data(value, pii_type)
        return anonymized

    def _anonymize_list(self, data: List[Any]) -> List[Any]:
        """Anonymize a list."""
        return [self.anonymize_data(item, "unknown") for item in data]

    def _detect_pii_type_from_key(self, key: str) -> str:
        """Detect PII type from dictionary key."""
        key_lower = key.lower()
        if any(word in key_lower for word in ["email", "mail"]):
            return "email"
        elif any(word in key_lower for word in ["phone", "tel", "mobile"]):
            return "phone"
        elif any(word in key_lower for word in ["name", "first", "last", "full"]):
            return "name"
        elif any(word in key_lower for word in ["address", "street", "city", "zip"]):
            return "address"
        elif any(word in key_lower for word in ["ssn", "social"]):
            return "ssn"
        elif any(word in key_lower for word in ["credit", "card", "cc"]):
            return "credit_card"
        else:
            return "unknown"

    def anonymize_email(self, email: str) -> str:
        """Anonymize an email address."""
        if not email or "@" not in email:
            return email

        if self.config.method == AnonymizationMethod.MASK:
            local, domain = email.split("@", 1)
            if self.config.preserve_length:
                masked_local = self.mask_data(local)
            else:
                masked_local = "user"
            return f"{masked_local}@{domain}"

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(email)

        elif self.config.method == AnonymizationMethod.REPLACE:
            return f"user{random.randint(1000, 9999)}@example.com"

        else:
            return email

    def anonymize_phone(self, phone: str) -> str:
        """Anonymize a phone number."""
        if not phone:
            return phone

        if self.config.method == AnonymizationMethod.MASK:
            # Remove non-digits
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                if self.config.preserve_format:
                    # Preserve original format
                    masked = phone
                    for i, char in enumerate(phone):
                        if char.isdigit() and i < len(phone) - 4:
                            masked = (
                                masked[:i] + self.config.mask_char + masked[i + 1 :]
                            )
                    return masked
                else:
                    return f"***-***-{digits[-4:]}"
            else:
                return self.mask_data(phone)

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(phone)

        elif self.config.method == AnonymizationMethod.REPLACE:
            return f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

        else:
            return phone

    def anonymize_name(self, name: str) -> str:
        """Anonymize a name."""
        if not name:
            return name

        if self.config.method == AnonymizationMethod.MASK:
            words = name.split()
            if len(words) >= 2:
                # Mask first name, keep last name initial
                first_name = words[0]
                last_name = words[-1]
                masked_first = self.mask_data(first_name)
                masked_last = last_name[0] + self.config.mask_char * (
                    len(last_name) - 1
                )
                return f"{masked_first} {masked_last}"
            else:
                return self.mask_data(name)

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(name)

        elif self.config.method == AnonymizationMethod.REPLACE:
            first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
            return f"{random.choice(first_names)} {random.choice(last_names)}"

        else:
            return name

    def anonymize_address(self, address: str) -> str:
        """Anonymize an address."""
        if not address:
            return address

        if self.config.method == AnonymizationMethod.MASK:
            # Mask street number and name
            words = address.split()
            if words and words[0].isdigit():
                # Mask street number
                words[0] = self.config.mask_char * len(words[0])
                # Mask street name (first word after number)
                if len(words) > 1:
                    words[1] = self.mask_data(words[1])
            return " ".join(words)

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(address)

        elif self.config.method == AnonymizationMethod.REPLACE:
            street_numbers = ["123", "456", "789", "321", "654"]
            street_names = ["Main St", "Oak Ave", "Pine Rd", "Elm St", "Maple Ave"]
            return f"{random.choice(street_numbers)} {random.choice(street_names)}"

        else:
            return address

    def anonymize_ssn(self, ssn: str) -> str:
        """Anonymize a Social Security Number."""
        if not ssn:
            return ssn

        if self.config.method == AnonymizationMethod.MASK:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", ssn)
            if len(digits) == 9:
                return f"***-**-{digits[-4:]}"
            else:
                return self.mask_data(ssn)

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(ssn)

        elif self.config.method == AnonymizationMethod.REPLACE:
            return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

        else:
            return ssn

    def anonymize_credit_card(self, cc: str) -> str:
        """Anonymize a credit card number."""
        if not cc:
            return cc

        if self.config.method == AnonymizationMethod.MASK:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", cc)
            if len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"
            else:
                return self.mask_data(cc)

        elif self.config.method == AnonymizationMethod.HASH:
            return self.hash_data(cc)

        elif self.config.method == AnonymizationMethod.REPLACE:
            return f"****-****-****-{random.randint(1000, 9999)}"

        else:
            return cc

    def mask_data(self, data: str, mask_char: Optional[str] = None) -> str:
        """Mask sensitive data."""
        if not data:
            return data

        mask = mask_char or self.config.mask_char

        if self.config.preserve_length:
            return mask * len(data)
        else:
            # Show first and last characters
            if len(data) <= 2:
                return mask * len(data)
            else:
                return data[0] + mask * (len(data) - 2) + data[-1]

    def hash_data(self, data: str, algorithm: Optional[str] = None) -> str:
        """Hash sensitive data."""
        if not data:
            return data

        algo = algorithm or self.config.hash_algorithm

        if algo == "sha256":
            hash_obj = hashlib.sha256()
        elif algo == "sha512":
            hash_obj = hashlib.sha512()
        elif algo == "md5":
            hash_obj = hashlib.md5()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algo}")

        # Add salt if provided
        if self.config.salt:
            data = data + self.config.salt

        hash_obj.update(data.encode("utf-8"))
        return hash_obj.hexdigest()

    def replace_data(self, data: str, replacement: str) -> str:
        """Replace sensitive data with a replacement value."""
        return replacement


# Convenience functions
def anonymize_data(
    data: Any, pii_type: str, config: Optional[AnonymizationConfig] = None
) -> Any:
    """Anonymize data using the default anonymizer."""
    anonymizer = DataAnonymizer(config)
    return anonymizer.anonymize_data(data, pii_type)


def anonymize_email(email: str, config: Optional[AnonymizationConfig] = None) -> str:
    """Anonymize an email address."""
    anonymizer = DataAnonymizer(config)
    return anonymizer.anonymize_email(email)


def anonymize_phone(phone: str, config: Optional[AnonymizationConfig] = None) -> str:
    """Anonymize a phone number."""
    anonymizer = DataAnonymizer(config)
    return anonymizer.anonymize_phone(phone)


def anonymize_name(name: str, config: Optional[AnonymizationConfig] = None) -> str:
    """Anonymize a name."""
    anonymizer = DataAnonymizer(config)
    return anonymizer.anonymize_name(name)


def anonymize_address(
    address: str, config: Optional[AnonymizationConfig] = None
) -> str:
    """Anonymize an address."""
    anonymizer = DataAnonymizer(config)
    return anonymizer.anonymize_address(address)


def mask_data(data: str, mask_char: str = "*", preserve_length: bool = True) -> str:
    """Mask sensitive data."""
    config = AnonymizationConfig(mask_char=mask_char, preserve_length=preserve_length)
    anonymizer = DataAnonymizer(config)
    return anonymizer.mask_data(data)


def hash_data(data: str, algorithm: str = "sha256", salt: Optional[str] = None) -> str:
    """Hash sensitive data."""
    config = AnonymizationConfig(hash_algorithm=algorithm, salt=salt)
    anonymizer = DataAnonymizer(config)
    return anonymizer.hash_data(data)


def replace_data(data: str, replacement: str) -> str:
    """Replace sensitive data with a replacement value."""
    anonymizer = DataAnonymizer()
    return anonymizer.replace_data(data, replacement)
