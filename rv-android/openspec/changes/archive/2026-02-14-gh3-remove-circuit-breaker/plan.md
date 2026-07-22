# Remove Circuit Breaker from rv-android-core

**GitHub Issue**: #3
**Track**: Quick Path
**Status**: Complete

## Context

The `CommandCircuitBreaker` class (~200 lines) implements a circuit breaker pattern with open/closed/half-open states, failure thresholds, and recovery timers. It is never instantiated in any production code path. The associated `CircuitBreakerOpenError` exception and ErrorHandler registration are also dead code.

## File Inventory

### Deleted
- `commands/circuit_breaker.py` → backed up to `backup/circuit_breaker/`
- `tests/commands/test_circuit_breaker.py` → backed up to `backup/circuit_breaker/`

### Modified (source)
- `tools/abstract_tool.py` — removed import, init, and all circuit breaker logic from `_execute_and_check_command()`
- `util/error/exceptions.py` — removed `CircuitBreakerOpenError` class
- `util/error/error_handler.py` — removed import, handler registration, and handler method

### Modified (tests)
- `tests/tools/test_abstract_tool.py` — removed 2 test methods, simplified 4 others
- `tests/util/error/test_error_handler_comprehensive.py` — removed 1 test, updated handler count
- `tests/util/error/test_error_handler.py` — removed commented-out circuit breaker code, updated handler count

## Acceptance Criteria

- [x] `grep -r "CircuitBreaker" modules/**/*.py` returns zero results
- [x] `grep -r "circuit_breaker" modules/**/*.py` returns zero results
- [x] All affected tests pass (284 passed)
- [x] Files backed up to `backup/circuit_breaker/`
