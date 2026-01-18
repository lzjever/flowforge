"""Pytest configuration and fixtures for Routilux tests."""

import pytest
from routilux.core import (
    Flow,
    FlowRegistry,
    Runtime,
    WorkerManager,
    get_flow_registry,
    get_worker_manager,
    reset_worker_manager,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    # Reset worker manager
    reset_worker_manager()
    
    # Note: FlowRegistry uses weak references, so flows will be cleaned up
    # automatically when they go out of scope. No need to manually unregister.
    
    yield
    
    # Cleanup after test
    reset_worker_manager()


@pytest.fixture
def runtime():
    """Create a Runtime instance for testing."""
    return Runtime(thread_pool_size=5)


@pytest.fixture
def empty_flow():
    """Create an empty Flow for testing."""
    return Flow()


@pytest.fixture
def worker_manager():
    """Get the global WorkerManager instance."""
    return get_worker_manager()
