from logging.config import fileConfig
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from asyncio import run as asyncio_run

from alembic import context

# Import Base from our models
from botspool_shared_utils.database.models import Base

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata


def get_database_url():
    """Get database URL from environment or use default."""
    # Override with environment variable if set
    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url")
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with a connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async engine."""
    # Get database URL
    url = get_database_url()
    
    # Create async engine
    engine = create_async_engine(
        url,
        poolclass=pool.NullPool,
        echo=False
    )
    
    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)
    
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run async migrations
    asyncio_run(run_migrations_online())
