"""
Key management utilities for encryption keys
"""

import os
import json
import base64
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey
import secrets

from .encryption import (
    generate_encryption_key,
    generate_key_pair,
    generate_key_derivation_salt,
)


class KeyManager:
    """
    Manages encryption keys with secure storage and rotation capabilities.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the key manager.

        Args:
            storage_path: Path to store keys (default: in-memory)
        """
        self.storage_path = storage_path
        self.keys: Dict[str, Dict] = {}
        self._load_keys()

    def _load_keys(self):
        """Load keys from storage."""
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    self.keys = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.keys = {}

    def _save_keys(self):
        """Save keys to storage."""
        if self.storage_path:
            try:
                with open(self.storage_path, "w") as f:
                    json.dump(self.keys, f, indent=2)
            except IOError as e:
                raise RuntimeError(f"Failed to save keys: {e}")

    def generate_secure_key(self, key_id: str, key_type: str = "aes") -> bytes:
        """
        Generate a secure encryption key.

        Args:
            key_id: Unique identifier for the key
            key_type: Type of key ("aes", "rsa")

        Returns:
            bytes: The generated key
        """
        if key_type == "aes":
            key = generate_encryption_key()
        elif key_type == "rsa":
            private_key, public_key = generate_key_pair()
            key = private_key
        else:
            raise ValueError(f"Unsupported key type: {key_type}")

        # Store key metadata
        self.keys[key_id] = {
            "key_type": key_type,
            "created_at": datetime.utcnow().isoformat(),
            "version": 1,
            "active": True,
        }

        self._save_keys()
        return key

    def store_key(
        self,
        key_id: str,
        key: bytes,
        key_type: str = "aes",
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Store an encryption key.

        Args:
            key_id: Unique identifier for the key
            key: The key to store
            key_type: Type of key ("aes", "rsa")
            metadata: Additional metadata for the key
        """
        key_data = {
            "key_type": key_type,
            "created_at": datetime.utcnow().isoformat(),
            "version": 1,
            "active": True,
            "metadata": metadata or {},
        }

        self.keys[key_id] = key_data
        self._save_keys()

    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve an encryption key.

        Args:
            key_id: The key identifier

        Returns:
            bytes: The key if found, None otherwise
        """
        if key_id not in self.keys:
            return None

        key_data = self.keys[key_id]
        if not key_data.get("active", False):
            return None

        # In a real implementation, you would retrieve the actual key
        # from secure storage (e.g., AWS KMS, Azure Key Vault, etc.)
        # For now, we'll return None as this is a placeholder
        return None

    def rotate_key(self, key_id: str) -> bytes:
        """
        Rotate an encryption key.

        Args:
            key_id: The key identifier to rotate

        Returns:
            bytes: The new key
        """
        if key_id not in self.keys:
            raise ValueError(f"Key {key_id} not found")

        key_data = self.keys[key_id]
        key_type = key_data["key_type"]

        # Generate new key
        new_key = self.generate_secure_key(key_id, key_type)

        # Update version
        key_data["version"] += 1
        key_data["rotated_at"] = datetime.utcnow().isoformat()

        self._save_keys()
        return new_key

    def deactivate_key(self, key_id: str) -> None:
        """
        Deactivate an encryption key.

        Args:
            key_id: The key identifier to deactivate
        """
        if key_id in self.keys:
            self.keys[key_id]["active"] = False
            self.keys[key_id]["deactivated_at"] = datetime.utcnow().isoformat()
            self._save_keys()

    def list_keys(self) -> List[Dict]:
        """
        List all keys with their metadata.

        Returns:
            List[Dict]: List of key metadata
        """
        return [
            {"key_id": key_id, **key_data} for key_id, key_data in self.keys.items()
        ]

    def get_key_metadata(self, key_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific key.

        Args:
            key_id: The key identifier

        Returns:
            Dict: Key metadata if found, None otherwise
        """
        if key_id not in self.keys:
            return None

        return {"key_id": key_id, **self.keys[key_id]}


def generate_secure_key(key_type: str = "aes") -> bytes:
    """
    Generate a secure encryption key.

    Args:
        key_type: Type of key ("aes", "rsa")

    Returns:
        bytes: The generated key
    """
    if key_type == "aes":
        return generate_encryption_key()
    elif key_type == "rsa":
        private_key, _ = generate_key_pair()
        return private_key
    else:
        raise ValueError(f"Unsupported key type: {key_type}")


def generate_key_derivation_salt() -> bytes:
    """
    Generate a secure salt for key derivation.

    Returns:
        bytes: A 16-byte salt
    """
    return generate_key_derivation_salt()


def store_key(
    key_id: str, key: bytes, key_type: str = "aes", metadata: Optional[Dict] = None
) -> None:
    """
    Store an encryption key.

    Args:
        key_id: Unique identifier for the key
        key: The key to store
        key_type: Type of key ("aes", "rsa")
        metadata: Additional metadata for the key
    """
    # In a real implementation, this would store the key securely
    # For now, this is a placeholder
    pass


def retrieve_key(key_id: str) -> Optional[bytes]:
    """
    Retrieve an encryption key.

    Args:
        key_id: The key identifier

    Returns:
        bytes: The key if found, None otherwise
    """
    # In a real implementation, this would retrieve the key from secure storage
    # For now, this is a placeholder
    return None


def rotate_key(key_id: str) -> bytes:
    """
    Rotate an encryption key.

    Args:
        key_id: The key identifier to rotate

    Returns:
        bytes: The new key
    """
    # In a real implementation, this would rotate the key in secure storage
    # For now, this is a placeholder
    return generate_secure_key()
