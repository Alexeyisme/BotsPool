"""
Database migration utilities for BotsPool

This module provides database migration management using Alembic.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .connection import DatabaseManager
from ..errors import DatabaseError, ConfigurationError


class MigrationManager:
    """
    Database migration manager for BotsPool.

    Handles database schema migrations using Alembic.
    """

    def __init__(
        self,
        database_manager: DatabaseManager,
        alembic_config_path: Optional[str] = None,
    ):
        self.database_manager = database_manager
        self.alembic_config_path = alembic_config_path or "alembic.ini"
        self.logger = logging.getLogger(__name__)

        # Initialize Alembic config
        self.alembic_cfg = self._create_alembic_config()

    def _create_alembic_config(self) -> Config:
        """Create Alembic configuration."""
        if not Path(self.alembic_config_path).exists():
            raise ConfigurationError(
                f"Alembic config file not found: {self.alembic_config_path}"
            )

        config = Config(self.alembic_config_path)

        # Set database URL
        config.set_main_option("sqlalchemy.url", self.database_manager.database_url)

        return config

    async def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            async with self.database_manager.get_session_context() as session:
                # Check if alembic_version table exists
                result = await session.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """
                    )
                )

                if not result.scalar():
                    return None

                # Get current revision
                result = await session.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                return result.scalar()

        except Exception as e:
            self.logger.error(f"Failed to get current revision: {e}")
            return None

    async def get_available_revisions(self) -> List[str]:
        """Get list of available revisions."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            return [rev.revision for rev in script_dir.walk_revisions()]
        except Exception as e:
            self.logger.error(f"Failed to get available revisions: {e}")
            return []

    async def get_pending_revisions(self) -> List[str]:
        """Get list of pending revisions."""
        current_rev = await self.get_current_revision()
        available_revs = await self.get_available_revisions()

        if current_rev is None:
            return available_revs

        # Find revisions after current
        current_index = (
            available_revs.index(current_rev) if current_rev in available_revs else -1
        )
        return available_revs[:current_index] if current_index > 0 else []

    async def upgrade_to_revision(self, revision: str = "head") -> bool:
        """
        Upgrade database to a specific revision.

        Args:
            revision: Target revision (default: "head")

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Upgrading database to revision: {revision}")

            # Run Alembic upgrade
            command.upgrade(self.alembic_cfg, revision)

            self.logger.info("Database upgrade completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database upgrade failed: {e}")
            raise DatabaseError(f"Database upgrade failed: {e}")

    async def downgrade_to_revision(self, revision: str) -> bool:
        """
        Downgrade database to a specific revision.

        Args:
            revision: Target revision

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Downgrading database to revision: {revision}")

            # Run Alembic downgrade
            command.downgrade(self.alembic_cfg, revision)

            self.logger.info("Database downgrade completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database downgrade failed: {e}")
            raise DatabaseError(f"Database downgrade failed: {e}")

    async def create_migration(
        self, message: str, autogenerate: bool = True
    ) -> Optional[str]:
        """
        Create a new migration.

        Args:
            message: Migration message
            autogenerate: Whether to autogenerate migration from model changes

        Returns:
            Migration revision ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Creating migration: {message}")

            if autogenerate:
                # Autogenerate migration
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
            else:
                # Create empty migration
                command.revision(self.alembic_cfg, message=message)

            # Get the latest revision
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            latest_rev = script_dir.get_current_head()

            self.logger.info(f"Migration created: {latest_rev}")
            return latest_rev

        except Exception as e:
            self.logger.error(f"Migration creation failed: {e}")
            raise DatabaseError(f"Migration creation failed: {e}")

    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            history = []

            for rev in script_dir.walk_revisions():
                history.append(
                    {
                        "revision": rev.revision,
                        "down_revision": rev.down_revision,
                        "branch_labels": rev.branch_labels,
                        "depends_on": rev.depends_on,
                        "doc": rev.doc,
                        "module_path": str(rev.module_path)
                        if rev.module_path
                        else None,
                    }
                )

            return history

        except Exception as e:
            self.logger.error(f"Failed to get migration history: {e}")
            return []

    async def check_migration_status(self) -> Dict[str, Any]:
        """Check migration status."""
        try:
            current_rev = await self.get_current_revision()
            available_revs = await self.get_available_revisions()
            pending_revs = await self.get_pending_revisions()

            return {
                "current_revision": current_rev,
                "available_revisions": available_revs,
                "pending_revisions": pending_revs,
                "is_up_to_date": len(pending_revs) == 0,
                "total_revisions": len(available_revs),
            }

        except Exception as e:
            self.logger.error(f"Failed to check migration status: {e}")
            return {"error": str(e), "is_up_to_date": False}

    async def initialize_database(self) -> bool:
        """Initialize database with initial migration."""
        try:
            current_rev = await self.get_current_revision()

            if current_rev is None:
                self.logger.info("Initializing database with initial migration")
                return await self.upgrade_to_revision("head")
            else:
                self.logger.info(
                    f"Database already initialized at revision: {current_rev}"
                )
                return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    async def reset_database(self) -> bool:
        """Reset database (WARNING: This will delete all data)."""
        try:
            self.logger.warning("Resetting database - all data will be lost!")

            # Downgrade to base
            command.downgrade(self.alembic_cfg, "base")

            # Upgrade to head
            command.upgrade(self.alembic_cfg, "head")

            self.logger.info("Database reset completed")
            return True

        except Exception as e:
            self.logger.error(f"Database reset failed: {e}")
            raise DatabaseError(f"Database reset failed: {e}")


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


async def run_migrations(
    database_manager: DatabaseManager, target_revision: str = "head"
) -> bool:
    """
    Run database migrations.

    Args:
        database_manager: Database manager instance
        target_revision: Target revision (default: "head")

    Returns:
        True if successful, False otherwise
    """
    global _migration_manager

    if _migration_manager is None:
        _migration_manager = MigrationManager(database_manager)

    return await _migration_manager.upgrade_to_revision(target_revision)


async def create_migration(
    database_manager: DatabaseManager, message: str, autogenerate: bool = True
) -> Optional[str]:
    """
    Create a new migration.

    Args:
        database_manager: Database manager instance
        message: Migration message
        autogenerate: Whether to autogenerate migration from model changes

    Returns:
        Migration revision ID if successful, None otherwise
    """
    global _migration_manager

    if _migration_manager is None:
        _migration_manager = MigrationManager(database_manager)

    return await _migration_manager.create_migration(message, autogenerate)


async def rollback_migration(
    database_manager: DatabaseManager, target_revision: str
) -> bool:
    """
    Rollback database to a specific revision.

    Args:
        database_manager: Database manager instance
        target_revision: Target revision

    Returns:
        True if successful, False otherwise
    """
    global _migration_manager

    if _migration_manager is None:
        _migration_manager = MigrationManager(database_manager)

    return await _migration_manager.downgrade_to_revision(target_revision)


def get_migration_manager() -> Optional[MigrationManager]:
    """Get the global migration manager instance."""
    return _migration_manager
