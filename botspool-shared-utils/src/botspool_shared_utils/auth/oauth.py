"""
OAuth2 integration for BotsPool

This module provides OAuth2 authentication with Google and GitHub providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ..errors import AuthenticationError, ExternalServiceError
from ..models.enums import AuthProvider


class OAuthProvider(ABC):
    """Abstract base class for OAuth providers."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Get authorization URL for OAuth flow."""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from provider."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name."""
        pass


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth2 provider."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            self.logger.error(f"Google token exchange failed: {e}")
            raise ExternalServiceError(f"Google token exchange failed: {e}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.user_info_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            self.logger.error(f"Google user info fetch failed: {e}")
            raise ExternalServiceError(f"Google user info fetch failed: {e}")

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "google"


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth2 provider."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"

    def get_authorization_url(self, state: str) -> str:
        """Get GitHub authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",
            "state": state,
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            self.logger.error(f"GitHub token exchange failed: {e}")
            raise ExternalServiceError(f"GitHub token exchange failed: {e}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from GitHub."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.user_info_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                user_data = response.json()

                # Get user email if not public
                if not user_data.get("email"):
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        primary_email = next(
                            (e for e in emails if e.get("primary")), None
                        )
                        if primary_email:
                            user_data["email"] = primary_email["email"]

                return user_data

        except httpx.HTTPError as e:
            self.logger.error(f"GitHub user info fetch failed: {e}")
            raise ExternalServiceError(f"GitHub user info fetch failed: {e}")

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "github"


class OAuthManager:
    """
    OAuth manager for BotsPool.

    Manages OAuth providers and authentication flows.
    """

    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self.logger = logging.getLogger(__name__)

    def register_provider(self, provider: OAuthProvider) -> None:
        """Register an OAuth provider."""
        provider_name = provider.get_provider_name()
        self.providers[provider_name] = provider
        self.logger.info(f"Registered OAuth provider: {provider_name}")

    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name."""
        return self.providers.get(provider_name)

    def get_authorization_url(self, provider_name: str, state: str) -> str:
        """Get authorization URL for provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            raise AuthenticationError(f"OAuth provider not found: {provider_name}")

        return provider.get_authorization_url(state)

    async def authenticate_user(self, provider_name: str, code: str) -> Dict[str, Any]:
        """
        Authenticate user with OAuth provider.

        Args:
            provider_name: OAuth provider name
            code: Authorization code

        Returns:
            User information from provider
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise AuthenticationError(f"OAuth provider not found: {provider_name}")

        try:
            # Exchange code for token
            token_data = await provider.exchange_code_for_token(code)
            access_token = token_data.get("access_token")

            if not access_token:
                raise AuthenticationError("No access token received from provider")

            # Get user information
            user_info = await provider.get_user_info(access_token)

            # Normalize user information
            normalized_info = self._normalize_user_info(provider_name, user_info)

            return normalized_info

        except Exception as e:
            self.logger.error(f"OAuth authentication failed for {provider_name}: {e}")
            raise AuthenticationError(f"OAuth authentication failed: {e}")

    def _normalize_user_info(
        self, provider_name: str, user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize user information from different providers."""
        if provider_name == "google":
            return {
                "provider": AuthProvider.GOOGLE,
                "provider_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "avatar_url": user_info.get("picture"),
                "verified": user_info.get("verified_email", False),
            }
        elif provider_name == "github":
            return {
                "provider": AuthProvider.GITHUB,
                "provider_id": str(user_info.get("id")),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "first_name": user_info.get("name", "").split(" ")[0]
                if user_info.get("name")
                else None,
                "last_name": " ".join(user_info.get("name", "").split(" ")[1:])
                if user_info.get("name")
                and len(user_info.get("name", "").split(" ")) > 1
                else None,
                "avatar_url": user_info.get("avatar_url"),
                "verified": True,  # GitHub emails are typically verified
            }
        else:
            raise AuthenticationError(f"Unsupported OAuth provider: {provider_name}")

    def get_available_providers(self) -> list[str]:
        """Get list of available OAuth providers."""
        return list(self.providers.keys())

    def is_provider_available(self, provider_name: str) -> bool:
        """Check if OAuth provider is available."""
        return provider_name in self.providers


# Global OAuth manager instance
_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    """Get the global OAuth manager instance."""
    global _oauth_manager

    if _oauth_manager is None:
        _oauth_manager = OAuthManager()

    return _oauth_manager


def register_google_provider(
    client_id: str, client_secret: str, redirect_uri: str
) -> None:
    """Register Google OAuth provider."""
    manager = get_oauth_manager()
    provider = GoogleOAuthProvider(client_id, client_secret, redirect_uri)
    manager.register_provider(provider)


def register_github_provider(
    client_id: str, client_secret: str, redirect_uri: str
) -> None:
    """Register GitHub OAuth provider."""
    manager = get_oauth_manager()
    provider = GitHubOAuthProvider(client_id, client_secret, redirect_uri)
    manager.register_provider(provider)
