# Test Warnings Fix Summary

**Date**: 2025-01-XX  
**Issue**: `make test-userstory` had 3 warnings and 2 skipped tests  
**Status**: ✅ **FIXED**

---

## Issues Found and Fixed

### 1. PytestReturnNotNoneWarning (2 warnings) - ✅ FIXED

**Problem**: Test functions were returning values, which pytest warns against.

**Affected Tests**:
- `test_create_worker` - returned `data["worker_id"]`
- `test_submit_job` - returned `data["job_id"]`

**Fix**: Removed `return` statements from both test functions. Test functions should not return values; if values are needed by other tests, they should use fixtures or instance variables.

**Files Modified**:
- `tests/userstory/test_overseer_demo.py` (lines 304, 331)

---

### 2. DeprecationWarning (1 warning) - ✅ FIXED

**Problem**: Using deprecated `data=` parameter in httpx client.

**Affected Test**:
- `test_invalid_json` - used `data="invalid json"`

**Fix**: Changed to `content="invalid json"` as recommended by httpx.

**Files Modified**:
- `tests/userstory/test_overseer_demo.py` (line 1129)

---

### 3. Skipped Tests (2 tests) - ✅ ACCEPTABLE

These tests are **intentionally skipped** under certain conditions:

#### `test_debug_session_lifecycle`
**Location**: `tests/userstory/test_userstory_debugging.py:410`

**Skip Reason**: Debug store not available or job not found
```python
if "error" in session:
    pytest.skip(f"Debug session not available: {session.get('error', {}).get('message', 'Unknown')}")
```

**Status**: ✅ **ACCEPTABLE** - Conditional skip based on debug store availability. This is expected behavior when debug store is not configured.

#### `test_export_and_reimport_flow`
**Location**: `tests/userstory/test_userstory_flow_building.py:126`

**Skip Reason**: YAML module not available
```python
if yaml is None:
    pytest.skip("yaml module not available")
```

**Status**: ✅ **ACCEPTABLE** - YAML is an optional dependency. Test correctly skips when yaml module is not installed. This is expected behavior.

---

## Test Results After Fix

**Before**:
- 146 passed, 2 skipped, **3 warnings**

**After**:
- 146 passed, 2 skipped, **0 warnings** ✅

---

## Summary

### Fixed Issues
- ✅ Removed return statements from test functions (2 warnings fixed)
- ✅ Updated httpx usage to use `content=` instead of `data=` (1 warning fixed)

### Acceptable Skips
- ✅ `test_debug_session_lifecycle` - Conditionally skipped when debug store unavailable
- ✅ `test_export_and_reimport_flow` - Conditionally skipped when yaml module unavailable

**All warnings have been resolved. The 2 skipped tests are intentional and acceptable.**
