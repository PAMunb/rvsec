# Coverage Strategy

Strategy for achieving meaningful test coverage without over-testing. Use to decide what to test and what to skip.

## How to Use

1. Identify the module type (core logic, integration, CLI)
2. Apply the must-test / should-test / skip criteria below
3. Select coverage targets from the module type table
4. Use the test pyramid to balance unit vs integration vs E2E tests

---

## Coverage Hierarchy

Test coverage types, ordered by value (diminishing returns as you go down):

| Level | What It Measures | Value | Effort |
|-------|-----------------|-------|--------|
| Function coverage | Every function called at least once | High | Low |
| Branch coverage | Every if/else branch taken | High | Medium |
| Line coverage | Every line executed | Medium | Medium |
| Path coverage | Every combination of branches | Low | Very High |

**Recommendation**: Target function + branch coverage. Line coverage follows naturally. Path coverage is rarely worth the effort.

## What to Test

### Must-Test (Always)

| Category | Why | Example |
|----------|-----|---------|
| Public API | Contract with callers | `RVAgent.run()`, `Platform.execute()` |
| Error handling paths | Silent failures are the worst bugs | `try/except` branches, error returns |
| State transitions | State bugs are hard to diagnose | Agent state machine, executor lifecycle |
| Boundary conditions | Bugs cluster at boundaries | Empty lists, max values, None inputs |
| Configuration parsing | Bad config = silent failure | Pydantic model validation, env var parsing |

### Should-Test (When Feasible)

| Category | Why | Example |
|----------|-----|---------|
| Complex internal logic | High cyclomatic complexity = high bug risk | Routing algorithms, priority calculations |
| Data transformations | Input→output mapping must be correct | JSON parsing, coordinate normalization |
| Integration points | Mismatched interfaces are common | Module-to-module calls, API clients |

### Skip (Don't Test)

| Category | Why | Example |
|----------|-----|---------|
| Trivial getters/setters | Zero logic, zero risk | `@property` that returns `self._field` |
| Framework-generated code | Tested by the framework | Pydantic `__init__`, dataclass fields |
| Third-party wrappers | Test the usage, not the library | Thin wrappers around `subprocess.run` |
| Constants | Can't break | `TIMEOUT = 300` |
| Type-only modules | No logic to test | Module with only type aliases or protocols |

## Coverage Targets by Module Type

| Module Type | Function Coverage | Branch Coverage | Examples |
|------------|------------------|----------------|----------|
| Core logic | 90%+ | 80%+ | rv-android-core domain models, rv-agent strategy |
| Service layer | 80%+ | 70%+ | rv-platform execution, rv-coverage tracking |
| Integration glue | 70%+ | 60%+ | rv-experiment orchestration, rv-instrumentation |
| CLI / entry points | Smoke tests | N/A | `__main__.py`, CLI argument parsing |
| Configuration | 90%+ (validation) | 80%+ | Pydantic models, config loading |

## Test Pyramid

```
        /\
       /  \       E2E / System tests (few)
      /    \      - Full workflow: experiment → platform → agent → results
     /------\
    /        \    Integration tests (moderate)
   /          \   - Module-to-module: platform calls tool factory
  /            \  - External: LLM client with mock server
 /--------------\
/                \ Unit tests (many)
/                  \ - Function-level: parse_action(), normalize_coords()
/____________________\ - Class-level: RVAgentStrategy with mock state
```

**Ratios**: ~70% unit, ~20% integration, ~10% E2E/system.

## rv-android Test Categories

| Category | Directory | Purpose | Speed |
|----------|-----------|---------|-------|
| unit | `tests/unit/` | Isolated function/class tests, no external deps | Fast (< 1s each) |
| integration | `tests/integration/` | Module interaction tests | Medium (< 10s each) |
| smoke | `tests/smoke/` | Minimal end-to-end sanity checks | Medium |
| online | `tests/online/` | Requires running LLM server or emulator | Slow |
| performance | `tests/performance/` | Timing and resource usage benchmarks | Slow |
| regression | `tests/regression/` | Specific bug reproduction tests | Fast |
| system | `tests/system/` | Full pipeline tests | Very slow |

## Mock Guidelines

### When to Mock

| Scenario | Mock Strategy |
|----------|--------------|
| External API calls | Mock the HTTP client or use `responses` library |
| File I/O | Use `tmp_path` fixture or mock `open()` |
| Network calls | Mock at the client level |
| Time-dependent code | Mock `time.time()` or `datetime.now()` |
| Environment variables | Use `monkeypatch.setenv()` |
| Subprocess calls | Mock `subprocess.run()` |

### When NOT to Mock

| Scenario | Why Not |
|----------|---------|
| Domain logic | Mocking hides bugs in the logic you're testing |
| Pure functions | No external deps = no mocks needed |
| Data transformations | Test real input → real output |
| Pydantic validation | Test with real invalid data, not mock validators |

### Mock Depth Rule

Mock at the boundary closest to your code. If testing `RVAgent.run()`:
- Mock the LLM client (external boundary) — correct
- Mock internal agent methods — usually wrong (tests implementation, not behavior)
