"""Reusable notification tools for LangGraph agents."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationClientConfig:
    """Configuration for notification tooling."""

    base_url: str
    api_key: str
    agent: str
    frontend: str = "telegram"
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(
        cls,
        *,
        agent: str,
        frontend: str = "telegram",
        base_url_var: str = "NOTIFICATION_SERVICE_URL",
        api_key_var: str = "NOTIFICATION_API_KEY",
        default_base_url: str = "http://botspool-notification-service:8090",
        default_api_key: str = "dev-secret-key-change-in-production",
    ) -> "NotificationClientConfig":
        """Create a configuration using environment variables."""

        base_url = os.getenv(base_url_var, default_base_url)
        api_key = os.getenv(api_key_var, default_api_key)
        return cls(base_url=base_url, api_key=api_key, agent=agent, frontend=frontend)


@dataclass(frozen=True)
class NotificationToolset:
    """Collection of notification tools and helpers."""

    send_notification: Callable[..., Awaitable[str]]
    schedule_reminder: Callable[..., Awaitable[str]]
    cancel_reminder: Callable[..., Awaitable[str]]
    list_user_reminders: Callable[..., Awaitable[str]]
    send_notification_impl: Callable[..., Awaitable[str]]
    schedule_reminder_impl: Callable[..., Awaitable[str]]
    list_user_reminders_impl: Callable[..., Awaitable[str]]


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def create_notification_toolset(
    config: NotificationClientConfig,
) -> NotificationToolset:
    """Create a LangGraph-compatible notification toolset."""

    base_url = _normalize_base_url(config.base_url)

    async def _send_notification_impl(
        *,
        message: str,
        chat_id: int,
        user_id: str,
        priority: str = "normal",
        notification_type: str = "info",
    ) -> str:
        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "frontend": config.frontend,
            "message": message,
            "agent": config.agent,
            "priority": priority,
            "notification_type": notification_type,
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": config.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(
                    f"{base_url}/api/v1/notifications", json=payload, headers=headers
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to send notification (status %s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return f"Error: Failed to send notification (status {exc.response.status_code})"
        except httpx.RequestError as exc:
            logger.error("Failed to connect to notification service: %s", exc)
            return f"Error: Could not reach notification service ({exc})"
        except Exception as exc:  # pragma: no cover - unexpected network failure
            logger.error("Unexpected notification error: %s", exc, exc_info=True)
            return f"Error: Unexpected notification failure ({exc})"

        logger.info("Notification sent to chat %s for user %s", chat_id, user_id)
        return "Notification sent successfully"

    async def _schedule_reminder_impl(
        *,
        message: str,
        hours_from_now: float,
        chat_id: int,
        user_id: str,
        reminder_type: str = "task_due",
    ) -> str:
        if hours_from_now <= 0:
            return "Error: hours_from_now must be positive"

        scheduled_for = datetime.utcnow() + timedelta(hours=hours_from_now)

        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "frontend": config.frontend,
            "message": message,
            "agent": config.agent,
            "priority": "normal",
            "notification_type": reminder_type,
            "scheduled_for": scheduled_for.isoformat(),
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": config.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(
                    f"{base_url}/api/v1/notifications/schedule",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to schedule reminder (status %s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return f"Error: Failed to schedule reminder (status {exc.response.status_code})"
        except httpx.RequestError as exc:
            logger.error("Failed to connect to notification service: %s", exc)
            return f"Error: Could not reach notification service ({exc})"
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected reminder scheduling error: %s", exc, exc_info=True)
            return f"Error: Unexpected reminder scheduling failure ({exc})"

        notification_id = data.get("notification_id")
        logger.info(
            "Reminder scheduled for chat %s at %s (id=%s)",
            chat_id,
            scheduled_for.isoformat(),
            notification_id,
        )
        return "Reminder scheduled for {hours} hours from now (at {time})".format(
            hours=hours_from_now,
            time=scheduled_for.strftime("%Y-%m-%d %H:%M UTC"),
        )

    async def _cancel_reminder_impl(reminder_id: str) -> str:
        headers = {"X-API-Key": config.api_key}

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.delete(
                    f"{base_url}/api/v1/notifications/{reminder_id}", headers=headers
                )

            if response.status_code == 404:
                return "Reminder not found (it may have already been sent or cancelled)"

            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to cancel reminder (status %s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return (
                f"Error: Failed to cancel reminder (status {exc.response.status_code})"
            )
        except httpx.RequestError as exc:
            logger.error("Failed to connect to notification service: %s", exc)
            return f"Error: Could not reach notification service ({exc})"
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Unexpected reminder cancellation error: %s", exc, exc_info=True
            )
            return f"Error: Unexpected reminder cancellation failure ({exc})"

        logger.info("Reminder cancelled: %s", reminder_id)
        return "Reminder cancelled successfully"

    async def _list_user_reminders_impl(user_id: str) -> str:
        headers = {"X-API-Key": config.api_key}

        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.get(
                    f"{base_url}/api/v1/notifications/user/{user_id}",
                    headers=headers,
                    params={"status": "pending"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to list reminders (status %s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return (
                f"Error: Failed to list reminders (status {exc.response.status_code})"
            )
        except httpx.RequestError as exc:
            logger.error("Failed to connect to notification service: %s", exc)
            return f"Error: Could not reach notification service ({exc})"
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected reminder listing error: %s", exc, exc_info=True)
            return f"Error: Unexpected reminder listing failure ({exc})"

        notifications: List[Dict[str, Any]] = data.get("notifications", [])
        if not notifications:
            return "You have no scheduled reminders"

        lines = [f"You have {len(notifications)} scheduled reminder(s):"]
        for notif in notifications:
            scheduled_time = notif.get("scheduled_for", "unknown time")
            message = notif.get("message", "")
            lines.append(f"- {message} (scheduled for {scheduled_time})")
        return "\n".join(lines)

    # LangGraph tool stubs used by the LLM; real work happens via the *_impl functions
    @tool
    async def send_notification(
        message: str, priority: str = "normal", notification_type: str = "info"
    ) -> str:
        """Request that an agent sends an immediate notification (context injected upstream)."""
        return "This tool is routed through execute_notification_tools for context injection."

    @tool
    async def schedule_reminder(
        message: str, hours_from_now: float, reminder_type: str = "task_due"
    ) -> str:
        """Request that an agent schedules a reminder (context injected upstream)."""
        return "This tool is routed through execute_notification_tools for context injection."

    @tool
    async def list_user_reminders() -> str:
        """Request that an agent lists scheduled reminders (context injected upstream)."""
        return "This tool is routed through execute_notification_tools for context injection."

    @tool
    async def cancel_reminder(reminder_id: str) -> str:
        """Cancel a scheduled reminder by identifier using the notification service."""
        return await _cancel_reminder_impl(reminder_id)

    return NotificationToolset(
        send_notification=send_notification,
        schedule_reminder=schedule_reminder,
        cancel_reminder=cancel_reminder,
        list_user_reminders=list_user_reminders,
        send_notification_impl=_send_notification_impl,
        schedule_reminder_impl=_schedule_reminder_impl,
        list_user_reminders_impl=_list_user_reminders_impl,
    )
