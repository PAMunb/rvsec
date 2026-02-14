# Plan: Replace String-Based Component Lookup with Type-Based

**GitHub Issue**: #7
**Workflow**: Quick Path (Analyze -> Fix -> Verify)
**Branch**: `modules` (current)

## Analysis Summary

`TaskExecutor._execute_coordinated_components()` identifies 5 registered components by matching
substrings against their `name` property. This works but is fragile: renaming a component class
or changing its `self.name` string would silently break the lookup.

Replace with `isinstance()` checks that provide type safety.

## Current Code (lines 263-273 of executor.py)

```python
for component in self.components:
    if "StaticAnalysis" in component.name:
        static_component = component
    elif "Coverage" in component.name:
        coverage_component = component
    elif "Emulator" in component.name:
        emulator_component = component
    elif "Logcat" in component.name:
        logcat_component = component
    elif "ToolExecution" in component.name:
        tool_component = component
```

## Target Code

```python
for component in self.components:
    if isinstance(component, StaticAnalysisComponent):
        static_component = component
    elif isinstance(component, CoverageComponent):
        coverage_component = component
    elif isinstance(component, EmulatorComponent):
        emulator_component = component
    elif isinstance(component, LogcatComponent):
        logcat_component = component
    elif isinstance(component, ToolExecutionComponent):
        tool_component = component
```

## Tasks

### Task 1: Add component imports to executor.py
Add imports for the 5 component classes.

### Task 2: Replace string matching with isinstance
Replace the 5 string-based conditions with isinstance checks.

### Task 3: Run tests
Verify no behavior change.

## Acceptance Criteria
- [ ] Zero string-based component identification patterns in executor.py
- [ ] Component lookup uses isinstance()
- [ ] All rv-platform tests pass
