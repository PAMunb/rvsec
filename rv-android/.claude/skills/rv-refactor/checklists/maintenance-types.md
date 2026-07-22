# Maintenance Types Checklist

Classification of software maintenance activities based on established software engineering practices.

---

## Three Types of Software Maintenance

```
                    CHANGE REQUEST
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │CORRECTIVE│   │ ADAPTIVE │   │PERFECTIVE│
    │  (Fault  │   │(Environ- │   │(Function │
    │  Repair) │   │  ment)   │   │ Addition)│
    └──────────┘   └──────────┘   └──────────┘
         │              │              │
         ▼              ▼              ▼
      ~17%           ~18%           ~65%
    of effort       of effort      of effort
```

---

## 1. Corrective Maintenance (Fault Repair)

**Purpose**: Fix bugs and errors in the software.

### Characteristics

- **Trigger**: Bug reports, error logs, user complaints
- **Scope**: Usually localized to specific code areas
- **Risk**: Low to medium (targeted fixes)
- **Typical effort**: ~17% of maintenance budget

### Types of Faults

| Level | Description | Cost to Fix |
|-------|-------------|-------------|
| Coding errors | Typos, logic bugs | Low |
| Design errors | May require rewriting components | Medium |
| Requirements errors | May require redesign | High |

### Checklist

- [ ] Bug clearly reproduced and understood
- [ ] Root cause identified (not just symptoms)
- [ ] Fix is localized (minimal changes)
- [ ] Regression test added
- [ ] No new issues introduced

### Skill to Use

**Use `/rv-tdd`** for corrective maintenance with test-driven fixes.

---

## 2. Adaptive Maintenance (Environmental Adaptation)

**Purpose**: Modify software to work in new/changed environment.

### Characteristics

- **Trigger**: Platform changes, dependency updates, new hardware
- **Scope**: May affect multiple system components
- **Risk**: Medium to high (compatibility issues)
- **Typical effort**: ~18% of maintenance budget

### Common Triggers

| Category | Examples |
|----------|----------|
| Platform | OS upgrade, new hardware |
| Runtime | Python version upgrade, JVM update |
| Dependencies | Library deprecation, API changes |
| Infrastructure | Cloud migration, database change |
| Standards | Compliance requirements, security patches |

### Checklist

- [ ] New environment requirements documented
- [ ] Compatibility matrix created
- [ ] Migration path defined
- [ ] Rollback strategy available
- [ ] Testing in new environment complete

### Skill to Use

**Use `/rv-refactor`** for significant architectural adaptations.

---

## 3. Perfective Maintenance (Functionality Addition/Improvement)

**Purpose**: Add new features or improve existing functionality.

### Characteristics

- **Trigger**: New requirements, user feedback, business changes
- **Scope**: Can range from small to large
- **Risk**: Varies by scope
- **Typical effort**: ~65% of maintenance budget (largest!)

### Subtypes

| Subtype | Description | Example |
|---------|-------------|---------|
| Feature addition | New functionality | Add export feature |
| Performance | Improve speed/efficiency | Optimize queries |
| Usability | Better user experience | Simplify workflow |
| Refactoring | Improve structure | Extract module |

### Checklist

- [ ] Requirements clearly defined
- [ ] Impact analysis complete
- [ ] Design reviewed
- [ ] Tests planned (TDD)
- [ ] Documentation updated

### Skill to Use

- **Use `/rv-feature`** for new functionality
- **Use `/rv-refactor`** for structural improvements
- **Use `/rv-tdd`** for feature implementation with tests

---

## Maintenance Type Decision Tree

```
START: Change Request
    │
    ├─ Is it fixing a bug/error?
    │    YES → CORRECTIVE → /rv-tdd
    │    NO → continue
    │
    ├─ Is it adapting to environment change?
    │    YES → ADAPTIVE → /rv-refactor
    │    NO → continue
    │
    └─ Is it adding/improving functionality?
         YES → PERFECTIVE
              │
              ├─ New feature → /rv-feature
              ├─ Structure improvement → /rv-refactor
              └─ Performance → /rv-refactor
```

---

## Maintenance Effort Distribution

Understanding typical effort distribution helps with planning:

| Type | % of Effort | Focus |
|------|-------------|-------|
| **Perfective** | 65% | Adding value |
| **Adaptive** | 18% | Staying current |
| **Corrective** | 17% | Fixing issues |

**Key insight**: Most maintenance is NOT bug fixing. It's adding features and adapting to change.

---

## Cost Factors

Factors that affect maintenance costs:

### Technical Factors

| Factor | Impact on Cost |
|--------|----------------|
| Team stability | Low stability → Higher cost |
| Code quality | Poor quality → Higher cost |
| Documentation | Missing docs → Higher cost |
| Testing | No tests → Higher cost |
| Architecture | Coupled → Higher cost |

### Process Factors

| Factor | Impact on Cost |
|--------|----------------|
| Program understanding | Most expensive part |
| Impact analysis | Critical for estimation |
| Test after change | Essential for quality |
| Documentation update | Often neglected |

---

## Preventative Maintenance

**Definition**: Improving software structure WITHOUT adding functionality.

### Benefits

- Reduces future maintenance costs
- Prevents structural degradation
- Makes future changes easier

### When to Apply

- [ ] Code is getting harder to change
- [ ] Bug fixes take longer than expected
- [ ] Same areas keep breaking
- [ ] New team members struggle to understand

### How to Apply

Use refactoring as preventative maintenance:
- Extract methods to reduce complexity
- Remove duplication
- Simplify conditional logic
- Improve naming

### Skill to Use

**Use `/rv-refactor`** or `/rv-cleanup`** for preventative maintenance.

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────┐
│               MAINTENANCE TYPES                         │
├──────────────┬──────────────────────────────────────────┤
│ CORRECTIVE   │ Fix bugs and errors                      │
│   (17%)      │ → /rv-tdd                                │
├──────────────┼──────────────────────────────────────────┤
│ ADAPTIVE     │ Adapt to environment changes             │
│   (18%)      │ → /rv-refactor                           │
├──────────────┼──────────────────────────────────────────┤
│ PERFECTIVE   │ Add features, improve structure          │
│   (65%)      │ → /rv-feature, /rv-refactor              │
├──────────────┼──────────────────────────────────────────┤
│ PREVENTATIVE │ Improve without new functionality        │
│              │ → /rv-refactor, /rv-cleanup              │
└──────────────┴──────────────────────────────────────────┘
```
