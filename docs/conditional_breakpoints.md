# Conditional Breakpoints

## Overview

Breakpoints can be configured with conditions to only pause execution when specific criteria are met. This allows you to debug specific scenarios without stopping at every breakpoint hit.

## Creating Conditional Breakpoints

### HTTP API

```bash
POST /api/jobs/{job_id}/breakpoints
Content-Type: application/json

{
  "type": "routine",
  "routine_id": "process_item",
  "slot_name": "input",
  "condition": "item_count > 100"
}
```

### Response

```json
{
  "breakpoint_id": "bp_abc123",
  "type": "routine",
  "routine_id": "process_item",
  "slot_name": "input",
  "condition": "item_count > 100",
  "created_at": "2025-01-15T10:30:00Z"
}
```

## Supported Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal to | `status == 'error'` |
| `!=` | Not equal to | `status != 'success'` |
| `<` | Less than | `count < 10` |
| `>` | Greater than | `count > 100` |
| `<=` | Less than or equal to | `count <= 100` |
| `>=` | Greater than or equal to | `retry_count >= 3` |

### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `and` | Logical AND | `status == 'error' and retry_count >= 3` |
| `or` | Logical OR | `status == 'error' or status == 'timeout'` |
| `not` | Logical NOT | `not is_active` |

### Membership Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `in` | Member of | `user_id in blocked_users` |
| `not in` | Not member of | `status not in ['completed', 'failed']` |

### Identity Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `is` | Identity | `result is None` |
| `is not` | Not identity | `result is not None` |

## Usage Examples

### Basic Conditions

Pause when status equals 'error':
```python
condition = "status == 'error'"
```

Pause when retry count is 3 or more:
```python
condition = "retry_count >= 3"
```

### Complex Conditions

Pause when multiple conditions are met:
```python
condition = "status == 'error' and retry_count >= 3"
```

Pause when any of multiple conditions are met:
```python
condition = "status == 'error' or status == 'timeout'"
```

Pause when user is in blocked list:
```python
condition = "user_id in blocked_users"
```

Pause when result is None:
```python
condition = "result is None"
```

### Using Variables

Conditions have access to all variables in the routine's context:

```python
# Variable from routine state
condition = "self.error_count > 10"

# Local variable
condition = "item_value > threshold"

# Nested attribute access
condition = "user.profile.age >= 18"
```

## Conditional Expression Evaluation

Conditions are evaluated using Python's expression syntax. The following operations are supported:

- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`
- Identity: `is`, `is not`
- Bitwise: `&`, `|`, `^`, `~`, `<<`, `>>`

## Best Practices

### 1. Keep Conditions Simple

Complex conditions are harder to debug and may impact performance:

**Good:**
```python
condition = "count > 100"
```

**Avoid:**
```python
condition = "(count > 100 and status == 'active') or (count > 50 and status == 'priority')"
```

### 2. Use Parentheses for Clarity

When using complex logical expressions, use parentheses to make the logic clear:

```python
condition = "(status == 'error' and retry_count >= 3) or (status == 'timeout' and timeout_count >= 2)"
```

### 3. Test Your Conditions

Before setting a breakpoint with a condition, test the condition in a Python REPL to ensure it's valid:

```python
# Test in REPL
>>> count = 150
>>> count > 100
True
>>> status = 'error'
>>> status == 'error' and count > 100
True
```

### 4. Avoid Side Effects

Conditions should not modify state. Only use comparison and logical operations:

**Good:**
```python
condition = "self.counter >= 100"
```

**Avoid:**
```python
condition = "self.counter += 1"  # This will fail
```

### 5. Use String Quotes Properly

When comparing strings, use quotes inside the condition string:

```python
condition = "status == 'error'"
condition = 'name == "John"'
```

## Debugging Conditional Breakpoints

If a conditional breakpoint isn't hitting as expected:

1. **Check variable names**: Ensure variables exist in the routine context
2. **Test the condition**: Evaluate the condition manually with actual variable values
3. **Check operator precedence**: Use parentheses to ensure correct evaluation order
4. **Review syntax**: Ensure all strings are properly quoted and parentheses are balanced

## Example: Full Debugging Session

```python
# Create a breakpoint with condition
POST /api/jobs/job_123/breakpoints
{
  "type": "routine",
  "routine_id": "process_payment",
  "slot_name": "input",
  "condition": "amount > 1000 and currency == 'USD'"
}

# Resume job execution
POST /api/jobs/job_123/debug/resume

# When breakpoint hits, check variables
GET /api/jobs/job_123/debug/variables?routine_id=process_payment

# Evaluate additional expressions
POST /api/jobs/job_123/debug/evaluate
{
  "expression": "amount * exchange_rate",
  "routine_id": "process_payment"
}
```

## Performance Considerations

Conditional breakpoints are evaluated each time the breakpoint location is reached. For performance-critical code:

1. **Keep conditions simple**: Complex conditions take longer to evaluate
2. **Use early exit**: Structure conditions to fail fast (e.g., `count > 100 and expensive_check()`)
3. **Consider hot paths**: Breakpoints in tight loops with conditions will still impact performance

## Troubleshooting

### Breakpoint Not Hitting

If your conditional breakpoint isn't hitting:

1. Check that the condition evaluates to `True` when expected
2. Verify variable names and spelling
3. Ensure the breakpoint location is actually being executed
4. Check for syntax errors in the condition

### Syntax Errors

If you get a syntax error:

1. Check that strings are properly quoted
2. Ensure parentheses are balanced
3. Verify operator usage (e.g., `==` not `=` for comparison)
4. Test the condition in a Python REPL

## Related Features

- [Expression Evaluation API](expression_evaluation.md) - Evaluate expressions at breakpoints
- [Debug Session Management](debug_sessions.md) - Manage debug sessions
- [Variables Inspection](variables.md) - Inspect and modify variables

## API Reference

See the [API Documentation](../api_reference.md) for complete endpoint details.
