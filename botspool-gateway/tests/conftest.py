"""
Pytest configuration and fixtures for BotsPool Gateway tests
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app
from src.config import Settings, get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """
    Get test settings.

    Override with test-specific configuration.
    """
    settings = Settings(
        environment="testing",
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",  # Use different DB for tests
    )
    return settings


@pytest.fixture
def client() -> Generator:
    """
    Get test client for synchronous tests.

    Yields:
        TestClient: FastAPI test client
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """
    Get async test client for async tests.

    Yields:
        AsyncClient: Async HTTP client
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
