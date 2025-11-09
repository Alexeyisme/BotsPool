"""
Session management for BotsPool

This module provides session management functionality including
session creation, validation, and cleanup.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import redis.asyncio as redis

from ..errors import AuthenticationError, ConfigurationError
from ..models.enums import FrontendType, GraphType
from ..redis_utils import RedisManager, RedisKeyPatterns, SessionData


class SessionManager:
    """
    Session manager for BotsPool.

    Manages user sessions using Redis for storage and provides
    session validation, cleanup, and management functionality.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        default_expiry: int = 86400,  # 24 hours (as per architecture)
        cleanup_interval: int = 300,  # 5 minutes
    ):
        self.redis_client = redis_client
        self.redis_manager = RedisManager(redis_client)
        self.default_expiry = default_expiry
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger(__name__)

        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Start the session cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())

    async def _cleanup_expired_sessions(self) -> None:
        """Cleanup expired sessions periodically."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Session cleanup error: {e}")

    async def create_session(
        self,
        session_id: str,
        user_id: Union[str, UUID],
        frontend_type: FrontendType,
        current_graph: Optional[GraphType] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user session using architecture-compliant Redis patterns.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            frontend_type: Frontend type
            current_graph: Current graph type user is interacting with
            ip_address: Client IP address
            user_agent: Client user agent
            expires_at: Session expiration time
            additional_data: Additional session data

        Returns:
            Session data
        """
        try:
            # Prepare session data according to architecture specification
            session_data = {
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                **(additional_data or {}),
            }

            # Create session using Redis manager
            session = await self.redis_manager.create_session(
                user_id=user_id,
                frontend_type=frontend_type,
                current_graph=current_graph,
                session_data=session_data,
                ttl=self.default_expiry,
            )

            self.logger.debug(f"Created session for user {user_id}")
            return session.to_dict()

        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            raise AuthenticationError(f"Failed to create session: {e}")

    async def get_session(self, user_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """
        Get session data by user ID using architecture-compliant Redis patterns.

        Args:
            user_id: User identifier

        Returns:
            Session data if found and valid, None otherwise
        """
        try:
            session = await self.redis_manager.get_session(user_id)

            if not session:
                return None

            return session.to_dict()

        except Exception as e:
            self.logger.error(f"Failed to get session for user {user_id}: {e}")
            return None

    async def update_session(
        self,
        user_id: Union[str, UUID],
        current_graph: Optional[GraphType] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update session data using architecture-compliant Redis patterns.

        Args:
            user_id: User identifier
            current_graph: Current graph type user is interacting with
            session_data: Additional session data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.redis_manager.update_session(
                user_id=user_id, current_graph=current_graph, session_data=session_data
            )

        except Exception as e:
            self.logger.error(f"Failed to update session for user {user_id}: {e}")
            return False

    async def delete_session(self, user_id: Union[str, UUID]) -> bool:
        """
        Delete a session using architecture-compliant Redis patterns.

        Args:
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.redis_manager.delete_session(user_id)

        except Exception as e:
            self.logger.error(f"Failed to delete session for user {user_id}: {e}")
            return False

    async def delete_user_sessions(self, user_id: Union[str, UUID]) -> int:
        """
        Delete all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions deleted
        """
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = await self.redis_client.smembers(user_sessions_key)

            deleted_count = 0
            for session_id in session_ids:
                if await self.delete_session(session_id.decode()):
                    deleted_count += 1

            # Clean up user sessions set
            await self.redis_client.delete(user_sessions_key)

            self.logger.info(f"Deleted {deleted_count} sessions for user {user_id}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete sessions for user {user_id}: {e}")
            return 0

    async def validate_session(self, session_id: str) -> bool:
        """
        Validate a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session is valid, False otherwise
        """
        session = await self.get_session(session_id)
        return session is not None and session.get("is_active", False)

    async def extend_session(
        self, session_id: str, additional_seconds: int = None
    ) -> bool:
        """
        Extend session expiration time.

        Args:
            session_id: Session identifier
            additional_seconds: Additional seconds to add (default: default_expiry)

        Returns:
            True if successful, False otherwise
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            if additional_seconds is None:
                additional_seconds = self.default_expiry

            # Update expiration time
            current_expires = datetime.fromisoformat(session["expires_at"])
            new_expires = current_expires + timedelta(seconds=additional_seconds)

            update_data = {"expires_at": new_expires.isoformat()}
            updated_session = await self.update_session(session_id, update_data)

            return updated_session is not None

        except Exception as e:
            self.logger.error(f"Failed to extend session {session_id}: {e}")
            return False

    async def get_user_sessions(
        self, user_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session data
        """
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = await self.redis_client.smembers(user_sessions_key)

            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id.decode())
                if session:
                    sessions.append(session)

            return sessions

        except Exception as e:
            self.logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            # Get all session keys
            pattern = f"{self.session_prefix}*"
            session_keys = await self.redis_client.keys(pattern)

            cleaned_count = 0
            for key in session_keys:
                try:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        session = json.loads(session_data)
                        expires_at = datetime.fromisoformat(session["expires_at"])

                        if datetime.utcnow() > expires_at:
                            await self.redis_client.delete(key)
                            cleaned_count += 1

                except Exception as e:
                    self.logger.warning(f"Failed to cleanup session {key}: {e}")

            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} expired sessions")

            return cleaned_count

        except Exception as e:
            self.logger.error(f"Session cleanup failed: {e}")
            return 0

    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Session statistics
        """
        try:
            # Get all session keys
            pattern = f"{self.session_prefix}*"
            session_keys = await self.redis_client.keys(pattern)

            total_sessions = len(session_keys)
            active_sessions = 0
            expired_sessions = 0

            for key in session_keys:
                try:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        session = json.loads(session_data)
                        expires_at = datetime.fromisoformat(session["expires_at"])

                        if datetime.utcnow() > expires_at:
                            expired_sessions += 1
                        else:
                            active_sessions += 1

                except Exception:
                    expired_sessions += 1

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "cleanup_interval": self.cleanup_interval,
                "default_expiry": self.default_expiry,
            }

        except Exception as e:
            self.logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}

    async def close(self) -> None:
        """Close the session manager and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def create_session_manager(redis_client: redis.Redis, **kwargs) -> SessionManager:
    """Create and configure session manager."""
    global _session_manager

    _session_manager = SessionManager(redis_client, **kwargs)
    return _session_manager


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager

    if _session_manager is None:
        raise ConfigurationError("Session manager not initialized")

    return _session_manager


async def create_session(
    session_id: str, user_id: Union[str, UUID], frontend_type: FrontendType, **kwargs
) -> Dict[str, Any]:
    """Create a new user session."""
    manager = get_session_manager()
    return await manager.create_session(session_id, user_id, frontend_type, **kwargs)


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data by session ID."""
    manager = get_session_manager()
    return await manager.get_session(session_id)


async def update_session(
    session_id: str, update_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Update session data."""
    manager = get_session_manager()
    return await manager.update_session(session_id, update_data)


async def delete_session(session_id: str) -> bool:
    """Delete a session."""
    manager = get_session_manager()
    return await manager.delete_session(session_id)


async def cleanup_expired_sessions() -> int:
    """Cleanup expired sessions."""
    manager = get_session_manager()
    return await manager.cleanup_expired_sessions()
