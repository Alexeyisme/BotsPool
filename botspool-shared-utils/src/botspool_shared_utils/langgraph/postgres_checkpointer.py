"""LangGraph PostgreSQL checkpointer helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def create_postgres_checkpointer(database_url: str) -> Any:
    """Create an async PostgreSQL checkpointer for LangGraph.

    Args:
        database_url: PostgreSQL database connection URL (SQLAlchemy format accepted)

    Returns:
        AsyncPostgresSaver: Configured async PostgreSQL checkpointer instance

    Raises:
        RuntimeError: If LangGraph dependencies are missing
        Exception: For any other initialisation failure
    """

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        logger.info("Initializing Async PostgreSQL checkpointer...")

        # LangGraph PostgresSaver expects a standard postgresql:// URL
        if database_url.startswith("postgresql+asyncpg://"):
            postgres_url = database_url.replace(
                "postgresql+asyncpg://", "postgresql://", 1
            )
        elif database_url.startswith("postgresql://"):
            postgres_url = database_url
        else:
            logger.warning(
                "Unexpected database URL format '%s'; using as-is", database_url
            )
            postgres_url = database_url

        checkpointer_manager = AsyncPostgresSaver.from_conn_string(postgres_url)
        checkpointer = await checkpointer_manager.__aenter__()
        logger.info("Async PostgreSQL checkpointer initialized successfully")

        # Store the manager for cleanup in close_postgres_checkpointer
        setattr(checkpointer, "_manager", checkpointer_manager)
        return checkpointer

    except ImportError as exc:  # pragma: no cover - missing optional dependency
        logger.error("Failed to import AsyncPostgresSaver: %s", exc)
        raise RuntimeError(
            "langgraph-checkpoint-postgres not installed. Install with "
            "'pip install langgraph-checkpoint-postgres'."
        ) from exc
    except Exception as exc:  # pragma: no cover - pass-through for callers to handle
        logger.error("Failed to create Async PostgreSQL checkpointer: %s", exc)
        raise


async def close_postgres_checkpointer(checkpointer: Any) -> None:
    """Close PostgreSQL checkpointer connections.

    Args:
        checkpointer: AsyncPostgresSaver instance to close
    """

    try:
        if not checkpointer:
            return

        manager = getattr(checkpointer, "_manager", None)
        if manager is not None:
            await manager.__aexit__(None, None, None)
        elif hasattr(checkpointer, "connector"):
            await checkpointer.connector.close()

        logger.info("PostgreSQL checkpointer closed successfully")
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.warning("Error closing PostgreSQL checkpointer: %s", exc)
