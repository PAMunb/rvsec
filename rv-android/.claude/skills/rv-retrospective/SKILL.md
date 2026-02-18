---
name: rv-retrospective
description: >-
  Conduct process retrospective and improvement analysis. Use after completing
  a feature, sprint, or project phase to identify lessons learned and improvements.
  Do NOT use for: code changes, bug fixes, or active development tasks.
argument-hint: [scope: feature|sprint|project]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash
disable-model-invocation: true
---

# Process Retrospective: $ARGUMENTS

## Supporting Files

Reference these files from this skill directory:
- **Checklists**:
  - `checklists/process-analysis.md` - 7 aspects to investigate
  - `checklists/improvement-cycle.md` - Measure-Analyze-Change framework
  - `checklists/gqm-framework.md` - Goal-Question-Metric approach

---

## Process Improvement Cycle

Retrospectives follow a continuous improvement cycle:

```
    ┌─────────┐
    │ Measure │
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Analyze │
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Change  │
    └────┬────┘
         │
         └──────────► (repeat)
```

---

## Workflow

### Phase 1: Scope Definition

Define what is being retrospected:

| Scope | Typical Duration | Focus |
|-------|-----------------|-------|
| **Feature** | Days to weeks | Single feature implementation |
| **Sprint** | 1-2 weeks | Sprint goals and deliverables |
| **Project** | Months | Overall project outcomes |

### Phase 2: Data Collection (Measure)

Reference: `checklists/improvement-cycle.md`

Collect quantitative and qualitative data:

#### 2.1 Process Metrics
```markdown
## Metrics Collected

### Time Metrics
- [ ] Total duration (calendar time)
- [ ] Active development time
- [ ] Time waiting/blocked

### Resource Metrics
- [ ] Effort (person-days)
- [ ] Tools/infrastructure used
- [ ] External dependencies

### Event Metrics
- [ ] Defects found during development
- [ ] Defects found after delivery
- [ ] Rework incidents
- [ ] Change requests
```

#### 2.2 Qualitative Data
- Git history analysis (commits, branches, merges)
- Code review comments and discussions
- Test results and coverage changes
- Issues/tickets created during work

### Phase 3: Process Analysis (Analyze)

Reference: `checklists/process-analysis.md`

Investigate 7 key aspects:

| Aspect | Key Question |
|--------|--------------|
| **Adoption** | Was the defined process actually followed? |
| **Practice** | Were good engineering practices used? |
| **Constraints** | What organizational factors affected the work? |
| **Communication** | Were there communication bottlenecks? |
| **Introspection** | Did the team reflect on the process? |
| **Learning** | How did new team members onboard? |
| **Tool Support** | Were tools effective and adequate? |

### Phase 4: Improvement Identification

Identify potential improvements based on analysis:

```markdown
## Identified Improvements

### Category: [Process/Practice/Tool/Communication]

**Issue**: [What was problematic]
**Evidence**: [Data/observations supporting this]
**Proposed Improvement**: [Specific change to make]
**Expected Benefit**: [What will improve]
**Effort**: [Low/Medium/High]
```

### Phase 5: Prioritization

Prioritize improvements using:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Impact** | High | How much will it improve outcomes? |
| **Effort** | Medium | How hard is it to implement? |
| **Risk** | Medium | What could go wrong? |
| **Urgency** | Low | How soon is it needed? |

Priority matrix:

```
                    Impact
              Low         High
        ┌───────────┬───────────┐
  Low   │  Maybe    │  Quick    │
Effort  │  Later    │  Win      │
        ├───────────┼───────────┤
  High  │  Avoid    │  Plan     │
        │           │  Carefully│
        └───────────┴───────────┘
```

### Phase 6: Action Items

Create concrete action items:

```markdown
## Action Items

### Priority 1: [Quick Wins]
- [ ] Action: [Specific task]
  - Owner: [Who]
  - Deadline: [When]
  - Success Criteria: [How to verify]

### Priority 2: [Planned Improvements]
- [ ] Action: [Specific task]
  - Owner: [Who]
  - Deadline: [When]
  - Dependencies: [What needs to happen first]

### Priority 3: [For Later Consideration]
- [ ] [Improvement to revisit in future retrospective]
```

### Phase 7: Documentation

Document the retrospective:

```markdown
## Retrospective Record

**Date**: YYYY-MM-DD
**Scope**: [Feature/Sprint/Project name]
**Participants**: [Who was involved]

### What Went Well
1. [Positive outcome]
2. [Positive outcome]

### What Could Be Improved
1. [Issue identified]
2. [Issue identified]

### Key Metrics
| Metric | Value | Baseline | Trend |
|--------|-------|----------|-------|
| [metric] | [value] | [previous] | [↑/↓/→] |

### Action Items Summary
| Action | Owner | Priority | Status |
|--------|-------|----------|--------|
| [action] | [owner] | [P1/P2/P3] | [pending] |

### Lessons Learned
1. [Key insight]
2. [Key insight]
```

---

## GQM Framework

Reference: `checklists/gqm-framework.md`

Use Goal-Question-Metric to guide measurement:

```
┌─────────────────────────────────────────┐
│           Goals to Achieve              │
│  (What the organization wants)          │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌───────┐   ┌───────┐   ┌───────┐
│  Q1   │   │  Q2   │   │  Q3   │  Questions
└───┬───┘   └───┬───┘   └───┬───┘  (What we need to know)
    │           │           │
    ▼           ▼           ▼
┌───────┐   ┌───────┐   ┌───────┐
│  M1   │   │  M2   │   │  M3   │  Metrics
└───────┘   └───────┘   └───────┘  (What we measure)
```

Example:
- **Goal**: Reduce defects found in production
- **Question**: Where do defects originate in our process?
- **Metric**: Defects by phase (design, coding, testing)

---

## Process Attributes to Consider

When analyzing process quality, consider these attributes:

| Attribute | Question |
|-----------|----------|
| Understandability | Is the process easy to understand? |
| Standardization | Is it consistently applied? |
| Visibility | Can progress be observed? |
| Measurability | Can outcomes be measured? |
| Supportability | Do tools support the process? |
| Acceptability | Do people accept and use it? |
| Reliability | Does it prevent errors? |
| Robustness | Does it handle unexpected problems? |
| Maintainability | Can it evolve with needs? |
| Rapidity | How fast can it be completed? |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Problematic |
|--------------|---------------------|
| Blame game | Focus on process, not people |
| Too many changes | Hard to assess effectiveness |
| No metrics | Can't verify improvement |
| No follow-up | Changes don't persist |
| Skipping training | People don't adopt changes |

---

## Output Format

```markdown
# Retrospective: [Scope Name]

**Date**: YYYY-MM-DD
**Period**: [Start] to [End]

## Summary

[One paragraph overview of the retrospective scope and key findings]

## Metrics Collected

| Category | Metric | Value | Notes |
|----------|--------|-------|-------|
| Time | Total duration | X days | |
| Time | Active dev time | Y days | |
| Quality | Defects found | N | During [phase] |
| Quality | Rework incidents | M | |

## Analysis

### What Went Well
1. [Positive]
2. [Positive]

### What Could Be Improved
1. [Issue] - [Evidence]
2. [Issue] - [Evidence]

### Root Causes
- [Issue] → [Root cause]

## Improvements

### Quick Wins (Do Now)
| Improvement | Owner | Effort |
|-------------|-------|--------|
| [action] | [who] | Low |

### Planned (Next Sprint/Phase)
| Improvement | Owner | Effort |
|-------------|-------|--------|
| [action] | [who] | Medium |

### Backlog (Future Consideration)
- [improvement for later]

## Lessons Learned

1. **[Topic]**: [What we learned]
2. **[Topic]**: [What we learned]

## Follow-Up

- Next retrospective scheduled: [date]
- Improvements to verify: [list]
```

---

## Integration with Other Skills

| Situation | Use |
|-----------|-----|
| Identified code quality issues | → rv-refactor |
| Found testing gaps | → rv-tdd, rv-test-add |
| Documentation outdated | → rv-docs-sync |
| Process risks identified | → rv-risk |
