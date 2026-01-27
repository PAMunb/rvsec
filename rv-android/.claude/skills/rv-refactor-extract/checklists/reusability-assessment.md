# Reusability Assessment Checklist

A framework for evaluating extraction candidates and designing reusable components.

---

## Overview

Before extracting code, assess whether it should be extracted for reuse. Not all code benefits from extraction - the decision depends on several factors.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Reuse Decision Framework                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. IDENTIFY ─────► Is this code duplicated or potentially shared? │
│                                                                     │
│  2. ASSESS ───────► Does extraction provide net benefit?           │
│                                                                     │
│  3. LEVEL ────────► What granularity makes sense?                  │
│                                                                     │
│  4. DESIGN ───────► How to make it truly reusable?                 │
│                                                                     │
│  5. DOCUMENT ─────► How will others find and use it?               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Identify Extraction Candidates

### Code Patterns Suggesting Extraction

| Pattern | Indicator | Action |
|---------|-----------|--------|
| **Duplication** | Same/similar code in 2+ places | Extract to shared location |
| **Large Files** | File > 500 lines | Split by responsibility |
| **Mixed Concerns** | Multiple unrelated classes in one file | Separate by concern |
| **Domain Logic** | Business rules embedded in infrastructure | Extract to domain layer |
| **Utility Code** | Generic helpers repeated across modules | Extract to shared utilities |
| **Complex Algorithms** | Intricate logic deserving isolation | Extract with clear interface |

### Questions to Identify Candidates

```markdown
## Extraction Candidate Analysis

### File: [path]

- [ ] Is there duplicated code across files?
- [ ] Does the file have multiple responsibilities?
- [ ] Are there utility functions that could be shared?
- [ ] Is there complex logic that deserves isolation?
- [ ] Could other modules benefit from this code?
- [ ] Is the code too tightly coupled to its context?
```

---

## Step 2: Assess Extraction Value

### Benefits of Extraction

| Benefit | Description | Weight |
|---------|-------------|--------|
| **Reduced Duplication** | DRY principle, single source of truth | High |
| **Increased Dependability** | Reused code is more tested | High |
| **Reduced Risk** | Known code vs new development | Medium |
| **Specialist Encapsulation** | Expert knowledge in one place | Medium |
| **Standards Compliance** | Consistent implementation | Medium |
| **Accelerated Development** | Future work can reuse | High |

### Costs and Problems of Extraction

| Cost | Description | Weight |
|------|-------------|--------|
| **Increased Complexity** | More files, more indirection | Medium |
| **Maintenance Overhead** | Separate component to maintain | Medium |
| **Finding Difficulty** | Others may not discover it | Low |
| **Adaptation Cost** | May need modification for new contexts | Medium |
| **Not-Invented-Here** | Resistance to using shared code | Low |

### Assessment Template

```markdown
## Extraction Assessment: [component name]

### Benefits Score (0-5 each)
| Benefit | Score | Justification |
|---------|-------|---------------|
| Reduced Duplication | [0-5] | [why] |
| Increased Dependability | [0-5] | [why] |
| Reduced Risk | [0-5] | [why] |
| Specialist Encapsulation | [0-5] | [why] |
| Standards Compliance | [0-5] | [why] |
| Accelerated Development | [0-5] | [why] |
| **Total Benefits** | [/30] | |

### Costs Score (0-5 each)
| Cost | Score | Justification |
|------|-------|---------------|
| Increased Complexity | [0-5] | [why] |
| Maintenance Overhead | [0-5] | [why] |
| Finding Difficulty | [0-5] | [why] |
| Adaptation Cost | [0-5] | [why] |
| **Total Costs** | [/20] | |

### Net Value = Benefits - Costs = [X]
- **> 15**: Strong candidate for extraction
- **10-15**: Consider extraction
- **< 10**: May not be worth extracting
```

---

## Step 3: Choose Extraction Level

### Reuse Granularity Levels

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Reuse Levels                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Level 1: FUNCTION/CLASS REUSE                                      │
│  ├── Single functions or classes                                    │
│  ├── Program libraries, utility modules                             │
│  └── Example: math functions, string helpers                        │
│                                                                     │
│  Level 2: COMPONENT REUSE                                           │
│  ├── Groups of related classes                                      │
│  ├── Subsystems with clear interfaces                               │
│  └── Example: logging system, configuration manager                 │
│                                                                     │
│  Level 3: FRAMEWORK REUSE                                           │
│  ├── Skeleton architecture with extension points                    │
│  ├── Inversion of control (callbacks, hooks)                        │
│  └── Example: testing framework, plugin system                      │
│                                                                     │
│  Level 4: APPLICATION REUSE                                         │
│  ├── Complete applications configured for context                   │
│  ├── Product lines with common core                                 │
│  └── Example: configurable tools, parameterized modules             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Level Selection Guide

| Situation | Recommended Level |
|-----------|-------------------|
| Single utility function used in 2-3 places | Level 1 (Function) |
| Related set of data structures + operations | Level 2 (Component) |
| Architecture pattern with customization points | Level 3 (Framework) |
| Similar applications with different configs | Level 4 (Application) |

### Extraction Destinations

| Level | Destination | Example |
|-------|-------------|---------|
| Function | Same module's utilities | `module/utils.py` |
| Class | Separate file in module | `module/helper.py` |
| Component | Subpackage in module | `module/subcomponent/` |
| Shared Component | Core module | `rv-android-core/` |
| New Module | Separate Poetry package | `modules/new-module/` |

---

## Step 4: Design for Reusability

### Characteristics of Reusable Components

| Characteristic | Description | How to Achieve |
|----------------|-------------|----------------|
| **Single Responsibility** | Does one thing well | Clear, focused purpose |
| **Minimal Dependencies** | Few external requirements | Depend on abstractions |
| **Clear Interface** | Easy to understand API | Good naming, documentation |
| **Configurable** | Adaptable to contexts | Parameters, not hardcoding |
| **Testable** | Can be tested in isolation | Dependency injection |
| **Documented** | Others can understand it | Docstrings, examples |

### Interface Design Checklist

```markdown
## Interface Design: [component name]

- [ ] **Naming**: Names describe what, not how
- [ ] **Parameters**: All inputs are parameters (no globals)
- [ ] **Returns**: Clear, documented return types
- [ ] **Errors**: Well-defined error conditions
- [ ] **Defaults**: Sensible default values where possible
- [ ] **Contracts**: Pre/post conditions documented

### Interface Specification

**Purpose**: [one sentence]

**Public API**:
| Method/Function | Parameters | Returns | Description |
|-----------------|------------|---------|-------------|
| `name()` | `param: Type` | `ReturnType` | What it does |

**Usage Example**:
```python
# Show typical usage
result = component.method(input)
```
```

### Dependency Management

```markdown
## Dependencies

### Required Dependencies
| Dependency | Why Needed | Alternative |
|------------|------------|-------------|
| [package] | [reason] | [if unavailable] |

### Dependency Injection Points
| What | How Injected | Default |
|------|--------------|---------|
| [dependency] | Constructor/Parameter | [default impl] |
```

---

## Step 5: Document for Discovery

### Component Documentation Template

```markdown
# Component: [Name]

## Purpose
[One paragraph describing what this component does and why it exists]

## When to Use
- [Situation 1 where this component is appropriate]
- [Situation 2]

## When NOT to Use
- [Situation where a different approach is better]

## Installation/Import
```python
from module.path import ComponentName
```

## Quick Start
```python
# Minimal example showing basic usage
component = ComponentName(config)
result = component.do_something(input)
```

## API Reference

### `ComponentName`

#### `__init__(self, config: Config)`
Initialize the component.
- **config**: Configuration object

#### `method_name(self, param: Type) -> ReturnType`
Description of what this method does.
- **param**: Description
- **returns**: Description

## Configuration Options
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option1` | `str` | `"default"` | What it controls |

## Examples

### Example 1: Basic Usage
```python
# Full working example
```

### Example 2: Advanced Usage
```python
# Example showing more features
```

## Related Components
- [`OtherComponent`](./other.md) - Related functionality
```

---

## Key Planning Factors

Before finalizing extraction, consider:

| Factor | Question | Impact on Decision |
|--------|----------|-------------------|
| **Schedule** | Is there time to do it right? | Rush = skip extraction |
| **Lifetime** | Will this code live long? | Short-lived = skip |
| **Team Skills** | Can team maintain extracted component? | No expertise = simplify |
| **Criticality** | Is reused code safety-critical? | Critical = more testing |
| **Domain** | Are there existing solutions? | Check before creating |
| **Platform** | Will it work across all targets? | Platform-specific = limit scope |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Description | Better Approach |
|--------------|-------------|-----------------|
| **Premature Extraction** | Extracting before patterns emerge | Wait for 3+ uses |
| **Over-generalization** | Making everything configurable | Start specific, generalize later |
| **Leaky Abstraction** | Exposing implementation details | Hide internals completely |
| **God Component** | One component does everything | Keep focused responsibility |
| **Forced Reuse** | Using component when doesn't fit | Allow some duplication |

---

## Summary Checklist

Before extracting:

- [ ] Identified clear extraction candidate
- [ ] Assessed benefits > costs
- [ ] Chose appropriate granularity level
- [ ] Designed clean interface
- [ ] Minimized dependencies
- [ ] Created documentation plan
- [ ] Considered long-term maintenance
- [ ] Verified team can support it

After extracting:

- [ ] All tests pass
- [ ] All imports updated
- [ ] Documentation written
- [ ] Usage examples provided
- [ ] Team notified of new component
