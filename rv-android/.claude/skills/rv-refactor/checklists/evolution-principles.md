# Software Evolution Principles

Fundamental laws and principles of software evolution that inform refactoring decisions.

---

## Lehman's Laws of Software Evolution

Empirically derived principles about how large software systems evolve over time.

### The 8 Laws

| Law | Name | Description |
|-----|------|-------------|
| 1 | Continuing Change | A system must be continually adapted or it becomes progressively less useful |
| 2 | Increasing Complexity | As a system evolves, its complexity increases unless work is done to maintain or reduce it |
| 3 | Self Regulation | System evolution is a self-regulating process with statistically determinable trends |
| 4 | Conservation of Stability | The rate of development is approximately constant over the system's lifetime |
| 5 | Conservation of Familiarity | Incremental changes in each release are approximately constant |
| 6 | Continuing Growth | Functionality must continually increase to maintain user satisfaction |
| 7 | Declining Quality | Quality will decline unless rigorously maintained and adapted |
| 8 | Feedback System | Evolution processes are multi-level feedback systems |

---

## Implications for Refactoring

### Law 1: Continuing Change

**Implication**: Systems that don't evolve become obsolete.

**Action**:
- [ ] Regularly assess system against current requirements
- [ ] Budget for continuous improvement
- [ ] Don't just fix bugs - improve the system

---

### Law 2: Increasing Complexity

**Implication**: Every change tends to degrade structure.

**Action**:
- [ ] Invest in preventative maintenance (refactoring)
- [ ] Simplify structure during every change
- [ ] Don't let complexity accumulate
- [ ] Track complexity metrics over time

**Signs of structural degradation**:
- Changes take longer than expected
- Bug fixes create new bugs
- Same areas keep breaking
- Team avoids touching certain code

---

### Law 3: Self Regulation

**Implication**: Large systems have their own dynamics.

**Action**:
- [ ] Accept that change rate is constrained
- [ ] Plan for realistic change increments
- [ ] Don't try to change everything at once

---

### Law 5: Conservation of Familiarity

**Implication**: Too much change at once increases risk.

**Action**:
- [ ] Keep changes incremental
- [ ] Maintain team's ability to understand code
- [ ] Large functionality additions → expect bug fix releases
- [ ] Plan time for stabilization after major changes

---

### Law 7: Declining Quality

**Implication**: Quality erodes naturally unless actively maintained.

**Action**:
- [ ] Regular refactoring (preventative maintenance)
- [ ] Continuous testing
- [ ] Monitor quality metrics
- [ ] Address technical debt proactively

---

## Software Evolution Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Initial         Evolution         Servicing        Phaseout   │
│  Development                                                    │
│                                                                 │
│  ────────────► ────────────────► ────────────────► ──────────►  │
│                                                                 │
│  • New system   • Active changes   • Bug fixes only   • No more │
│  • Architecture • Architecture     • Minimal changes    changes │
│    defined        evolves          • System stable    • End of  │
│  • Features     • Features added   • Replacement        life    │
│    implemented  • Structure may      planned                    │
│                   degrade                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase Identification Checklist

**Evolution Phase** (active development):
- [ ] Significant new features being added
- [ ] Architecture changes are acceptable
- [ ] Active user base with change requests
- [ ] Investment in the system continues

**Servicing Phase** (maintenance mode):
- [ ] Only bug fixes and critical updates
- [ ] Avoiding structural changes
- [ ] Changes are expensive/risky
- [ ] Replacement being considered

**Implication**: Know which phase you're in before refactoring.

---

## When to Refactor vs When to Reengineer

### Refactoring (Small, Continuous Improvements)

**Characteristics**:
- Preserves external behavior
- Small, incremental changes
- Low risk
- Continuous process

**Use When**:
- [ ] Code works but is hard to change
- [ ] Adding features to existing system
- [ ] Preventing structural degradation
- [ ] During active evolution phase

**Examples**:
- Extract method
- Rename variable
- Remove duplication
- Simplify conditionals

---

### Reengineering (Major Restructuring)

**Characteristics**:
- May change behavior
- Large-scale changes
- Higher risk
- One-time effort

**Use When**:
- [ ] Structure too degraded for incremental improvement
- [ ] Technology platform needs to change
- [ ] Architecture fundamentally flawed
- [ ] Cost of maintenance exceeds reengineering cost

**Activities**:
- Source code translation
- Reverse engineering
- Program structure improvement
- Program modularization
- Data reengineering

---

## Decision Matrix

| Situation | Approach | Skill |
|-----------|----------|-------|
| Code works, hard to read | Refactor | /rv-refactor |
| Adding new feature | Refactor + Feature | /rv-feature |
| Bug fixes take too long | Refactor | /rv-refactor |
| Technology obsolete | Reengineer | Manual |
| Architecture wrong | Reengineer | Manual |
| System in servicing phase | Minimal changes | /rv-cleanup |
| Dead code accumulated | Cleanup | /rv-cleanup |

---

## Bad Smells (Indicators for Refactoring)

| Smell | Description | Solution |
|-------|-------------|----------|
| Duplicate code | Same/similar code in multiple places | Extract method/class |
| Long methods | Methods > 50 lines | Extract method |
| Large classes | Classes > 500 lines | Extract class |
| Switch statements | Type-based switch/case | Polymorphism |
| Data clumping | Same data always together | Create object |
| Speculative generality | Unused abstractions | Remove unused code |
| Feature envy | Method uses other class's data | Move method |
| Inappropriate intimacy | Classes too tightly coupled | Move/extract |

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────┐
│           EVOLUTION PRINCIPLES                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  KEY LAWS TO REMEMBER:                                  │
│                                                         │
│  1. Systems MUST change or become useless               │
│  2. Complexity INCREASES unless actively fought         │
│  3. Quality DECLINES unless maintained                  │
│  4. Changes should be INCREMENTAL                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  REFACTOR when:        REENGINEER when:                 │
│  • Code works          • Structure too degraded         │
│  • Small improvements  • Technology change              │
│  • Low risk            • Architecture wrong             │
│  • Evolution phase     • High maintenance cost          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
