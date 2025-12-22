"""
Test Configuration
==================
Pytest fixtures for Token Trackr tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import get_session
from backend.main import app
from backend.models.base import Base

# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(test_session) -> Generator[TestClient, None, None]:
    """Create test client with database session override."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_usage_event() -> dict:
    """Sample usage event for testing."""
    return {
        "tenant_id": "test-tenant",
        "provider": "bedrock",
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "timestamp": datetime.utcnow().isoformat(),
        "latency_ms": 1500,
        "host": {
            "hostname": "test-host",
            "cloud_provider": "aws",
            "instance_id": "i-1234567890",
            "k8s": {
                "pod": "test-pod",
                "namespace": "test-ns",
            },
        },
    }


@pytest.fixture
def sample_batch_events() -> list[dict]:
    """Sample batch of usage events for testing."""
    return [
        {
            "tenant_id": "test-tenant",
            "provider": "bedrock",
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "tenant_id": "test-tenant",
            "provider": "azure_openai",
            "model": "gpt-4o",
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "tenant_id": "test-tenant",
            "provider": "gemini",
            "model": "gemini-1.5-pro",
            "prompt_tokens": 150,
            "completion_tokens": 75,
            "timestamp": datetime.utcnow().isoformat(),
        },
    ]
