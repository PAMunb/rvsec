# Cleanup Analysis Report Template

---

## Cleanup Analysis Report

### Target: `[module-name]`
### Date: `[YYYY-MM-DD]`

---

## 1. Dead Code Found

### Unused Imports

| File | Line | Import | Confidence |
|------|------|--------|------------|
| `file.py` | 10 | `unused_module` | HIGH |

### Unused Functions

| File | Line | Function | Callers Found | Confidence |
|------|------|----------|---------------|------------|
| `file.py` | 50 | `old_function()` | 0 | HIGH |

### Unused Classes

| File | Line | Class | References | Confidence |
|------|------|-------|------------|------------|
| `file.py` | 100 | `LegacyClass` | 0 | MEDIUM |

### Unused Variables

| File | Line | Variable | Confidence |
|------|------|----------|------------|
| `file.py` | 25 | `temp_var` | HIGH |

### Commented Code Blocks

| File | Lines | Description |
|------|-------|-------------|
| `file.py` | 200-220 | Old implementation |

---

## 2. Dependency Issues

### Circular Dependencies

| Cycle | Modules Involved | Risk |
|-------|------------------|------|
| None found | - | - |

### Unused Dependencies (pyproject.toml)

| Package | Used In | Recommendation |
|---------|---------|----------------|
| `old-package` | Nowhere | Remove |

---

## 3. Complexity Issues

### Over-Engineered Code

| File | Issue | Recommendation |
|------|-------|----------------|
| `file.py` | Unnecessary abstraction | Simplify |

### Duplicated Code

| Location 1 | Location 2 | Lines | Recommendation |
|------------|------------|-------|----------------|
| `a.py:10` | `b.py:20` | 15 | Extract common |

---

## 4. Summary

| Category | Count | Est. Lines to Remove |
|----------|-------|---------------------|
| Unused imports | X | Y |
| Unused functions | X | Y |
| Unused classes | X | Y |
| Commented code | X | Y |
| **Total** | **X** | **Y** |

---

## 5. Risk Assessment

| Item | Risk Level | Reason |
|------|------------|--------|
| Remove `old_function` | LOW | No callers |
| Remove `LegacyClass` | MEDIUM | May use reflection |

---

## 6. Recommendations

1. **Priority 1**: Remove unused imports (safest)
2. **Priority 2**: Remove unused private functions
3. **Priority 3**: Review and remove unused classes
