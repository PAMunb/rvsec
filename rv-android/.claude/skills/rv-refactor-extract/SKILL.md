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
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Extract Component: $ARGUMENTS

## Steps

1. **Parse arguments**:
   - File path containing code
   - Target to extract (function, class, or code block)

2. **Analyze file structure**:
   ```
   Invoke /rv-analyze-file $FILE_PATH
   ```
   This helps understand dependencies and what can be safely extracted.

3. **Analyze extraction target**:
   - What does it do?
   - What are its dependencies?
   - What depends on it?

4. **Plan extraction**:
   - New file location
   - Interface changes
   - Import updates needed

5. **Create backup**:
   ```bash
   cp path/to/file.py backup/file_before_extract.py
   ```

6. **Perform extraction**:
   - Create new file with extracted code
   - Update imports in original file
   - Update all files that used the extracted code

7. **Verify**:
   ```bash
   cd modules/$MODULE
   PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v
   ```

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
def helper_logic(data):
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
class HelperClass: ...

# mixed_file.py
from .helper_class import HelperClass
class MainClass: ...
```

### Extract Module
When multiple related classes/functions should move together.

## Output Format

```
## Extraction Report: [target]

### Extracted
- **From**: [original file]
- **To**: [new file]
- **Type**: function/class/module

### Changes Made

#### New File Created
- **Path**: [new file path]
- **Contains**: [list of extracted items]

#### Original File Updated
- Removed: [extracted code]
- Added import: `from .new_file import X`

#### Other Files Updated
| File | Change |
|------|--------|
| file.py | Updated import |

### Backup
- Created: backup/[filename]_before_extract.py

### Verification
- Tests: [pass/fail]
- Imports: [ok/broken]
```

## Guidelines

- Extract when file > 500 lines
- Extract when single file has multiple responsibilities
- Keep related code together
- Maintain clear interfaces
- Update all imports
