# File Analysis Dimensions

Structured dimensions for single-file analysis. Ensures comprehensive coverage of all relevant aspects.

## How to Use

1. Analyze the target file through each of the 8 dimensions below, in priority order
2. Produce at least one finding per dimension
3. If a dimension is not applicable (e.g., no error handling in a pure data module), note "N/A" with reason
4. Summarize with a health score and recommended actions

---

## Analysis Priority Order

Analyze in this order — earlier dimensions provide context for later ones:

1. Structure → 2. Responsibilities → 3. Dependencies → 4. Complexity → 5. Error Handling → 6. API Surface → 7. Configuration → 8. Testing

---

## Dimension 1: Structure

What the file contains and how it is organized.

**Analyze**:
- Module-level code (imports, constants, module docstring)
- Classes: count, hierarchy, inner classes
- Functions: count, module-level vs class methods
- Import organization: stdlib → third-party → internal (PEP 8 order)
- File length (LOC)

**Report**: File type (pure module, class definition, script, config), organization quality, structural issues.

## Dimension 2: Responsibilities

What the file is responsible for — Single Responsibility assessment.

**Analyze**:
- Can you describe the file's purpose in one sentence?
- How many distinct responsibilities does it handle?
- Are there groups of methods/functions that serve different purposes?
- Cohesion: do all parts of the file work toward the same goal?

**Report**: Responsibility count, cohesion assessment (high/medium/low), SRP violations if any.

**Threshold**: A file should have 1–2 responsibilities. 3+ indicates splitting opportunity.

## Dimension 3: Dependencies

What the file imports and what depends on it.

**Analyze**:
- Standard library imports (count and purpose)
- Third-party imports (each is a coupling point)
- Internal imports (which rv-android modules/files)
- Circular dependency risk (mutual imports)
- Import-time side effects

**Report**: Dependency count by category, coupling assessment, any problematic imports.

**Threshold**: > 10 internal imports = high coupling. > 5 third-party imports = broad external surface.

## Dimension 4: Complexity

Quantitative complexity assessment at the function level.

**Analyze**:
- Cyclomatic complexity per function (see complexity-thresholds.md)
- Cognitive complexity per function
- Maximum nesting depth
- Longest function (LOC)
- Number of parameters per function

**Report**: Per-function metrics table, aggregate file complexity, functions exceeding thresholds.

## Dimension 5: Error Handling

How the file handles errors and exceptional conditions.

**Analyze**:
- try/except blocks: what they catch, how specific
- Bare `except:` or `except Exception` (too broad)
- Error propagation: does it re-raise, wrap, or swallow?
- Cleanup patterns: `finally`, context managers (`with`)
- Error messages: informative or generic?

**Report**: Error handling pattern quality, specific issues found.

**Red flags**: Bare except, `except: pass`, generic error messages, no cleanup in resource-managing code.

## Dimension 6: API Surface

The public interface the file exposes.

**Analyze**:
- Public functions/methods (no leading underscore)
- Public classes
- Module-level constants
- `__all__` definition (explicit API)
- Docstrings on public symbols
- Type annotations on public signatures

**Report**: API breadth (number of public symbols), documentation coverage, type annotation coverage.

**Threshold**: > 15 public symbols = broad API, consider splitting. 0% docstrings on public API = documentation debt.

## Dimension 7: Configuration

Configurable behavior and magic values.

**Analyze**:
- Constants defined in the file
- Magic numbers/strings (unlabeled literal values)
- Environment variable reads (`os.environ`, `os.getenv`)
- Configuration class attributes
- Default values that might need to change

**Report**: Magic value count, configuration surface, externalization opportunities.

**Threshold**: > 3 magic values = extract to constants. Any `os.environ.get` without default = fragile.

## Dimension 8: Testing

How testable the file is and what testing strategy it needs.

**Analyze**:
- Pure functions (easy to test) vs side-effect functions (need mocks)
- External dependencies that require mocking (network, filesystem, database)
- State management (stateless functions vs stateful classes)
- Entry points for integration testing
- Existing test coverage (if test files exist)

**Report**: Testability assessment (high/medium/low), recommended test approach, mock requirements.

---

## Health Score

After analyzing all 8 dimensions, assign an overall health score:

| Score | Criteria |
|-------|----------|
| A (Healthy) | 0–1 issues, all dimensions clean, well-structured |
| B (Good) | 2–3 minor issues, no critical problems |
| C (Needs Attention) | 4–5 issues or 1 critical (SRP violation, high complexity) |
| D (Needs Refactoring) | 6+ issues or 2+ critical problems |
| F (Critical) | Fundamental structural problems, must refactor before extending |
