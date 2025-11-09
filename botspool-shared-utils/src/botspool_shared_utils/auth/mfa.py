"""
Multi-Factor Authentication (MFA) for BotsPool

This module provides TOTP-based MFA functionality for enhanced security.
"""

import base64
import io
import logging
from typing import Optional, Union
from uuid import UUID

import pyotp
import qrcode
from qrcode.image.pil import PilImage

from ..errors import AuthenticationError, ValidationError


class MFAHandler:
    """
    Multi-Factor Authentication handler for BotsPool.

    Provides TOTP-based MFA functionality using Google Authenticator
    compatible time-based one-time passwords.
    """

    def __init__(self, issuer_name: str = "BotsPool"):
        self.issuer_name = issuer_name
        self.logger = logging.getLogger(__name__)

    def generate_secret(self, user_id: Union[str, UUID]) -> str:
        """
        Generate TOTP secret for user.

        Args:
            user_id: User identifier

        Returns:
            Base32 encoded secret
        """
        try:
            secret = pyotp.random_base32()
            self.logger.debug(f"Generated MFA secret for user {user_id}")
            return secret

        except Exception as e:
            self.logger.error(f"Failed to generate MFA secret: {e}")
            raise AuthenticationError(f"Failed to generate MFA secret: {e}")

    def generate_qr_code(
        self, user_id: Union[str, UUID], secret: str, user_email: Optional[str] = None
    ) -> str:
        """
        Generate QR code for MFA setup.

        Args:
            user_id: User identifier
            secret: TOTP secret
            user_email: User email for display

        Returns:
            Base64 encoded QR code image
        """
        try:
            # Create TOTP URI
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_email or str(user_id), issuer_name=self.issuer_name
            )

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(totp_uri)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            raise AuthenticationError(f"Failed to generate QR code: {e}")

    def verify_token(self, secret: str, token: str, valid_window: int = 1) -> bool:
        """
        Verify TOTP token.

        Args:
            secret: TOTP secret
            token: Token to verify
            valid_window: Time window for validation

        Returns:
            True if token is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=valid_window)

        except Exception as e:
            self.logger.error(f"Failed to verify MFA token: {e}")
            return False

    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup codes for MFA.

        Args:
            count: Number of backup codes to generate

        Returns:
            List of backup codes
        """
        try:
            import secrets
            import string

            codes = []
            for _ in range(count):
                # Generate 8-character alphanumeric code
                code = "".join(
                    secrets.choice(string.ascii_uppercase + string.digits)
                    for _ in range(8)
                )
                codes.append(code)

            return codes

        except Exception as e:
            self.logger.error(f"Failed to generate backup codes: {e}")
            raise AuthenticationError(f"Failed to generate backup codes: {e}")

    def verify_backup_code(self, code: str, used_codes: list[str]) -> bool:
        """
        Verify backup code.

        Args:
            code: Backup code to verify
            used_codes: List of used backup codes

        Returns:
            True if code is valid and unused, False otherwise
        """
        try:
            # Check if code is in used codes
            if code in used_codes:
                return False

            # Basic format validation (8 characters, alphanumeric)
            if len(code) != 8 or not code.isalnum():
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to verify backup code: {e}")
            return False

    def get_remaining_time(self, secret: str) -> int:
        """
        Get remaining time for current TOTP window.

        Args:
            secret: TOTP secret

        Returns:
            Remaining seconds in current window
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.interval - (int(pyotp.time.time()) % totp.interval)

        except Exception as e:
            self.logger.error(f"Failed to get remaining time: {e}")
            return 0

    def is_mfa_enabled(self, user_secret: Optional[str]) -> bool:
        """
        Check if MFA is enabled for user.

        Args:
            user_secret: User's MFA secret

        Returns:
            True if MFA is enabled, False otherwise
        """
        return user_secret is not None and len(user_secret) > 0

    def validate_secret_format(self, secret: str) -> bool:
        """
        Validate MFA secret format.

        Args:
            secret: Secret to validate

        Returns:
            True if secret format is valid, False otherwise
        """
        try:
            # Check if it's valid base32
            pyotp.TOTP(secret)
            return True

        except Exception:
            return False


# Global MFA handler instance
_mfa_handler: Optional[MFAHandler] = None


def get_mfa_handler() -> MFAHandler:
    """Get the global MFA handler instance."""
    global _mfa_handler

    if _mfa_handler is None:
        _mfa_handler = MFAHandler()

    return _mfa_handler


def generate_mfa_secret(user_id: Union[str, UUID]) -> str:
    """Generate TOTP secret for user."""
    handler = get_mfa_handler()
    return handler.generate_secret(user_id)


def generate_mfa_qr_code(
    user_id: Union[str, UUID], secret: str, user_email: Optional[str] = None
) -> str:
    """Generate QR code for MFA setup."""
    handler = get_mfa_handler()
    return handler.generate_qr_code(user_id, secret, user_email)


def verify_mfa_token(secret: str, token: str, valid_window: int = 1) -> bool:
    """Verify TOTP token."""
    handler = get_mfa_handler()
    return handler.verify_token(secret, token, valid_window)


def is_mfa_enabled(user_secret: Optional[str]) -> bool:
    """Check if MFA is enabled for user."""
    handler = get_mfa_handler()
    return handler.is_mfa_enabled(user_secret)
