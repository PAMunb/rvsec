---
name: rv-refactor-extract
description: >-
  Extract function, class, or module from complex code. Use when splitting large files,
  isolating concerns, or improving modularity.
  Do NOT use for: simplification without extraction (use /rv-refactor-simplify),
  full module refactoring (use /rv-refactor).
argument-hint: [file-path] [target-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Skill
disable-model-invocation: true
---

# Extract Component: $ARGUMENTS

## Supporting Files

Reference these files from this skill directory:
- **Checklists**:
  - `checklists/reusability-assessment.md` - Evaluate extraction candidates and design for reuse

## Guiding Principles

When deciding what to extract and how, you must be guided by fundamental software design principles that improve modularity and quality.

1.  **High Cohesion**: A cohesive module performs a single, well-defined task. The code you extract should have a clear and singular purpose.
    *   **Justification**: "I am extracting these functions into a new `ImageProcessor` class because they all relate to image manipulation. This increases **cohesion** by grouping related responsibilities, following the Single Responsibility Principle."

2.  **Low Coupling**: The extracted component should have minimal dependencies on the code it's leaving behind, and vice-versa. Its interface should be small and well-defined.
    *   **Justification**: "The proposed interface for this new service has only two methods and doesn't depend on the internal state of the calling class. This promotes **low coupling** and reduces the risk of ripple effects from future changes."

3.  **Abstraction & Information Hiding**: The new component should hide its internal implementation details. Users of the component should only interact with it through its public API, without needing to know *how* it works.
    *   **Justification**: "By creating the `ReportGenerator` class, I am applying **abstraction**. The calling code will only need to know about the `generate()` method, hiding the complexity of PDF creation and data formatting."

4.  **Separation of Concerns (SoC)**: Ensure that different concepts are in different parts of the code. Extraction is a key tool for separating concerns like UI, data access, and business logic.
    *   **Justification**: "This extraction separates the data validation logic from the user interface rendering, improving **Separation of Concerns**. This makes both components easier to understand and maintain independently."

5.  **Reusability**: Extract code that is, or could be, used in multiple places. Don't repeat yourself (DRY).
    *   **Justification**: "This code is duplicated in three different places. By extracting it into a single utility function, I am improving **reusability** and making future maintenance easier."

## Requirement for Principle-Based Justification

When you propose an extraction, you **must** justify it using the principles above. Explain *why* the extraction improves the design quality.

- "This extraction is justified because it improves **cohesion** and **separation of concerns** by..."
- "I designed the interface for the new class to ensure **low coupling** by..."

This ensures that refactoring is deliberate and directly contributes to a better software architecture.

---

## Workflow

```
PHASE 1: IDENTIFY ────────────────────────────────────────────────────►
    │  Analyze target, find extraction candidates
    ▼
PHASE 2: ASSESS ──────────────────────────────────────────────────────►
    │  Evaluate reusability, benefits vs costs
    ▼
PHASE 3: DESIGN ──────────────────────────────────────────────────────►
    │  Plan interface, choose granularity level
    ▼
PHASE 4: EXTRACT ─────────────────────────────────────────────────────►
    │  Create new file, update imports
    ▼
PHASE 5: VERIFY ──────────────────────────────────────────────────────►
    │  Run tests, validate extraction
    ▼
DONE
```

---

## Phase 1: Identify Extraction Target

### Step 1.1: Parse Arguments
- File path containing code
- Target to extract (function, class, or code block)

### Step 1.2: Analyze File Structure

Use the **Skill tool**:
```
Skill tool: skill="rv-analyze-file", args="$FILE_PATH"
```

This helps understand dependencies and what can be safely extracted.

### Step 1.3: Identify Extraction Candidates

Look for these patterns:

| Pattern | Indicator | Extraction Type |
|---------|-----------|-----------------|
| **Duplication** | Same code in 2+ places | Function/Class |
| **Large File** | File > 500 lines | Split by responsibility |
| **Mixed Concerns** | Unrelated classes together | Separate files |
| **Utility Code** | Generic helpers | Shared utilities |
| **Complex Logic** | Algorithm deserving isolation | Dedicated module |

---

## Phase 2: Assess Reusability

Reference: `checklists/reusability-assessment.md`

### Step 2.1: Evaluate Benefits

| Benefit | Question | Score (0-5) |
|---------|----------|-------------|
| **Reduced Duplication** | Will this eliminate copy-paste? | |
| **Increased Dependability** | Will reused code be more tested? | |
| **Reduced Risk** | Is this known, working code? | |
| **Accelerated Development** | Will future work benefit? | |

### Step 2.2: Evaluate Costs

| Cost | Question | Score (0-5) |
|------|----------|-------------|
| **Increased Complexity** | How many more files/indirection? | |
| **Maintenance Overhead** | Is there capacity to maintain? | |
| **Adaptation Cost** | Will it need modification for new uses? | |

### Step 2.3: Make Decision

```markdown
## Extraction Decision

**Benefits Total**: [X/20]
**Costs Total**: [Y/15]
**Net Value**: [Benefits - Costs]

Decision:
- > 10: Proceed with extraction
- 5-10: Consider simpler alternative
- < 5: Do not extract
```

---

## Phase 3: Design for Reuse

### Step 3.1: Choose Granularity Level

| Level | When to Use | Destination |
|-------|-------------|-------------|
| **Function** | Single utility used in 2-3 places | `module/utils.py` |
| **Class** | Data structure + operations | `module/component.py` |
| **Component** | Related set of classes | `module/subpackage/` |
| **Shared** | Cross-module utility | `rv-android-core/` |

### Step 3.2: Design Interface

```markdown
## Interface Design

**Purpose**: [one sentence]

**Public API**:
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `name()` | `param: Type` | `ReturnType` | What it does |

**Dependencies**:
- [list external dependencies]

**Usage Example**:
```python
from module.component import function
result = function(input)
```
```

### Step 3.3: Plan File Structure

```markdown
## File Structure

**New File**: [path/to/new_file.py]
**Contains**:
- [list of classes/functions to extract]

**Original File**: [path/to/original.py]
**Changes**:
- Remove: [extracted code]
- Add import: `from .new_file import X`

**Other Files to Update**:
| File | Change |
|------|--------|
| [file.py] | Update import |
```

---

## Phase 4: Perform Extraction

### Step 4.1: Create Backup

```bash
cp path/to/file.py backup/file_before_extract.py
```

### Step 4.2: Create New File

Include:
- Module docstring explaining purpose
- Imports needed by extracted code
- Extracted code with original docstrings
- `__all__` if multiple exports

### Step 4.3: Update Original File

- Remove extracted code
- Add import from new file
- Ensure all references work

### Step 4.4: Update Dependent Files

Find all files importing from original:
```bash
grep -r "from original import" modules/
```

Update imports as needed.

---

## Phase 5: Verify Extraction

### Step 5.1: Run Tests

```bash
cd modules/$MODULE
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v
```

### Step 5.2: Verify Imports

```bash
cd modules/$MODULE
uv run python -c "from module.new_file import X; print('Import OK')"
```

### Step 5.3: Check for Broken References

Use the **Skill tool**:
```
Skill tool: skill="rv-analyze-dependencies", args="$MODULE"
```

---

## Extraction Types

### Extract Function

```python
# Before (in large_file.py)
def complex_function():
    # ... 50 lines of helper logic ...
    result = helper_logic(data)
    # ... more code ...

# After
# helper.py
"""Helper functions for [purpose]."""

def helper_logic(data):
    """Process data and return result.

    Args:
        data: Input data to process

    Returns:
        Processed result
    """
    # ... extracted logic ...

# large_file.py
from .helper import helper_logic

def complex_function():
    result = helper_logic(data)
    # ... more code ...
```

### Extract Class

```python
# Before (in mixed_file.py)
class MainClass: ...
class HelperClass: ...  # Extract this

# After
# helper_class.py
"""Helper class for [purpose]."""

class HelperClass:
    """Description of what this class does."""
    ...

# mixed_file.py
from .helper_class import HelperClass

class MainClass: ...
```

### Extract Module (Subpackage)

When multiple related classes/functions should move together:

```
# Before
module/
    big_file.py  # Contains ClassA, ClassB, ClassC

# After
module/
    __init__.py
    big_file.py  # Only MainClass
    subcomponent/
        __init__.py  # exports ClassA, ClassB, ClassC
        class_a.py
        class_b.py
        class_c.py
```

---

## Output Format

```markdown
## Extraction Report: [target]

### Summary
- **Extracted**: [what was extracted]
- **From**: [original file]
- **To**: [new file]
- **Type**: function/class/module
- **Reuse Level**: Function/Component/Shared

### Reusability Assessment
- **Benefits Score**: [X/20]
- **Costs Score**: [Y/15]
- **Net Value**: [X-Y] (threshold: 10)

### Interface
```python
# How to use the extracted component
from module.new_file import Component
result = Component.method(input)
```

### Files Changed

#### New File Created
- **Path**: [new file path]
- **Contains**: [list of extracted items]
- **Purpose**: [why it exists]

#### Original File Updated
- Removed: [extracted code]
- Added import: `from .new_file import X`

#### Other Files Updated
| File | Change |
|------|--------|
| file.py | Updated import |

### Verification
- Tests: [pass/fail]
- Imports: [ok/broken]

### Backup
- Created: backup/[filename]_before_extract.py
```

---

## Guidelines

### When to Extract

- File > 500 lines
- Same code appears 2+ times
- Single file has multiple responsibilities
- Code could benefit other modules
- Complex algorithm deserves isolation

### When NOT to Extract

- Code is used only once and unlikely to be reused
- Extraction would add complexity without benefit
- Team doesn't have capacity to maintain separate component
- Code is too tightly coupled to its context

### Best Practices

- **Wait for patterns**: Extract after 2-3 uses, not speculatively
- **Start specific**: Don't over-generalize initially
- **Clear interfaces**: Hide implementation details
- **Minimal dependencies**: Depend on abstractions
- **Document for discovery**: Others need to find it
- **Keep related code together**: Don't fragment cohesive units
