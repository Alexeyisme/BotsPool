"""
Core encryption functions for symmetric and asymmetric encryption
"""

import os
import base64
import hashlib
from typing import Union, Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import secrets


def generate_encryption_key() -> bytes:
    """
    Generate a secure 256-bit encryption key.

    Returns:
        bytes: A 32-byte encryption key
    """
    return secrets.token_bytes(32)


def generate_key_derivation_salt() -> bytes:
    """
    Generate a secure salt for key derivation.

    Returns:
        bytes: A 16-byte salt
    """
    return secrets.token_bytes(16)


def derive_key_from_password(
    password: str, salt: bytes, iterations: int = 100000
) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2.

    Args:
        password: The password to derive the key from
        salt: The salt for key derivation
        iterations: Number of PBKDF2 iterations (default: 100000)

    Returns:
        bytes: The derived encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(data: Union[str, bytes], key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt data using AES-256-GCM.

    Args:
        data: The data to encrypt (string or bytes)
        key: The encryption key (32 bytes)

    Returns:
        Tuple[bytes, bytes, bytes]: (encrypted_data, iv, auth_tag)
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    # Generate a random IV
    iv = secrets.token_bytes(12)  # 96-bit IV for GCM

    # Create cipher
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Encrypt the data
    encrypted_data = encryptor.update(data) + encryptor.finalize()

    return encrypted_data, iv, encryptor.tag


def decrypt_data(
    encrypted_data: bytes, key: bytes, iv: bytes, auth_tag: bytes
) -> bytes:
    """
    Decrypt data using AES-256-GCM.

    Args:
        encrypted_data: The encrypted data
        key: The decryption key (32 bytes)
        iv: The initialization vector
        auth_tag: The authentication tag

    Returns:
        bytes: The decrypted data

    Raises:
        InvalidTag: If authentication fails
    """
    # Create cipher
    cipher = Cipher(
        algorithms.AES(key), modes.GCM(iv, auth_tag), backend=default_backend()
    )
    decryptor = cipher.decryptor()

    # Decrypt the data
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    return decrypted_data


def encrypt_field(field_value: Union[str, bytes], key: bytes) -> str:
    """
    Encrypt a field value and return a base64-encoded string.

    Args:
        field_value: The field value to encrypt
        key: The encryption key

    Returns:
        str: Base64-encoded encrypted data with IV and auth tag
    """
    encrypted_data, iv, auth_tag = encrypt_data(field_value, key)

    # Combine encrypted data, IV, and auth tag
    combined = encrypted_data + iv + auth_tag

    # Encode as base64
    return base64.b64encode(combined).decode("utf-8")


def decrypt_field(encrypted_field: str, key: bytes) -> bytes:
    """
    Decrypt a field value from a base64-encoded string.

    Args:
        encrypted_field: Base64-encoded encrypted data
        key: The decryption key

    Returns:
        bytes: The decrypted field value

    Raises:
        InvalidTag: If authentication fails
        ValueError: If the encrypted field format is invalid
    """
    try:
        # Decode from base64
        combined = base64.b64decode(encrypted_field.encode("utf-8"))

        # Extract components
        # Auth tag is 16 bytes, IV is 12 bytes
        auth_tag = combined[-16:]
        iv = combined[-28:-16]
        encrypted_data = combined[:-28]

        # Decrypt the data
        return decrypt_data(encrypted_data, key, iv, auth_tag)

    except Exception as e:
        raise ValueError(f"Failed to decrypt field: {str(e)}") from e


def generate_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
    """
    Generate an RSA key pair.

    Args:
        key_size: The key size in bits (default: 2048)

    Returns:
        Tuple[bytes, bytes]: (private_key_pem, public_key_pem)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size, backend=default_backend()
    )

    # Get public key
    public_key = private_key.public_key()

    # Serialize keys
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def encrypt_with_public_key(data: Union[str, bytes], public_key_pem: bytes) -> bytes:
    """
    Encrypt data using an RSA public key.

    Args:
        data: The data to encrypt
        public_key_pem: The public key in PEM format

    Returns:
        bytes: The encrypted data
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    # Load public key
    public_key = serialization.load_pem_public_key(
        public_key_pem, backend=default_backend()
    )

    # Encrypt the data
    encrypted_data = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return encrypted_data


def decrypt_with_private_key(encrypted_data: bytes, private_key_pem: bytes) -> bytes:
    """
    Decrypt data using an RSA private key.

    Args:
        encrypted_data: The encrypted data
        private_key_pem: The private key in PEM format

    Returns:
        bytes: The decrypted data
    """
    # Load private key
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )

    # Decrypt the data
    decrypted_data = private_key.decrypt(
        encrypted_data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return decrypted_data


def hash_data(data: Union[str, bytes], algorithm: str = "sha256") -> str:
    """
    Hash data using the specified algorithm.

    Args:
        data: The data to hash
        algorithm: The hash algorithm ('sha256', 'sha512', 'blake2b')

    Returns:
        str: The hexadecimal hash of the data
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if algorithm == "sha256":
        hash_obj = hashlib.sha256(data)
    elif algorithm == "sha512":
        hash_obj = hashlib.sha512(data)
    elif algorithm == "blake2b":
        hash_obj = hashlib.blake2b(data)
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    return hash_obj.hexdigest()


def verify_hash(
    data: Union[str, bytes], hash_value: str, algorithm: str = "sha256"
) -> bool:
    """
    Verify that data matches a hash value.

    Args:
        data: The data to verify
        hash_value: The expected hash value
        algorithm: The hash algorithm used

    Returns:
        bool: True if the hash matches, False otherwise
    """
    computed_hash = hash_data(data, algorithm)
    return computed_hash == hash_value
