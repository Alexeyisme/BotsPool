"""
Password management utilities for BotsPool

This module provides secure password hashing, validation, and reset functionality.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID

from passlib.context import CryptContext
from passlib.hash import bcrypt

from ..errors import ValidationError, AuthenticationError


class PasswordManager:
    """
    Password management utility for BotsPool.

    Provides secure password hashing, validation, and reset functionality.
    """

    def __init__(self, rounds: int = 12):
        """
        Initialize password manager.

        Args:
            rounds: Number of bcrypt rounds (higher = more secure, slower)
        """
        self.context = CryptContext(
            schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=rounds
        )

    def hash_password(self, password: str) -> str:
        """
        Hash a password securely.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        return self.context.verify(password, hashed_password)

    def validate_password_strength(self, password: str) -> bool:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            True if password meets strength requirements

        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in password):
            raise ValidationError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            raise ValidationError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain at least one number")

        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            raise ValidationError(
                "Password must contain at least one special character"
            )

        # Check for common passwords
        common_passwords = [
            "password",
            "123456",
            "123456789",
            "qwerty",
            "abc123",
            "password123",
            "admin",
            "letmein",
            "welcome",
            "monkey",
        ]

        if password.lower() in common_passwords:
            raise ValidationError("Password is too common")

        return True

    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a secure random password.

        Args:
            length: Password length

        Returns:
            Generated password
        """
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(characters) for _ in range(length))

        # Ensure password meets requirements
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)

        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)

        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)

        if not any(c in "!@#$%^&*" for c in password):
            password = password[:-1] + secrets.choice("!@#$%^&*")

        return password

    def generate_password_reset_token(self) -> str:
        """
        Generate a secure password reset token.

        Returns:
            Password reset token
        """
        return secrets.token_urlsafe(32)

    def verify_password_reset_token(
        self, token: str, stored_token: str, expiry: datetime
    ) -> bool:
        """
        Verify a password reset token.

        Args:
            token: Token to verify
            stored_token: Stored token hash
            expiry: Token expiry time

        Returns:
            True if token is valid and not expired
        """
        if datetime.utcnow() > expiry:
            return False

        return secrets.compare_digest(token, stored_token)


# Global password manager instance
_password_manager: Optional[PasswordManager] = None


def get_password_manager() -> PasswordManager:
    """Get the global password manager instance."""
    global _password_manager

    if _password_manager is None:
        _password_manager = PasswordManager()

    return _password_manager


def hash_password(password: str) -> str:
    """Hash a password securely."""
    manager = get_password_manager()
    return manager.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    manager = get_password_manager()
    return manager.verify_password(password, hashed_password)


def generate_password_reset_token() -> str:
    """Generate a secure password reset token."""
    manager = get_password_manager()
    return manager.generate_password_reset_token()


def verify_password_reset_token(
    token: str, stored_token: str, expiry: datetime
) -> bool:
    """Verify a password reset token."""
    manager = get_password_manager()
    return manager.verify_password_reset_token(token, stored_token, expiry)
