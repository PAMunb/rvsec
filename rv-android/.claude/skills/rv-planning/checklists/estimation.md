# Estimation Guidelines

Techniques for estimating task effort with appropriate uncertainty handling.

---

## Estimation Philosophy

### Key Principles

1. **Estimates are not commitments** - They are informed guesses based on current knowledge
2. **Uncertainty decreases over time** - Early estimates are less accurate
3. **Contingency is essential** - Always add buffer for unknowns
4. **Track and calibrate** - Compare estimates to actuals for improvement

### The Cone of Uncertainty

```
Project Start ──────► Project End

     ▲
  4x │  ████
     │  ████
  2x │  ████████
     │  ████████████
  1x │  ████████████████
     │  ████████████████████
0.5x │  ████████████████████████
     │  ████████████████████████████
0.25x│  ████████████████████████████████
     └──────────────────────────────────►
       Initial  Detailed  Iteration  Task
       Concept  Planning  Start      Start
```

Early estimates may be off by 4x; detailed task estimates are more accurate.

---

## Estimation Techniques

### 1. Analogy-Based

Compare to similar tasks done before.

**When to use**: Task resembles past work

**Process**:
1. Find similar past task
2. Note how long it took
3. Adjust for differences
4. Apply to current task

**Example**:
```
"Adding auth middleware" ~ "Adding logging middleware" (3 min)
Difference: Auth is slightly more complex
Estimate: 4 min base
```

### 2. Decomposition-Based

Sum estimates of subtasks.

**When to use**: Task is too large to estimate directly

**Process**:
1. Break into smaller tasks
2. Estimate each subtask
3. Sum estimates
4. Add coordination overhead (10-20%)

**Example**:
```
Add user endpoint:
- Repository function: 2 min
- Service function: 3 min
- Route handler: 2 min
- Tests: 4 min
Subtotal: 11 min
Coordination: +10% = 1 min
Estimate: 12 min base
```

### 3. Expert Judgment

Ask someone with experience.

**When to use**: Unfamiliar territory

**Process**:
1. Describe the task clearly
2. Ask experienced developer
3. Document their reasoning
4. Use as reference

**Caveat**: Experts often underestimate because they forget learning time.

### 4. Historical Data

Use past performance metrics.

**When to use**: Have tracked data from similar work

**Process**:
1. Look up similar past tasks
2. Note actual completion time
3. Adjust for current context
4. Apply with confidence level

---

## Contingency Factors

### Purpose of Contingency

Contingency accounts for:
- Unknown unknowns
- Context switching
- Clarification time
- Debugging
- Rework

### Contingency by Risk Level

| Risk Level | Contingency | Reasoning |
|------------|-------------|-----------|
| **Low** | +30% | Routine, well-understood task |
| **Medium** | +40% | Some unknowns, may need adjustment |
| **High** | +50% | Significant uncertainty, may pivot |
| **Very High** | +100% | Experimental, research-like |

### Contingency Application

```
Base estimate: 10 min
Risk level: Medium (+40%)
Contingency: 4 min
Total estimate: 14 min
```

### When to Increase Contingency

Add extra contingency when:
- First time doing this type of task
- Dependencies on external systems
- Integration with unfamiliar code
- Tight coupling with other tasks
- Multiple stakeholders involved

---

## Common Estimation Pitfalls

### 1. Planning Fallacy

**Problem**: Underestimating due to optimism

**Fix**: Use "reference class forecasting" - base on similar past projects, not this one's specifics

### 2. Forgetting Overhead

**Problem**: Only estimating coding time

**Include**:
- Reading and understanding existing code
- Testing the change
- Debugging issues
- Code review time
- Documentation updates

### 3. Anchoring

**Problem**: First number heard dominates thinking

**Fix**: Estimate independently before discussing with others

### 4. Scope Creep in Estimates

**Problem**: Task grows during estimation

**Fix**: Note assumptions; anything not in assumptions is out of scope

---

## Estimation Template

### Per-Task Estimation

```markdown
### Task: [Name]

**Base Estimate**: X min
**Assumptions**:
- [Assumption 1]
- [Assumption 2]

**Risk Level**: Low/Medium/High
**Contingency**: +X%
**Total Estimate**: Y min

**Confidence**: Low/Medium/High
```

### Project Summary

```markdown
## Estimation Summary

| Task | Base | Risk | Contingency | Total |
|------|------|------|-------------|-------|
| Task 1 | 3 min | Low | +30% | 4 min |
| Task 2 | 5 min | Med | +40% | 7 min |
| Task 3 | 8 min | High | +50% | 12 min |
| **Sum** | 16 min | | | 23 min |

**Overall Confidence**: Medium
**Assumptions**:
- Codebase is stable during implementation
- No blocking questions requiring stakeholder input
```

---

## Estimation Calibration

### Track Actuals

After completing tasks, record:

```markdown
| Task | Estimated | Actual | Ratio |
|------|-----------|--------|-------|
| Task 1 | 4 min | 5 min | 1.25 |
| Task 2 | 7 min | 6 min | 0.86 |
| Task 3 | 12 min | 15 min | 1.25 |
```

### Analyze Patterns

Over time, look for:
- Consistent over/underestimation
- Task types that are harder to estimate
- Risk categories that need more contingency

### Adjust Future Estimates

If consistently off by 20%:
- Apply 20% correction factor
- Or increase contingency percentage

---

## Special Cases

### First-Time Tasks

When doing something for the first time:

```markdown
**Estimate approach**:
1. Find analogous task: X min
2. Add learning curve: +50%
3. Add integration discovery: +25%
4. Apply standard contingency: +40%

Total multiplier: ~2.1x the analogous task
```

### Research/Spike Tasks

For exploratory work:

```markdown
**Approach**: Time-box instead of estimate

"Investigate authentication options"
Time-box: 30 min
Deliverable: Decision document with pros/cons
```

### Bug Fixes

For debugging work:

```markdown
**Approach**: Estimate diagnosis separately

"Fix user creation bug"
- Diagnosis: 10 min (high uncertainty)
- Fix (once found): 3 min (low uncertainty)
Total: 13 min + 50% = ~20 min
```

---

## Checklist

Before finalizing estimates:

- [ ] Each task has base estimate
- [ ] Assumptions documented
- [ ] Risk level assigned
- [ ] Appropriate contingency added
- [ ] Special cases handled (first-time, spike, bug)
- [ ] Total adds up correctly
- [ ] Confidence level stated
- [ ] Ready to track actuals
