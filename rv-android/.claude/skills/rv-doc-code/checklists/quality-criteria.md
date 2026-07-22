# Quality Criteria for Code Documentation

Standards and anti-patterns for docstrings and inline comments in RV-Android.

---

## Google-Style Format Checklist

### Summary Line

- [ ] Imperative mood ("Calculate similarity score." not "Calculates...")
- [ ] One line, ends with period
- [ ] Describes WHAT the function does, not HOW
- [ ] No parameter names in summary (save for Args section)

### Blank Lines

- [ ] Blank line after summary if there are additional sections
- [ ] Blank line between sections (Args, Returns, Raises, Example)
- [ ] No blank line before closing `"""`

### Args Section

- [ ] Each parameter on its own line: `name: Description.`
- [ ] No type annotations (types live in function signatures)
- [ ] Multi-line descriptions indented 4 spaces from parameter name
- [ ] Default values mentioned only when non-obvious
- [ ] Description starts with capital letter, ends with period

### Returns Section

- [ ] Describes the value, not the type
- [ ] For Dict returns: document keys with types and meaning
- [ ] For Optional returns: explain when None is returned
- [ ] For tuple returns: describe each element

### Raises Section

- [ ] Only exceptions the method itself raises
- [ ] Not exceptions from @ErrorHandler decorator
- [ ] Format: `ExceptionType: When this happens.`
- [ ] Covers all `raise` statements in the method

### Example Section

- [ ] Runnable Python (uses `>>>` doctest format)
- [ ] Shows typical usage, not edge cases
- [ ] Includes expected output for non-obvious results
- [ ] Only for Tier 1 methods with complex I/O

---

## Content Quality

### Summary

| Quality | Example |
|---------|---------|
| Good | "Detect actual package name of APK using priority-based heuristics." |
| Bad | "This method detects the package name." |
| Bad | "A function that finds packages." |

### Args

| Quality | Example |
|---------|---------|
| Good | `apk: Androguard APK instance (already loaded).` |
| Bad | `apk: The apk.` |
| Bad | `apk (APK): Androguard APK instance.` (type in docstring) |

### Returns

| Quality | Example |
|---------|---------|
| Good | `PackageDetectionResult with manifest_package, code_package, confidence, detection_method, and supporting data.` |
| Bad | `Returns a PackageDetectionResult.` |
| Good (dict) | `Dictionary with keys: "task_id" (str): Unique task identifier, "apk_name" (str): APK file name without extension` |

### WHY Blocks

| Quality | Example |
|---------|---------|
| Good | `# The manifest package can differ from the actual code package in apps using build flavors or game engines` |
| Bad | `# Check if packages are different` (restates code) |
| Bad | `# This is because of a design decision we made` (vague) |

---

## Inline Comment Quality

### Phase/Step Markers

- [ ] Numbered sequentially (Phase 1, Phase 2... or Step 1, Step 2...)
- [ ] Short description after number (not just "Phase 1:")
- [ ] Used consistently within a method (all phases or none)
- [ ] Phase for orchestration, Step for algorithms

### Section Dividers

- [ ] Format: `# === LABEL ===` (with spaces, all caps label)
- [ ] Used in constants/configuration files
- [ ] Group related constants logically
- [ ] Not used inside functions (use Phase/Step markers instead)

### WHY Blocks

- [ ] Explain rationale, not mechanics
- [ ] Placed BEFORE the code they explain
- [ ] Multi-line for complex reasoning (each line starts with `#`)
- [ ] No blank lines within a WHY block

### TODO/FIXME Format

- [ ] Format: `# TODO(context): description`
- [ ] Format: `# FIXME(context): description`
- [ ] Context is module name, issue number, or topic: `TODO(rv-agent)`, `TODO(#42)`, `FIXME(rv-coverage)`
- [ ] Description is actionable (starts with verb)
- [ ] No bare `# TODO:` without context

---

## P1-P4 Compliance

| Principle | Docstring Check | Inline Comment Check |
|-----------|----------------|---------------------|
| **P1 Simplicity** | Skip self-evident code. Three-line properties need no docstring. | No comments that restate code. No comment on `if not items: return []`. |
| **P2 Human-Readable** | Explain WHY in summary paragraph, not just WHAT. Self-contained for readers. | WHY blocks explain rationale. Phase markers give narrative flow. |
| **P3 No Backward Compat** | No "migrated from", "replaces old", "formerly known as". | No `# removed`, `# deprecated`, `# was previously`. |
| **P4 Current-State** | Describe what the code does NOW. No version history. | No promotional language. No "elegant", "modern", "advanced". |

---

## Review Questions

Use these to evaluate documentation quality:

1. **Would a developer understand this without reading the implementation?**
   - If yes → documentation is sufficient
   - If no → add more context to summary or WHY blocks

2. **Is there anything in the docstring that restates the code?**
   - If yes → remove it (P1)
   - Args descriptions should add context beyond what the type signature shows

3. **Does the docstring mention history or migration?**
   - If yes → rewrite to describe current behavior only (P4)

4. **Are there undocumented complex operations?**
   - If yes → add WHY blocks before them

5. **Is the tier appropriate?**
   - Over-documented trivial code violates P1
   - Under-documented public API hurts discoverability
