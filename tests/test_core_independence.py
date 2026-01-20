"""Test that core module can be used without monitoring module."""

from pathlib import Path


def test_core_import_without_monitoring():
    """Test that core can be imported even if monitoring is not available."""
    # This test verifies that core module has no hard dependencies on monitoring
    # at import time

    # Import core - should succeed
    from routilux.core import Runtime
    from routilux.core.hooks import NullExecutionHooks

    # Verify we can use core without monitoring
    runtime = Runtime(thread_pool_size=1)
    assert runtime is not None

    # Verify hooks work without monitoring
    hooks = NullExecutionHooks()
    should_enqueue, reason = hooks.on_slot_before_enqueue(
        slot=None,
        routine_id="test",
        job_context=None,
        data={},
        flow_id="test",
    )
    assert should_enqueue is True
    assert reason is None


def test_runtime_no_monitoring_imports():
    """Test that Runtime module does not import monitoring at module level."""
    import routilux.core.runtime as runtime_module

    # Check that monitoring is not in the module's globals at import time
    # (it may be imported lazily in functions, which is OK)
    module_source = Path(runtime_module.__file__).read_text()

    # Should not have top-level imports from monitoring
    lines = module_source.split("\n")
    top_level_imports = [
        line.strip()
        for line in lines
        if line.strip().startswith("from routilux.monitoring")
        or line.strip().startswith("import routilux.monitoring")
    ]

    # All monitoring imports should be inside functions (lazy imports)
    # or in TYPE_CHECKING blocks
    for imp in top_level_imports:
        # Check if it's in a function or TYPE_CHECKING
        # This is a simple check - in practice, we rely on the fact that
        # we removed the imports in Step 3.1
        assert "TYPE_CHECKING" in imp or imp == "", (
            f"Found top-level monitoring import: {imp}. Should be lazy import inside function."
        )
