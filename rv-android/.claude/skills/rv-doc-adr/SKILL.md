---
name: rv-doc-adr
description: >-
  Create Architecture Decision Record (ADR) for significant decisions.
  Use when making refactoring decisions, choosing technologies, or changing architecture.
  Do NOT use for: minor code changes, bug fixes, or documentation updates.
  Use /rv-doc-architecture for module docs, /rv-doc-generate-claude-md for CLAUDE.md.
argument-hint: [decision-title]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash, AskUserQuestion
---

# Create ADR: $ARGUMENTS

Creates an Architecture Decision Record at `modules/<module>/docs/adr/ADR-XXX-<title>.md`.

## Documentation Guidelines

**CRITICAL**: Follow these guidelines:

1. **Language**: English only
2. **Tone**: Professional, objective, factual
3. **No bias terms**: Avoid "modern", "better", "elegant"
4. **Neutral comparison**: Present options objectively with trade-offs

## When to Create ADR

| Situation | Create ADR? |
|-----------|-------------|
| Major refactoring | ✅ Yes |
| New architectural pattern | ✅ Yes |
| Technology choice | ✅ Yes |
| Breaking API changes | ✅ Yes |
| Bug fix | ❌ No |
| Minor refactoring | ❌ No |
| Code formatting | ❌ No |

## Workflow

```
STEP 1: GATHER CONTEXT ──────────────────────────────────────────►
    │  Understand the decision context
    ▼
STEP 2: ASK FOR DETAILS ─────────────────────────────────────────►
    │  Get missing information from user
    ▼
STEP 3: DETERMINE NUMBER ────────────────────────────────────────►
    │  Find next ADR number for module
    ▼
STEP 4: GENERATE ADR ────────────────────────────────────────────►
    │  Write ADR from template
    ▼
STEP 5: LINK TO ARCHITECTURE ────────────────────────────────────►
    │  Reference in architecture.md if exists
```

## Steps

### 1. Gather Context

Ask user with `AskUserQuestion`:
- What module does this affect?
- What is the decision being made?
- What are the options considered?
- What is the chosen option and why?

### 2. Determine ADR Number

```bash
MODULE="[module-name]"
mkdir -p modules/$MODULE/docs/adr

# Find next number
NEXT_NUM=$(ls modules/$MODULE/docs/adr/ADR-*.md 2>/dev/null | wc -l)
NEXT_NUM=$((NEXT_NUM + 1))
printf "ADR-%03d" $NEXT_NUM
```

### 3. Generate ADR

Write to `modules/<module>/docs/adr/ADR-XXX-<title>.md`.

## Template: ADR

```markdown
# ADR-[NUMBER]: [Title]

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Date

[YYYY-MM-DD]

## Context

[What is the issue that we're seeing that is motivating this decision or change?]

## Decision Drivers

- [Driver 1]: [Explanation]
- [Driver 2]: [Explanation]

## Considered Options

### Option 1: [Name]

**Description**: [What this option involves]

**Pros**:
- [Pro 1]
- [Pro 2]

**Cons**:
- [Con 1]
- [Con 2]

### Option 2: [Name]

**Description**: [What this option involves]

**Pros**:
- [Pro 1]
- [Pro 2]

**Cons**:
- [Con 1]
- [Con 2]

## Decision

[Option X] because [reasons].

## Consequences

### Positive
- [Consequence 1]
- [Consequence 2]

### Negative
- [Consequence 1]
- [Consequence 2]

### Neutral
- [Consequence 1]

## Implementation Notes

[Any specific implementation details or considerations]

## Related

- [Link to related ADRs]
- [Link to related architecture docs]
- [Link to related code]
```

## Output

```
## Created: ADR-XXX-[title]

### File
- **Path**: modules/[module]/docs/adr/ADR-XXX-[title].md
- **Status**: Proposed

### Summary
- **Decision**: [Brief summary]
- **Chosen Option**: [Option name]
- **Key Reason**: [Main reason]

### Next Steps
- Review with team
- Update status to "Accepted" after review
- Implement decision
- Update architecture.md to reference this ADR
```

## ADR Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded]
```

- **Proposed**: Initial creation, under review
- **Accepted**: Decision approved and implemented
- **Deprecated**: No longer relevant
- **Superseded**: Replaced by newer ADR

## Rules

1. **One decision per ADR** - Keep focused
2. **Objective language** - No bias terms
3. **Include all options** - Even rejected ones
4. **Document trade-offs** - Both pros and cons
5. **Link to code** - Reference implementation
