"""
Encryption utilities for botspool-shared-utils

This module provides comprehensive encryption utilities for securing sensitive data,
managing encryption keys, and ensuring data protection compliance.
"""

from .encryption import (
    encrypt_data,
    decrypt_data,
    encrypt_field,
    decrypt_field,
    generate_encryption_key,
    generate_key_pair,
    encrypt_with_public_key,
    decrypt_with_private_key,
)

from .key_manager import (
    KeyManager,
    generate_secure_key,
    generate_key_derivation_salt,
    store_key,
    retrieve_key,
    rotate_key,
)

# Additional encryption modules will be added as needed

__all__ = [
    # Core encryption functions
    "encrypt_data",
    "decrypt_data",
    "encrypt_field",
    "decrypt_field",
    "generate_encryption_key",
    "generate_key_pair",
    "encrypt_with_public_key",
    "decrypt_with_private_key",
    # Key management
    "KeyManager",
    "generate_secure_key",
    "generate_key_derivation_salt",
    "store_key",
    "retrieve_key",
    "rotate_key",
]
