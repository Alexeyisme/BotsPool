"""Data models for the bot"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class GraphUnavailableError(Exception):
    """Exception raised when a graph service is unavailable"""

    def __init__(self, agent: str):
        self.agent = agent
        super().__init__(f"Graph {agent} is unavailable")


class AuthRefreshError(Exception):
    """Exception raised when token refresh fails and re-auth is required."""

    def __init__(self, message: str = "Authentication needs to be refreshed"):
        super().__init__(message)


class UserContext(BaseModel):
    """User context information"""

    chat_id: int
    telegram_user_id: int
    active_agent: str = "todo"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires: Optional[float] = None
