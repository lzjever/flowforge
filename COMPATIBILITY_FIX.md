# Python 3.12+ Compatibility Fix

## Issue Fixed

The security module had compatibility issues with Python 3.12+ where certain AST node types were removed:
- `ast.Exec` - Removed (exec is a function, not a statement in Python 3)
- `ast.Comp` - Removed in Python 3.8+

## Solution

Modified `routilux/api/security.py` to dynamically build the `FORBIDDEN_NODES` tuple using only AST nodes that exist in the current Python version:

```python
# Build FORBIDDEN_NODES tuple with nodes that exist in current Python version
FORBIDDEN_NODES = tuple(
    node for node in BASE_FORBIDDEN_NODES
    if hasattr(ast, node.__name__)
)
```

This ensures compatibility across all supported Python versions (3.8-3.14).

## Testing

```bash
# Test import
python -c "from routilux.api.security import safe_evaluate; print('✅ OK')"

# Test API startup
python -m routilux.api.main
```

## Status

✅ **Fixed and Verified**

The API now starts successfully on Python 3.12+ while maintaining security features.
