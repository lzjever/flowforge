# TODO Tracking - P2-2 from A04 Code Review

## Date
2026-02-08

## Task
Track TODO markers and address or create GitHub issues.

## Findings

### Search Results
Searched entire codebase for TODO/FIXME/XXX/HACK markers:
- Pattern: `TODO`, `FIXME`, `XXX`, `HACK` (case-insensitive)
- File types: `*.py`
- Locations searched: All Python files in routilux/

### Results
**No TODO markers found in production code.**

The only matches found were in documentation configuration:
- `docs/source/conf.py:41` - `'sphinx.ext.todo'` (Sphinx extension name, legitimate)
- `docs/source/conf.py:132` - `todo_include_todos = True` (Sphinx config, legitimate)

### A04 Review Reference
The A04 code review (2026-02-08) mentioned a TODO at `server/main.py:51`.
Upon investigation:
- Line 51 currently contains: `_ensure_event_publisher()` (event publisher initialization)
- Line 53 contains the environment variable check: `if os.getenv("ROUTILUX_DEBUGGER_MODE") == "true":`
- No TODO marker exists at this location
- The TODO was likely removed during recent refactoring (commit `5c3e2f9` - "refactor: remove legacy Flow/JobState architecture")

## Conclusion

The codebase is **clean of TODO markers**. The recommendation from A04 to "establish GitHub Issues/Projects tracking" is noted, but there are currently no inline TODO markers to migrate.

## Best Practices Going Forward

1. **Prefer GitHub Issues over inline TODOs**: When work is needed, create a GitHub issue instead of adding inline TODO comments
2. **Reference issues in code**: If code needs temporary workarounds, reference the issue number:
   ```python
   # Workaround for https://github.com/owner/repo/issues/123
   # Remove when fix is deployed
   ```
3. **Regular audits**: The codebase should be periodically audited for new TODO markers

## Related Issues
- A04 Code Review: `docs/reviews/A04-code-review.md` (line 536-540)
