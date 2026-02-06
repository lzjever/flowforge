# I04@V01 Production Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete production release polish by fixing 3 minor issues (import sorting, PyYAML type stubs, and strict type checking) identified in v01-checklist.

**Architecture:** Systematic fixes across code quality (ruff formatting), dependencies (types-PyYAML), and type safety (mypy strict mode).

**Tech Stack:** Python 3.8+, mypy, ruff, pytest, uv

---

## Overview

This plan addresses 3 issues from v01-checklist:

| Task | Issue | Effort |
|------|-------|--------|
| 1 | Import sorting (L-1) | 5 min |
| 2 | PyYAML type stubs (L-2) | 5 min |
| 3 | Strict type checking (L-3) | 2-3 hours |

**Total Estimated Time:** ~3 hours

---

# Task 1: Fix Import Sorting (L-1)

**Issue:** Import block in `routilux/__init__.py:8` is unsorted

**Files:**
- Modify: `routilux/__init__.py`

## Step 1: Run ruff format to fix imports

Run: `uv run ruff format routilux/__init__.py`

Expected: File is reformatted, import block becomes sorted

## Step 2: Verify with ruff check

Run: `uv run ruff check routilux/__init__.py --select I`

Expected: No errors reported

## Step 3: Run tests to ensure no breakage

Run: `uv run pytest tests/ -v --tb=short 2>&1 | tail -5`

Expected: All tests pass (407 passed)

## Step 4: Commit

```bash
git add routilux/__init__.py
git commit -m "fix(L-1): fix import sorting in __init__.py

Apply ruff format to sort import blocks.

Fixes: L-1 from v01-checklist"
```

---

# Task 2: Add PyYAML Type Stubs (L-2)

**Issue:** mypy reports "Library stubs not installed for yaml" at `routilux/builtin_routines/text_processing/result_extractor.py:125`

**Files:**
- Modify: `pyproject.toml`

## Step 1: Add types-PyYAML to dev dependencies

Edit `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=0.991",
    "build>=0.10.0",
    "pip-audit>=2.6.0",
    "bandit>=1.7.5",
    "safety>=2.3.0",
    "pytest-benchmark>=4.0.0",
    "types-PyYAML>=6.0.0",  # Add this line
]
```

## Step 2: Install the new dependency

Run: `uv sync --group dev`

Expected: Package installs successfully

## Step 3: Verify mypy no longer complains about yaml

Run: `uv run mypy routilux/builtin_routines/text_processing/result_extractor.py --show-error-codes`

Expected: No "import-untyped" error for yaml

## Step 4: Run tests to ensure no breakage

Run: `uv run pytest tests/ -v --tb=short 2>&1 | tail -5`

Expected: All tests pass (407 passed)

## Step 5: Commit

```bash
git add pyproject.toml
git commit -m "fix(L-2): add types-PyYAML to dev dependencies

Adds type stubs for PyYAML to eliminate mypy import-untyped error.

Fixes: L-2 from v01-checklist"
```

---

# Task 3: Enable Strict Type Checking (L-3)

**Issue:** 9 functions lack return type annotations, preventing strict mypy mode

**Files:**
- Modify: `pyproject.toml`
- Modify: `routilux/analysis/analyzers/routine.py`
- Modify: `routilux/routine_mixins.py`
- Modify: `routilux/routine.py`
- Modify: `routilux/builtin_routines/text_processing/result_extractor.py`

## Step 1: Add return type to RoutineAnalyzer.__init__

Edit `routilux/analysis/analyzers/routine.py:30-32`:

```python
def __init__(self) -> None:
    """Initialize the routine analyzer."""
    self.routines: list[dict[str, Any]] = []
```

## Step 2: Add return type to ConfigMixin.__init__

Edit `routilux/routine_mixins.py:45-51`:

```python
def __init__(self, *args: Any, **kwargs: Any) -> None:
    """Initialize ConfigMixin.

    Note: This is a mixin, called via super().__init__() from Routine.
    """
    super().__init__(*args, **kwargs)
    self._config: Dict[str, Any] = {}
```

## Step 3: Add return type to ExecutionMixin.__init__

Edit `routilux/routine_mixins.py:134-141`:

```python
def __init__(self, *args: Any, **kwargs: Any) -> None:
    """Initialize ExecutionMixin.

    Note: This is a mixin, called via super().__init__() from Routine.
    """
    super().__init__(*args, **kwargs)
    self._slots: Dict[str, Slot] = {}
    self._events: Dict[str, Event] = {}
```

## Step 4: Add return type to LifecycleMixin.__init__

Edit `routilux/routine_mixins.py:357-364`:

```python
def __init__(self, *args: Any, **kwargs: Any) -> None:
    """Initialize LifecycleMixin.

    Note: This is a mixin, called via super().__init__() from Routine.
    """
    super().__init__(*args, **kwargs)
    self._before_hooks: List[Callable[[], None]] = []
    self._after_hooks: List[Callable[[JobState], None]] = []
```

## Step 5: Add return type to Routine.__init__

Edit `routilux/routine.py:133-140`:

```python
def __init__(self, routine_id: str | None = None) -> None:
    """Initialize a Routine instance.

    Args:
        routine_id: Optional identifier for this routine. If not provided,
        uses the instance ID. For production use, provide a meaningful ID.
        Configuration values should be stored in self._config dictionary after object creation.
        See set_config() method for a convenient way to set configuration.
    """
    # Call all mixin __init__ methods (ConfigMixin, ExecutionMixin, LifecycleMixin)
    # and Serializable.__init__()
    super().__init__()
    self._id: str = hex(id(self))

    # Error handler for this routine (optional)
    # Priority: routine-level error handler > flow-level error handler > default (STOP)
    self._error_handler: ErrorHandler | None = None
```

## Step 6: Add return type to _register_builtin_extractors

Edit `routilux/builtin_routines/text_processing/result_extractor.py:106-109`:

```python
def _register_builtin_extractors(self) -> None:
    """Register built-in extractor functions."""
    if not hasattr(self, "_extractors"):
        self._extractors: dict[str, Callable] = {}
```

## Step 7: Run mypy to check remaining errors

Run: `uv run mypy routilux/ --show-error-codes 2>&1 | grep -v "annotation-unchecked" | head -20`

Expected: Only annotation-unchecked warnings remain (no actual errors)

## Step 8: Enable strict type checking in mypy config

Edit `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true      # Changed from false
check_untyped_defs = true         # Added
no_implicit_optional = true
ignore_missing_imports = true
```

## Step 9: Run mypy in strict mode

Run: `uv run mypy routilux/`

Expected: All checks pass (annotation-unchecked is expected, not an error)

## Step 10: Run full test suite

Run: `uv run pytest tests/ -v --tb=short 2>&1 | tail -5`

Expected: All tests pass (407 passed)

## Step 11: Run ruff linting

Run: `uv run ruff check routilux/`

Expected: No errors

## Step 12: Commit type annotations

```bash
git add routilux/analysis/analyzers/routine.py \
        routilux/routine_mixins.py \
        routilux/routine.py \
        routilux/builtin_routines/text_processing/result_extractor.py
git commit -m "fix(L-3): add return type annotations to all __init__ methods

Add -> None return type to:
- RoutineAnalyzer.__init__()
- ConfigMixin.__init__()
- ExecutionMixin.__init__()
- LifecycleMixin.__init__()
- Routine.__init__()
- ResultExtractor._register_builtin_extractors()

Enable disallow_untyped_defs=true in mypy config.

Fixes: L-3 from v01-checklist"
```

---

# Task 4: Final Verification and Documentation

## Step 1: Run full test suite with coverage

Run: `uv run pytest tests/ -v --cov=routilux --cov-report=term-missing 2>&1 | tail -30`

Expected: All 407 tests pass

## Step 2: Run mypy strict mode

Run: `uv run mypy routilux/`

Expected: No errors (annotation-unchecked notes are OK)

## Step 3: Run ruff linting

Run: `uv run ruff check routilux/`

Expected: No errors

## Step 4: Create implementation summary

Create `docs/verifications/v01-implementation-summary.md`:

```markdown
# I04@V01 Implementation Summary

**Date:** 2026-02-06
**Scope:** Production polish for v01 release

## Issues Resolved

| ID | Issue | Resolution |
|----|-------|------------|
| L-1 | Import sorting | ✅ Fixed with ruff format |
| L-2 | Missing PyYAML stubs | ✅ Added types-PyYAML>=6.0.0 |
| L-3 | Incomplete type annotations | ✅ Enabled strict mypy mode |

## Changes Made

### L-1: Import Sorting
- Ran `ruff format` on `routilux/__init__.py`
- Import blocks now properly sorted

### L-2: PyYAML Type Stubs
- Added `types-PyYAML>=6.0.0` to dev dependencies
- Eliminated mypy import-untyped error

### L-3: Strict Type Checking
- Added `-> None` return type to 6 `__init__` methods
- Added `-> None` to `_register_builtin_extractors()`
- Enabled `disallow_untyped_defs = true`
- Added `check_untyped_defs = true`

## Verification

All checks passing:
- ✅ 407 tests passing
- ✅ mypy strict mode passing
- ✅ ruff linting passing
- ✅ No blocking issues

## Release Status

**Ready for production release** ✅

All v01-checklist items resolved.
```

## Step 5: Update v01-checklist with implementation status

Edit `docs/verifications/v01-checklist.md`, add at end:

```markdown
## 8) I04@V01 实施状态 (2026-02-06)

### 已解决问题

| ID | 问题 | 状态 |
|----|------|------|
| L-1 | Import 排序问题 | ✅ 已修复 |
| L-2 | 缺少 PyYAML 类型存根 | ✅ 已添加 |
| L-3 | 类型注解不完整 | ✅ 已完成 |

### 实施总结

所有 v01 检查清单中的轻微问题已解决:
- L-1: 运行 ruff format 修复 import 排序
- L-2: 添加 types-PyYAML>=6.0.0 到 dev 依赖
- L-3: 启用严格类型检查 (disallow_untyped_defs=true)

**状态**: 准备发布 ✅
```

## Step 6: Final commit

```bash
git add docs/verifications/v01-implementation-summary.md \
        docs/verifications/v01-checklist.md
git commit -m "docs: document I04@V01 implementation completion

All v01-checklist issues resolved:
- L-1: Import sorting fixed
- L-2: PyYAML type stubs added
- L-3: Strict type checking enabled

Release status: Ready for production"
```

---

# Verification Commands

```bash
# All tests
uv run pytest tests/ -v

# Type checking
uv run mypy routilux/

# Linting
uv run ruff check routilux/

# Import check
uv run ruff check routilux/ --select I
```

---

## Summary

This plan completes the production polish for I04@V01:

| Task | Description | Time |
|------|-------------|------|
| Task 1 | Fix import sorting | 5 min |
| Task 2 | Add PyYAML stubs | 5 min |
| Task 3 | Enable strict type checking | 2-3 hours |
| Task 4 | Final verification | 15 min |

**Total:** ~3 hours

All changes are non-breaking and maintain backward compatibility.
