# Core Tests

This directory contains tests for Routilux core functionality.

## Test Structure

- **Core Tests**: Tests in `tests/` directory test the core Routilux framework
  - Routine, Slot, Event, Connection classes
  - Flow orchestration and execution
  - Serialization and persistence
  - Error handling
  - Job state management
  - Execution tracking
  - Aggregation patterns
  - API endpoints (if API dependencies are installed)

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_routine.py

# Run with coverage
pytest tests/ --cov=routilux --cov-report=html
```

### Run Integration Tests

```bash
# Integration tests require external services
pytest tests/ -m integration
```

## Test Organization

All tests use **pytest** framework. The `pytest.ini` configuration:
- Configures coverage reporting
- Sets up test markers (unit, integration, slow, persistence, resume)
- Excludes integration tests by default
