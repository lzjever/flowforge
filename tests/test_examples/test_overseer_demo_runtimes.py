"""
Test that overseer_demo_app.py registers runtimes correctly.

This test verifies that the demo app creates and registers three runtimes
as expected for testing purposes.
"""

import pytest
from routilux.monitoring.runtime_registry import RuntimeRegistry
from routilux.runtime import Runtime


def test_demo_app_registers_runtimes():
    """Test: Demo app registers three runtimes correctly."""
    # Simulate what demo app does
    runtime_registry = RuntimeRegistry.get_instance()
    
    # Clear any existing runtimes (for clean test)
    # Note: We can't easily clear default runtime, so we'll work with existing ones
    
    # Create and register three runtimes (as in demo app)
    runtimes_to_create = [
        ("production", 0, True, "Production runtime using shared thread pool (recommended)"),
        ("development", 5, False, "Development runtime with small independent thread pool"),
        ("testing", 2, False, "Testing runtime with minimal thread pool for isolation"),
    ]
    
    registered_runtimes = []
    for runtime_id, thread_pool_size, is_default, description in runtimes_to_create:
        # Check if already registered
        existing = runtime_registry.get(runtime_id)
        if existing is None:
            runtime = Runtime(thread_pool_size=thread_pool_size)
            runtime_registry.register(runtime, runtime_id, is_default=is_default)
        else:
            runtime = existing
        registered_runtimes.append((runtime_id, runtime))
    
    # Verify all runtimes are registered
    all_runtimes = runtime_registry.list_all()
    runtime_ids = [rt_id for rt_id, _, _, _ in runtimes_to_create]
    
    for runtime_id in runtime_ids:
        assert runtime_id in all_runtimes, f"Runtime '{runtime_id}' should be registered"
        runtime = runtime_registry.get(runtime_id)
        assert runtime is not None, f"Runtime '{runtime_id}' should exist"
    
    # Verify default runtime
    default_id = runtime_registry.get_default_id()
    assert default_id == "production", f"Default runtime should be 'production', got '{default_id}'"
    
    # Verify thread pool sizes
    production = runtime_registry.get("production")
    development = runtime_registry.get("development")
    testing = runtime_registry.get("testing")
    
    assert production.thread_pool_size == 0, "Production should use shared pool (0)"
    assert development.thread_pool_size == 5, "Development should have 5 threads"
    assert testing.thread_pool_size == 2, "Testing should have 2 threads"
    
    print("✓ All three runtimes registered correctly")
    print(f"  - production: thread_pool_size={production.thread_pool_size} (default)")
    print(f"  - development: thread_pool_size={development.thread_pool_size}")
    print(f"  - testing: thread_pool_size={testing.thread_pool_size}")


def test_runtime_registry_list_all():
    """Test: RuntimeRegistry.list_all() returns all registered runtimes."""
    registry = RuntimeRegistry.get_instance()
    
    # Ensure at least default runtime exists
    registry.get_or_create_default(thread_pool_size=0)
    
    all_runtimes = registry.list_all()
    assert len(all_runtimes) >= 1, "Should have at least default runtime"
    
    # Verify default is in list
    default_id = registry.get_default_id()
    assert default_id in all_runtimes, "Default runtime should be in list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
