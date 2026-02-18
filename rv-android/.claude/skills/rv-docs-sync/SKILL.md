---
name: rv-docs-sync
description: >-
  Synchronize documentation with code. Use after refactoring, adding features, or when docs might be stale.
  Updates CLAUDE.md, architecture.md, and validates ADRs.
  Do NOT use for: creating new docs from scratch (use /rv-doc-generate-claude-md, /rv-doc-architecture, /rv-doc-adr).
argument-hint: [module-name or 'all']
context: fork
agent: general-purpose
allowed-tools: Read, Write, Grep, Glob, Bash, Skill
---

# Sync Documentation: $ARGUMENTS

Documentation Orchestrator that detects code changes and updates documentation accordingly.

## Documentation Guidelines

**CRITICAL**: Follow these guidelines:

1. **Language**: English only
2. **Tone**: Professional, objective, factual
3. **No bias terms**: Avoid "modern", "better", "elegant"
4. **Current state only**: Do not reference migration or legacy

## Managed Documentation

| File | Location | Purpose |
|------|----------|---------|
| CLAUDE.md | `modules/<module>/CLAUDE.md` | Quick reference for Claude |
| architecture.md | `modules/<module>/docs/architecture.md` | Detailed architecture |
| ADRs | `modules/<module>/docs/adr/ADR-*.md` | Architecture decisions |

## Supporting Files

- **Templates**: `templates/sync-report.md` - Report output format

---

## Workflow

```
STEP 1: DETECT CHANGES ──────────────────────────────────────────►
    │  git diff to find modified files
    ▼
STEP 2: GROUP BY MODULE ─────────────────────────────────────────►
    │  Organize changes by affected module
    ▼
STEP 3: ASSESS SEVERITY ─────────────────────────────────────────►
    │  Architecture change vs minor update
    ▼
STEP 4: UPDATE DOCS ─────────────────────────────────────────────►
    │  Regenerate or update specific sections
    ▼
STEP 5: VERIFY CONSISTENCY ──────────────────────────────────────►
    │  Check docs match code
    ▼
REPORT ──────────────────────────────────────────────────────────►
```

---

## Steps

### 1. Detect Code Changes

```bash
# Get changed files since last commit or from HEAD~1
git diff --name-only HEAD~1

# Or since specific commit
git diff --name-only [commit-hash]

# Filter to Python source files
git diff --name-only HEAD~1 | grep -E "^modules/.*/src/.*\.py$"
```

### 2. Group Changes by Module

Parse changed files to determine affected modules:

```
modules/rv-agent/src/rv_agent/llm/llm_client.py  → rv-agent
modules/rv-platform/src/rv_platform/platform.py → rv-platform
```

### 3. Assess Change Severity

For each module, categorize changes:

| Severity | Criteria | Action |
|----------|----------|--------|
| **ARCHITECTURE** | New/deleted files, renamed modules, new dependencies | Regenerate full CLAUDE.md |
| **STRUCTURAL** | New classes, changed public APIs | Update Key Components section |
| **BEHAVIORAL** | Modified logic, bug fixes | Update Gotchas if applicable |
| **MINOR** | Formatting, comments, internal refactoring | No doc update needed |

### 4. Determine Required Updates

**For ARCHITECTURE changes** - Use the **Skill tool**:
```
Skill tool: skill="rv-doc-generate-claude-md", args="[module]"
Skill tool: skill="rv-doc-architecture", args="[module]"  # If architecture.md exists
```

**For STRUCTURAL changes:**
Update specific sections:
- Key Components table (CLAUDE.md)
- Component Architecture section (architecture.md)
- Dependencies list (both)

**For BEHAVIORAL changes:**
Check if Gotchas section needs update (CLAUDE.md)

### 5. Update Documentation

For each module needing updates:

1. Read current CLAUDE.md
2. Identify sections to update
3. Preserve custom content (marked `<!-- CUSTOM -->`)
4. Write updated file

### 6. Verify Consistency

Cross-check:
- [ ] All public modules have CLAUDE.md
- [ ] architecture.md matches current structure (if exists)
- [ ] ADRs are still valid (not superseded by code changes)
- [ ] Dependencies match pyproject.toml
- [ ] Entry points are accurate
- [ ] Test paths are correct

---

## Documentation Principles

Apply these principles to all generated documentation:

1. **Reader perspective**: Write from the reader's viewpoint. What do they need to know? What will they look for first? Structure content for their workflow, not for comprehensiveness.
2. **No repetition**: State information once in the most logical location. Cross-reference instead of duplicating. If the same fact appears in two sections, one is wrong.
3. **No ambiguity**: Define terminology on first use. Use precise file paths. Prefer concrete examples over abstract descriptions. If a notation is used (diagram, table), explain how to read it.
4. **Standard organization**: Follow the established templates and section order. Consistency across documents reduces cognitive load. Deviations must be justified by content needs.
5. **Capture rationale**: Document WHY, not just WHAT. Every significant choice should have a brief explanation. Future readers need to understand the reasoning to make informed changes.
6. **Currency**: Only document current state (P4). Do not include migration history, version notes, or planned features. If something changed, describe the current behavior only.
7. **Stakeholder awareness**: Know the audience. CLAUDE.md is for LLMs (precise paths, exact commands). architecture.md is for developers (conceptual understanding). README.md is for newcomers (getting started).

## Output Format

```markdown
## Documentation Sync Report

### Changes Detected
| Module | Files Changed | Severity |
|--------|---------------|----------|
| rv-agent | 5 | STRUCTURAL |
| rv-platform | 2 | MINOR |

### Actions Taken
| Module | Action | Status |
|--------|--------|--------|
| rv-agent | Updated Key Components | DONE |
| rv-platform | No update needed | SKIPPED |

### Verification
- [ ] All CLAUDE.md files up to date
- [ ] architecture.md files match code (if exist)
- [ ] ADRs still valid
- [ ] No missing documentation
- [ ] Dependencies consistent

### Summary
- Modules scanned: X
- Updates made: Y
- Issues found: Z
```

---

## Special Handling

### When to Regenerate Full CLAUDE.md

- New module created
- Module renamed
- Major architectural change
- Dependencies significantly changed
- More than 5 files changed in module

### When to Skip

- Only test files changed
- Only comments/docstrings changed
- Changes in `backup/` directory
- Changes in `__pycache__/`

### Custom Content Markers

Preserve content between these markers:
```markdown
<!-- CUSTOM:START -->
User-added content that should not be overwritten
<!-- CUSTOM:END -->
```

---

## Integration Notes

This skill is called by orchestrators in the Audit phase:
- `rv-refactor` → After code changes committed
- `rv-feature` → After feature implementation
- `rv-cleanup` → After dead code removal

Called as: `Skill tool: skill="rv-docs-sync", args="[module]"`

---

## Rules

1. **DETECT before updating** - Don't regenerate unnecessarily
2. **PRESERVE custom content** - Never overwrite user additions
3. **VERIFY consistency** - Check docs match code
4. **REPORT all actions** - Document what was changed
5. **MINIMAL updates** - Only update affected sections
