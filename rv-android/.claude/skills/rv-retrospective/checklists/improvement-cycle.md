# Process Improvement Cycle

The Measure-Analyze-Change cycle for continuous process improvement.

---

## The Cycle

```
         ┌──────────────────────────────────────┐
         │                                      │
         ▼                                      │
    ┌─────────┐                                 │
    │ MEASURE │ ◄── Collect data on process    │
    │         │     and product attributes     │
    └────┬────┘                                 │
         │                                      │
         ▼                                      │
    ┌─────────┐                                 │
    │ ANALYZE │ ◄── Identify weaknesses        │
    │         │     and bottlenecks            │
    └────┬────┘                                 │
         │                                      │
         ▼                                      │
    ┌─────────┐                                 │
    │ CHANGE  │ ◄── Implement improvements     │
    │         │     and collect new data       │
    └────┬────┘                                 │
         │                                      │
         └──────────────────────────────────────┘
```

---

## Phase 1: Measure

### Purpose
Collect quantitative data about the process and products to establish baselines and track improvements.

### Three Types of Process Metrics

| Type | Description | Examples |
|------|-------------|----------|
| **Time Metrics** | Duration of process activities | Time to complete testing, calendar days to release |
| **Resource Metrics** | Resources consumed | Person-days effort, tool costs, compute resources |
| **Event Metrics** | Count of occurrences | Defects found, change requests, rework incidents |

### Measurement Collection

```markdown
## Measurement Record

### Time Metrics
| Activity | Start | End | Duration | Notes |
|----------|-------|-----|----------|-------|
| Requirements | [date] | [date] | [days] | |
| Design | [date] | [date] | [days] | |
| Implementation | [date] | [date] | [days] | |
| Testing | [date] | [date] | [days] | |
| Review/Rework | [date] | [date] | [days] | |

**Total Calendar Time**: [X days]
**Total Active Time**: [Y days]
**Wait/Block Time**: [Z days]

### Resource Metrics
| Resource | Planned | Actual | Variance |
|----------|---------|--------|----------|
| Person-days | [X] | [Y] | [+/-Z] |
| External costs | [$X] | [$Y] | [+/-$Z] |

### Event Metrics
| Event | Count | Rate | Notes |
|-------|-------|------|-------|
| Commits | [N] | [per day] | |
| Code reviews | [N] | | |
| Defects (dev) | [N] | [per KLOC] | Found during development |
| Defects (test) | [N] | [per KLOC] | Found during testing |
| Defects (prod) | [N] | [per KLOC] | Found in production |
| Change requests | [N] | | |
| Rework incidents | [N] | | |
```

### Measurement Best Practices

- [ ] Collect data consistently
- [ ] Define metrics before starting (not after)
- [ ] Automate collection where possible
- [ ] Include both process and product metrics
- [ ] Normalize by size/complexity for comparison
- [ ] Document data collection methodology

---

## Phase 2: Analyze

### Purpose
Assess the process, identify weaknesses and bottlenecks, and understand root causes.

### Analysis Techniques

#### 1. Trend Analysis
Compare metrics over time to identify patterns:

```
Defects per Release
     │
  20 ┤     *
     │   *   *
  15 ┤ *       *
     │           *
  10 ┤             *
     │
   5 ┤
     └───────────────────
       R1  R2  R3  R4  R5
```

#### 2. Pareto Analysis
Identify the 20% of causes responsible for 80% of problems:

```markdown
## Defect Source Analysis

| Source | Count | Cumulative % |
|--------|-------|--------------|
| Requirements unclear | 15 | 30% |
| Integration issues | 12 | 54% |
| Logic errors | 8 | 70% |
| Data handling | 6 | 82% |
| UI issues | 5 | 92% |
| Other | 4 | 100% |

**Focus Area**: Requirements + Integration = 54% of defects
```

#### 3. Root Cause Analysis
Ask "Why?" repeatedly to find root causes:

```markdown
## 5 Whys Analysis

**Problem**: High defect rate in integration testing

1. Why? → Components didn't work together
2. Why? → Interfaces weren't clearly defined
3. Why? → Design documents were incomplete
4. Why? → Time pressure to start coding
5. Why? → Unrealistic schedule

**Root Cause**: Schedule pressure → Skip design → Integration problems
**Solution**: Ensure adequate design time in schedule
```

### Analysis Output

```markdown
## Analysis Summary

### Process Bottlenecks
| Bottleneck | Impact | Evidence |
|------------|--------|----------|
| [bottleneck] | [what it causes] | [data supporting] |

### Quality Issues
| Issue | Frequency | Root Cause |
|-------|-----------|------------|
| [issue] | [how often] | [why it happens] |

### Efficiency Issues
| Area | Current | Target | Gap |
|------|---------|--------|-----|
| [area] | [metric] | [goal] | [difference] |
```

---

## Phase 3: Change

### Purpose
Introduce process changes to address identified weaknesses.

### Change Process

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Identify   │   │  Prioritize  │   │  Introduce   │
│ Improvements │ → │ Improvements │ → │   Changes    │
└──────────────┘   └──────────────┘   └──────────────┘
        │                                    │
        │          ┌──────────────┐          │
        │          │    Train     │          │
        └─────────►│  Engineers   │◄─────────┘
                   └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │    Tune      │
                   │   Changes    │
                   └──────────────┘
```

### 1. Identify Improvements

```markdown
## Improvement Proposals

### Proposal 1: [Name]
- **Problem Addressed**: [What issue this solves]
- **Proposed Change**: [What to do differently]
- **Expected Benefit**: [What will improve]
- **Evidence Base**: [Data supporting this change]
```

### 2. Prioritize Improvements

```markdown
## Prioritization Matrix

| Improvement | Impact | Effort | Risk | Priority |
|-------------|--------|--------|------|----------|
| [change 1] | High | Low | Low | **P1** |
| [change 2] | High | High | Med | **P2** |
| [change 3] | Med | Low | Low | **P2** |
| [change 4] | Low | High | High | **Defer** |
```

**Decision Criteria:**
- Impact: How much will it improve outcomes?
- Effort: How hard to implement?
- Risk: What could go wrong?

### 3. Introduce Changes

```markdown
## Change Implementation Plan

### Change: [Name]
- **Scope**: [What/who is affected]
- **Timeline**: [When it will be implemented]
- **Pilot**: [Where to test first, if applicable]
- **Rollout**: [How to deploy broadly]
- **Rollback**: [How to revert if needed]
```

### 4. Train Engineers

```markdown
## Training Plan

### Training Needed
| Topic | Audience | Format | Duration |
|-------|----------|--------|----------|
| [topic] | [who] | [workshop/doc/video] | [time] |

### Training Materials
- [ ] Documentation created/updated
- [ ] Training session scheduled
- [ ] Reference materials available
```

### 5. Tune Changes

After introduction, allow time for adjustment:

```markdown
## Change Tuning Record

### Change: [Name]
**Introduced**: [Date]
**Tuning Period**: [Duration]

### Feedback Collected
| Source | Feedback | Action Taken |
|--------|----------|--------------|
| [who] | [what they said] | [adjustment made] |

### Adjustments Made
1. [Adjustment and reason]
2. [Adjustment and reason]

### Final State
- Change adopted: [Yes/No/Modified]
- Effectiveness: [Assessment]
```

---

## Change Management Best Practices

### Do
- [ ] Involve affected people in planning
- [ ] Introduce changes incrementally
- [ ] Allow time for tuning
- [ ] Measure effectiveness
- [ ] Communicate clearly

### Don't
- [ ] Impose changes without buy-in
- [ ] Introduce too many changes at once
- [ ] Skip training
- [ ] Expect immediate results
- [ ] Abandon changes too quickly

---

## Cycle Cadence

| Scope | Measurement | Analysis | Change |
|-------|-------------|----------|--------|
| Feature | Per feature | After feature | Before next feature |
| Sprint | Weekly | End of sprint | Next sprint |
| Project | Monthly | Quarterly | Continuous |

---

## Checklist

Before completing an improvement cycle:

- [ ] Metrics collected with consistent methodology
- [ ] Analysis based on data, not just opinions
- [ ] Root causes identified (not just symptoms)
- [ ] Changes prioritized by impact and effort
- [ ] Affected people involved in planning
- [ ] Training planned and delivered
- [ ] Tuning period allowed
- [ ] Effectiveness measured
- [ ] Lessons documented for future cycles
