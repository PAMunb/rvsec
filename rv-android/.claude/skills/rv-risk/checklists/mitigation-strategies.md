# Mitigation Strategies

Risk response strategies: avoidance, minimization, and contingency planning.

---

## Strategy Types

| Strategy | Goal | When to Use |
|----------|------|-------------|
| **Avoidance** | Eliminate the risk entirely | Risk can be prevented by changing approach |
| **Minimization** | Reduce probability or impact | Risk cannot be fully avoided |
| **Contingency** | Prepare response if risk occurs | Risk is likely or consequences are severe |

The best approach uses all three strategies in combination.

---

## Avoidance Strategies

Avoidance eliminates the risk by changing the project approach.

### Technology Avoidance

| Risk | Avoidance Strategy |
|------|---------------------|
| New technology performance | Use proven technology; benchmark before committing |
| Dependency instability | Use stable versions; avoid bleeding edge |
| Integration complexity | Choose technologies that integrate well |
| Single vendor lock-in | Use open standards; abstract vendor-specific code |

### People Avoidance

| Risk | Avoidance Strategy |
|------|---------------------|
| Skill shortage | Hire contractors; train existing staff early |
| Single point of failure | Cross-train from project start |
| Team conflicts | Careful team selection; define roles clearly |

### Requirements Avoidance

| Risk | Avoidance Strategy |
|------|---------------------|
| Scope creep | Fixed scope contracts; clear change process |
| Unclear requirements | Prototype early; iterative refinement |
| Conflicting requirements | Stakeholder alignment sessions early |

### Estimation Avoidance

| Risk | Avoidance Strategy |
|------|---------------------|
| Underestimation | Use historical data; add contingency |
| Complexity surprise | Prototype complex areas first |
| Integration time | Integrate continuously from start |

---

## Minimization Strategies

Minimization reduces either the probability or the impact of a risk.

### Reducing Probability

| Risk | Minimization Strategy |
|------|------------------------|
| Staff turnover | Competitive compensation; good work environment |
| Technology failure | Early prototyping; expert review |
| Requirements change | Regular customer contact; iterative development |
| Defects | Code reviews; automated testing; pair programming |

### Reducing Impact

| Risk | Minimization Strategy |
|------|------------------------|
| Staff turnover | Documentation; knowledge sharing; pair programming |
| Technology failure | Modular design; abstraction layers |
| Requirements change | Information hiding; flexible architecture |
| Schedule slip | Phased delivery; prioritized features |

### Common Minimization Patterns

**Documentation and Knowledge Sharing**:
- Maintain up-to-date documentation
- Pair programming and code reviews
- Regular knowledge transfer sessions
- ADRs (Architecture Decision Records)

**Modular and Flexible Design**:
- Information hiding
- Clear interfaces
- Dependency injection
- Feature flags

**Continuous Verification**:
- Automated testing
- Continuous integration
- Regular performance testing
- Early integration

---

## Contingency Strategies

Contingency planning prepares responses for when risks occur.

### Contingency Plan Components

1. **Trigger**: When is the contingency activated?
2. **Response**: What immediate actions to take?
3. **Owner**: Who is responsible?
4. **Resources**: What is needed to respond?
5. **Communication**: Who needs to be informed?

### Common Contingency Plans

| Risk | Contingency Plan |
|------|------------------|
| Key staff leaves | Backup developer identified; documentation ready |
| Budget cut | Prioritized feature list; scope reduction plan |
| Technology fails | Alternative technology evaluated; migration path |
| Schedule slip | Overtime authorization; scope negotiation ready |
| Vendor failure | Alternative vendor identified; data export ready |

### Contingency Plan Template

```markdown
## Contingency Plan: [Risk Name]

### Trigger
[What event activates this plan?]

### Immediate Response (First 24 hours)
1. [Action item]
2. [Action item]
3. [Action item]

### Short-term Response (First week)
1. [Action item]
2. [Action item]

### Long-term Response
1. [Action item]

### Owner
[Person responsible for executing this plan]

### Resources Required
- [Resource 1]
- [Resource 2]

### Communication Plan
| Stakeholder | When | How | Message |
|-------------|------|-----|---------|
| [name] | Immediately | Call | [brief] |
| [name] | Within 24h | Email | [brief] |

### Success Criteria
[How do we know the contingency worked?]
```

---

## Strategy Selection Guide

### Use Avoidance When:
- Risk can be eliminated by changing approach
- Cost of change is less than cost of risk
- Alternative approach is viable
- Early in project (more flexibility)

### Use Minimization When:
- Risk cannot be fully avoided
- Reducing probability is feasible
- Reducing impact is valuable
- Multiple small actions help

### Use Contingency When:
- Risk is likely to occur
- Consequences are severe
- Fast response is needed
- Can prepare in advance

---

## Example Risk Strategies

### Staff Turnover

**Avoidance**:
- Hire contractors as backup
- Avoid over-reliance on any individual

**Minimization**:
- Cross-training and pair programming
- Documentation and knowledge sharing
- Good work environment

**Contingency**:
- Identified backup for each critical role
- Knowledge base maintained
- Handover process defined

### Requirements Changes

**Avoidance**:
- Clear change management process
- Fixed scope for current iteration
- Stakeholder alignment early

**Minimization**:
- Information hiding in design
- Flexible architecture
- Traceability maintained

**Contingency**:
- Impact assessment process
- Scope negotiation templates
- Prioritization criteria defined

### Technology Performance

**Avoidance**:
- Benchmark before committing
- Use proven technologies
- Expert review of architecture

**Minimization**:
- Performance testing throughout
- Monitoring and alerting
- Optimization budget in schedule

**Contingency**:
- Alternative technology identified
- Migration path understood
- Performance degradation plan

### Budget Reduction

**Avoidance**:
- Strong business case
- Executive sponsorship
- Regular value demonstration

**Minimization**:
- Phased delivery approach
- Prioritized feature list
- Efficient processes

**Contingency**:
- Scope reduction options prepared
- Briefing document ready
- Alternative funding sources identified

---

## Strategy Effectiveness Review

### Questions to Ask

For each strategy:

1. **Is it actionable?**
   - Can we actually do this?
   - Do we have the resources?

2. **Is it timely?**
   - Will it be ready when needed?
   - Is there lead time required?

3. **Is it sufficient?**
   - Will it address the risk adequately?
   - Do we need additional strategies?

4. **Is it monitored?**
   - How do we know if it's working?
   - What are the indicators?

### Review Checklist

- [ ] Each key risk has at least one strategy
- [ ] Strategies are documented and shared
- [ ] Owners are assigned
- [ ] Resources are allocated
- [ ] Triggers are defined for contingencies
- [ ] Effectiveness is being monitored
