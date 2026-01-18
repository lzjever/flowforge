"""Pytest configuration and fixtures for Routilux tests."""

import pytest

from fastapi.testclient import TestClient

from routilux.core import (
    Flow,
    Runtime,
    get_flow_registry,
    get_worker_manager,
    reset_worker_manager,
)
from routilux.server.dependencies import reset_storage
from routilux.server.main import app


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "userstory: User story integration tests (multi-API workflows that simulate real user scenarios)",
    )


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    # Reset worker manager
    reset_worker_manager()

    # Clear flow registry
    registry = get_flow_registry()
    registry.clear()

    # Reset storage
    reset_storage()

    yield

    # Cleanup after test
    reset_worker_manager()
    registry.clear()
    reset_storage()


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


# ==============================================================================
# User Story Test Fixtures
# ==============================================================================


@pytest.fixture
def api_client():
    """Create a test API client for user story tests."""
    return TestClient(app)


@pytest.fixture
def registered_pipeline_flow(api_client):
    """Create and register a simple pipeline flow for testing.

    Creates a flow with: data_source -> data_transformer -> data_sink
    """
    from tests.helpers.flow_builder import FlowBuilder

    builder = FlowBuilder(api_client)
    builder.build_pipeline()
    flow_id = builder.flow_id

    yield builder

    # Cleanup
    try:
        builder.delete()
    except Exception:
        pass


@pytest.fixture
def registered_branching_flow(api_client):
    """Create and register a branching flow for testing.

    Creates a flow with: data_source -> (data_transformer1, data_transformer2) -> data_sink
    """
    from tests.helpers.flow_builder import FlowBuilder

    builder = FlowBuilder(api_client)
    builder.build_branching_flow()
    flow_id = builder.flow_id

    yield builder

    # Cleanup
    try:
        builder.delete()
    except Exception:
        pass


@pytest.fixture
def flow_builder(api_client):
    """Create a FlowBuilder instance for dynamic flow construction."""
    from tests.helpers.flow_builder import FlowBuilder

    return FlowBuilder(api_client)


@pytest.fixture
def job_monitor(api_client):
    """Create a JobMonitor instance for monitoring job execution."""
    from tests.helpers.job_monitor import JobMonitor

    return JobMonitor(api_client)


@pytest.fixture
def debug_client(api_client):
    """Create a DebugClient instance for debugging jobs."""
    from tests.helpers.debug_client import DebugClient

    return DebugClient(api_client)
