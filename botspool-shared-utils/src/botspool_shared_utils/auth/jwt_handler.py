"""
JWT token management for BotsPool

This module provides JWT token generation, validation, and management
using RS256 algorithm for secure authentication.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import JWTError

from ..errors import (
    TokenExpiredError,
    InvalidTokenError,
    AuthenticationError,
    ConfigurationError,
)
from ..models.enums import UserRole, Permission, FrontendType, GraphType


class JWTHandler:
    """
    JWT token handler for BotsPool authentication.

    Provides secure token generation, validation, and management using RS256.
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        algorithm: str = "RS256",
        access_token_expiry: int = 3600,  # 1 hour
        refresh_token_expiry: int = 2592000,  # 30 days
        issuer: str = "botspool.ai",
        audience: str = "botspool-api",
    ):
        self.algorithm = algorithm
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.issuer = issuer
        self.audience = audience
        self.logger = logging.getLogger(__name__)

        # Initialize keys
        if private_key and public_key:
            self.private_key = private_key
            self.public_key = public_key
        else:
            self.private_key, self.public_key = self._generate_key_pair()

    def _generate_key_pair(self) -> tuple[str, str]:
        """Generate RSA key pair for JWT signing."""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

            # Get public key
            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            return private_pem, public_pem

        except Exception as e:
            self.logger.error(f"Failed to generate key pair: {e}")
            raise ConfigurationError(f"Failed to generate JWT key pair: {e}")

    def generate_access_token(
        self,
        user_id: Union[str, UUID],
        role: UserRole,
        permissions: List[Permission],
        frontend_type: FrontendType,
        allowed_graphs: List[GraphType],
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate access token for user.

        Args:
            user_id: User identifier
            role: User role
            permissions: List of user permissions
            frontend_type: Type of frontend (telegram, discord, web, etc.)
            allowed_graphs: List of graph types user can access
            additional_claims: Additional JWT claims

        Returns:
            JWT access token
        """
        try:
            now = datetime.utcnow()

            payload = {
                "sub": str(user_id),
                "iss": self.issuer,
                "aud": self.audience,
                "iat": now,
                "exp": now + timedelta(seconds=self.access_token_expiry),
                "type": "access",
                "role": role.value,
                "permissions": [p.value for p in permissions],
                "frontend_type": frontend_type.value,
                "allowed_graphs": [g.value for g in allowed_graphs],
                "jti": str(uuid4()),  # JWT ID for revocation
            }

            # Add additional claims
            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)

            self.logger.debug(f"Generated access token for user {user_id}")
            return token

        except Exception as e:
            self.logger.error(f"Failed to generate access token: {e}")
            raise AuthenticationError(f"Failed to generate access token: {e}")

    def generate_refresh_token(
        self,
        user_id: Union[str, UUID],
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate refresh token for user.

        Args:
            user_id: User identifier
            additional_claims: Additional JWT claims

        Returns:
            JWT refresh token
        """
        try:
            now = datetime.utcnow()

            payload = {
                "sub": str(user_id),
                "iss": self.issuer,
                "aud": self.audience,
                "iat": now,
                "exp": now + timedelta(seconds=self.refresh_token_expiry),
                "type": "refresh",
                "jti": str(uuid4()),
            }

            # Add additional claims
            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)

            self.logger.debug(f"Generated refresh token for user {user_id}")
            return token

        except Exception as e:
            self.logger.error(f"Failed to generate refresh token: {e}")
            raise AuthenticationError(f"Failed to generate refresh token: {e}")

    def validate_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Validate JWT token.

        Args:
            token: JWT token to validate
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )

            # Validate token type
            if payload.get("type") != token_type:
                raise InvalidTokenError("Invalid token type")

            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise TokenExpiredError("Token has expired")

            self.logger.debug(
                f"Validated {token_type} token for user {payload.get('sub')}"
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}")
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            raise InvalidTokenError(f"Token validation failed: {e}")

    def refresh_access_token(
        self,
        refresh_token: str,
        frontend_type: FrontendType,
        allowed_graphs: List[GraphType],
    ) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token
            frontend_type: Type of frontend (telegram, discord, web, etc.)
            allowed_graphs: List of graph types user can access

        Returns:
            Dictionary with new access token and refresh token
        """
        try:
            # Validate refresh token
            payload = self.validate_token(refresh_token, "refresh")
            user_id = payload["sub"]

            # Get user role and permissions (this would typically come from database)
            # For now, we'll use the payload if available
            role = UserRole(payload.get("role", UserRole.FREE_USER.value))
            permissions = [Permission(p) for p in payload.get("permissions", [])]

            # Generate new access token
            new_access_token = self.generate_access_token(
                user_id=user_id,
                role=role,
                permissions=permissions,
                frontend_type=frontend_type,
                allowed_graphs=allowed_graphs,
            )

            # Generate new refresh token
            new_refresh_token = self.generate_refresh_token(user_id)

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expiry,
            }

        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Get token information without validation.

        Args:
            token: JWT token

        Returns:
            Token information
        """
        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})

            return {
                "user_id": payload.get("sub"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", []),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "token_type": payload.get("type"),
                "jti": payload.get("jti"),
            }

        except Exception as e:
            self.logger.error(f"Failed to get token info: {e}")
            raise InvalidTokenError(f"Failed to get token info: {e}")

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired without full validation.

        Args:
            token: JWT token

        Returns:
            True if expired, False otherwise
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})

            exp = payload.get("exp")
            if exp:
                return datetime.utcnow().timestamp() > exp

            return False

        except Exception:
            return True

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to blacklist).

        Note: This is a simple implementation. In production, you'd want to
        use a more sophisticated token blacklist system with Redis or database.

        Args:
            token: JWT token to revoke

        Returns:
            True if successful
        """
        try:
            # Get token info
            token_info = self.get_token_info(token)
            jti = token_info.get("jti")

            if jti:
                # In a real implementation, you would store the JTI in a blacklist
                # For now, we'll just log it
                self.logger.info(f"Token revoked: {jti}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to revoke token: {e}")
            return False


# Global JWT handler instance
_jwt_handler: Optional[JWTHandler] = None


def create_jwt_handler(
    private_key: Optional[str] = None, public_key: Optional[str] = None, **kwargs
) -> JWTHandler:
    """
    Create and configure JWT handler.

    Args:
        private_key: Private key for signing (optional, will generate if not provided)
        public_key: Public key for verification (optional, will generate if not provided)
        **kwargs: Additional JWT handler configuration

    Returns:
        Configured JWTHandler instance
    """
    global _jwt_handler

    _jwt_handler = JWTHandler(private_key=private_key, public_key=public_key, **kwargs)

    return _jwt_handler


def get_jwt_handler() -> JWTHandler:
    """
    Get the global JWT handler instance.

    Returns:
        JWTHandler instance

    Raises:
        ConfigurationError: If JWT handler is not initialized
    """
    global _jwt_handler

    if _jwt_handler is None:
        raise ConfigurationError("JWT handler not initialized")

    return _jwt_handler


def generate_token(
    user_id: Union[str, UUID], role: UserRole, permissions: List[Permission], **kwargs
) -> str:
    """
    Generate access token for user.

    Convenience function for generating tokens.
    """
    handler = get_jwt_handler()
    return handler.generate_access_token(user_id, role, permissions, **kwargs)


def validate_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Validate JWT token.

    Convenience function for validating tokens.
    """
    handler = get_jwt_handler()
    return handler.validate_token(token, token_type)


def refresh_token(refresh_token: str) -> Dict[str, str]:
    """
    Refresh access token.

    Convenience function for refreshing tokens.
    """
    handler = get_jwt_handler()
    return handler.refresh_access_token(refresh_token)
