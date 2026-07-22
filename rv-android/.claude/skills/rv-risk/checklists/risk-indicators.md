# Risk Indicators

Monitoring indicators to detect when risks are materializing.

---

## Purpose

Risk indicators are measurable factors that signal when a risk is becoming more likely or when a risk has started to materialize. Regular monitoring of these indicators enables early intervention.

---

## Indicators by Risk Type

### Technology Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Hardware/software delivery | On schedule | < 1 week late | > 1 week late |
| Technology problems reported | 0-1 per week | 2-5 per week | > 5 per week |
| Workarounds implemented | 0 | 1-2 | > 2 |
| Performance test results | Meets requirements | Within 20% | Fails requirements |
| Dependency vulnerabilities | None critical | Low/Medium only | High/Critical |
| API stability | No breaking changes | Deprecation warnings | Breaking changes |

**What to watch**:
- Late delivery of hardware or support software
- Many reported technology problems
- Team working around technology limitations
- Prototype/POC not meeting expectations

### People Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Team morale | High | Mixed | Low |
| Turnover | 0% | 1 person considering | Person leaving |
| Attendance | Full attendance | Occasional absences | Frequent absences |
| Communication | Open, frequent | Reduced | Minimal/conflict |
| Overtime | None/rare | Occasional | Frequent/required |
| Skills coverage | Redundant | Single expert | No expert |

**What to watch**:
- Poor staff morale
- Poor relationships amongst team members
- High staff turnover
- Resistance to change
- Complaints about workload

### Organizational Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Management attention | Regular engagement | Reduced engagement | No engagement |
| Budget status | Approved | Under review | Cut/threatened |
| Organizational news | Stable | Rumors | Announced changes |
| Priority ranking | Top priority | Competing priorities | Deprioritized |
| Sponsor availability | Always available | Sometimes available | Rarely available |

**What to watch**:
- Organizational gossip about changes
- Lack of action by senior management
- Delayed approvals
- Budget review meetings
- Sponsor reassignment

### Tools Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Tool satisfaction | High | Mixed | Low |
| Tool complaints | None | Occasional | Frequent |
| Workarounds needed | 0 | 1-2 | > 2 |
| Hardware requests | None | Performance complaints | Upgrade demands |
| Integration issues | None | Minor | Blocking |

**What to watch**:
- Reluctance by team to use tools
- Complaints about CASE tools
- Demands for higher-powered workstations
- Manual workarounds for tool limitations

### Requirements Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Change requests | < 2/sprint | 2-5/sprint | > 5/sprint |
| Customer complaints | None | Occasional | Frequent |
| Requirements clarity | Clear | Some ambiguity | Major confusion |
| Scope creep | None | Minor additions | Significant growth |
| Stakeholder alignment | Aligned | Minor disagreements | Major conflicts |

**What to watch**:
- Many requirements change requests
- Customer complaints
- Disagreements between stakeholders
- "That's not what I meant" feedback
- Scope growing without schedule adjustment

### Estimation Risk Indicators

| Indicator | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Schedule adherence | On track | < 10% behind | > 10% behind |
| Defect backlog | Decreasing | Stable | Increasing |
| Velocity trend | Stable/improving | Declining | Significantly declining |
| Completed vs planned | > 90% | 70-90% | < 70% |
| Rework rate | < 10% | 10-25% | > 25% |

**What to watch**:
- Failure to meet agreed schedule
- Failure to clear reported defects
- Estimates consistently wrong
- Team velocity declining
- Increasing technical debt

---

## Monitoring Process

### Weekly Risk Check

Quick check of key indicators:

1. **Review dashboards/metrics**
   - Build status
   - Test results
   - Velocity charts
   - Bug counts

2. **Team pulse check**
   - How are people feeling?
   - Any blockers?
   - Any concerns?

3. **External factors**
   - Any organizational news?
   - Any dependency updates?
   - Any customer feedback?

### Sprint/Milestone Review

Deeper risk assessment:

1. **Review all risk indicators**
2. **Update risk register**
   - New risks identified?
   - Probability changes?
   - Effect changes?
3. **Evaluate mitigation effectiveness**
4. **Adjust plans as needed**

### Escalation Triggers

When to escalate to stakeholders:

| Condition | Action |
|-----------|--------|
| Critical risk materializing | Immediate escalation |
| Multiple Yellow indicators | Review with team lead |
| Any Red indicator | Escalate to sponsor |
| Trend worsening | Proactive notification |
| Mitigation failing | Request additional resources |

---

## Indicator Dashboard Template

```markdown
# Risk Indicators Dashboard

**Date**: [date]
**Sprint**: [number]

## Summary
| Risk Type | Status | Trend |
|-----------|--------|-------|
| Technology | 🟢/🟡/🔴 | ↑/→/↓ |
| People | 🟢/🟡/🔴 | ↑/→/↓ |
| Organizational | 🟢/🟡/🔴 | ↑/→/↓ |
| Tools | 🟢/🟡/🔴 | ↑/→/↓ |
| Requirements | 🟢/🟡/🔴 | ↑/→/↓ |
| Estimation | 🟢/🟡/🔴 | ↑/→/↓ |

## Key Metrics
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Build success rate | X% | > 95% | 🟢/🟡/🔴 |
| Test pass rate | X% | > 90% | 🟢/🟡/🔴 |
| Change requests | X | < 5 | 🟢/🟡/🔴 |
| Velocity | X pts | Y pts | 🟢/🟡/🔴 |
| Defect backlog | X bugs | < Y | 🟢/🟡/🔴 |

## Concerns
- [concern 1]
- [concern 2]

## Actions
- [ ] [action item]
- [ ] [action item]
```

---

## Early Warning Signs

### Technology
- Prototypes not working as expected
- Team avoiding certain technologies
- Excessive time spent on infrastructure

### People
- Increased sick days
- Reduced participation in meetings
- Decreased code review quality

### Organizational
- Delayed responses from management
- Budget questions
- Priority discussions

### Tools
- Shadow IT (unofficial tools)
- Manual processes replacing automation
- Frequent tool crashes

### Requirements
- "Just one more thing"
- Stakeholder absence from meetings
- Conflicting feedback

### Estimation
- "We just need a bit more time"
- Scope negotiations every sprint
- Always 90% complete
