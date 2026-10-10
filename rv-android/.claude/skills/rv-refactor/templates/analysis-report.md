# Analysis Report Template

Use this template to document Phase 1 (Analysis) findings.

---

## Refactoring Analysis Report

### Target: `[module or file path]`
### Date: `[YYYY-MM-DD]`
### Analyst: Claude Code

---

## 1. Executive Summary

[2-3 sentences summarizing the main findings and recommendations]

---

## 2. Complexity Metrics

### Files Analyzed

| File | Lines | Functions | Classes | Complexity Score |
|------|-------|-----------|---------|------------------|
| `path/to/file.py` | XXX | XX | X | HIGH/MEDIUM/LOW |

### Threshold Violations

Thresholds come from `.claude/skills/rv-analyze-complexity/reference.md`; copy the band you applied, do not restate a number from memory.

| Metric | Threshold (band) | Actual | Files Affected |
|--------|------------------|--------|----------------|
| Lines per file | [file size band] | XXX | file1.py, file2.py |
| Function length | [function size band] | XXX | file1.py:func_name |
| Nesting depth | [nesting band] | X | file2.py:method_name |

---

## 3. Dependency Analysis

### Internal Dependencies

```
[module] depends on:
├── rv-android-core (foundation)
└── rv-screen-parser (UI parsing)
```

### Circular Dependencies

| Cycle | Risk | Recommendation |
|-------|------|----------------|
| A → B → A | HIGH | Break by extracting interface |
| None found | - | - |

### Coupling Assessment (per workspace module, from /rv-analyze-dependencies)

| Module | Ca (dependent modules) | Ce (modules depended on) | Instability Ce/(Ca+Ce) |
|--------|------------------------|--------------------------|------------------------|
| rv-xxx | X | Y | Y/(X+Y) |

---

## 4. Identified Refactoring Targets

### Priority 1 (Critical)

| Target | Issue | Impact | Effort |
|--------|-------|--------|--------|
| `file.py` | 800 lines, 5 responsibilities | HIGH | MEDIUM |

### Priority 2 (Important)

| Target | Issue | Impact | Effort |
|--------|-------|--------|--------|
| `other.py` | Duplicated logic with X | MEDIUM | LOW |

### Priority 3 (Nice to Have)

| Target | Issue | Impact | Effort |
|--------|-------|--------|--------|
| `util.py` | Could be simplified | LOW | LOW |

---

## 5. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing tests | MEDIUM | HIGH | Run tests after each change |
| Introducing regressions | LOW | HIGH | Comprehensive backup |

---

## 6. Recommendations

1. **Immediate**: [what to do first]
2. **Short-term**: [next steps]
3. **Long-term**: [future improvements]

---

## 7. Next Steps

- [ ] Present this analysis to user for approval
- [ ] Create detailed refactoring plan
- [ ] Estimate effort for each target
