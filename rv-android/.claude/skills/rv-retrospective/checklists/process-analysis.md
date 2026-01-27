# Process Analysis Checklist

Seven key aspects to investigate during process analysis.

---

## Purpose

Process analysis helps understand:
- What is actually happening in the process
- Problems and inefficiencies
- How the process is influenced by organizational factors
- Tool effectiveness and gaps

---

## The 7 Aspects

### 1. Adoption and Standardization

**Key Questions:**
- Is the process documented?
- Is the same process used consistently across the team/organization?
- Do people actually follow the documented process?

**Investigation:**
```markdown
## Adoption Analysis

### Process Documentation
- [ ] Process is documented: [Yes/No/Partially]
- [ ] Documentation is up-to-date: [Yes/No]
- [ ] Documentation is accessible: [Yes/No]

### Consistency
- [ ] Process followed by all team members: [Yes/No/Varies]
- [ ] Local variations identified: [List]
- [ ] Variations beneficial or problematic: [Assessment]

### Compliance
- Estimated compliance rate: [X%]
- Areas with lowest compliance: [List]
- Reasons for non-compliance: [List]
```

---

### 2. Software Engineering Practice

**Key Questions:**
- Are known good practices being used?
- What practices are missing?
- How do missing practices affect outcomes?

**Investigation:**
```markdown
## Practice Analysis

### Practices in Use
| Practice | Status | Effectiveness |
|----------|--------|---------------|
| Code review | Used/Partial/Not used | [Rating] |
| Automated testing | Used/Partial/Not used | [Rating] |
| CI/CD | Used/Partial/Not used | [Rating] |
| Documentation | Used/Partial/Not used | [Rating] |

### Missing Practices
| Practice | Why Missing | Impact |
|----------|-------------|--------|
| [practice] | [reason] | [impact on quality/time] |

### Practice Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

### 3. Organizational Constraints

**Key Questions:**
- What organizational factors affect the process?
- Are there external requirements or standards to follow?
- What constraints limit process changes?

**Investigation:**
```markdown
## Constraints Analysis

### External Constraints
- Regulatory requirements: [List]
- Customer requirements: [List]
- Industry standards: [List]

### Internal Constraints
- Budget limitations: [Description]
- Time pressures: [Description]
- Resource availability: [Description]
- Technical debt: [Description]

### Constraint Impact
| Constraint | Impact on Process | Mitigation |
|------------|-------------------|------------|
| [constraint] | [how it affects work] | [what can be done] |
```

---

### 4. Communications

**Key Questions:**
- How do team members communicate?
- Where are communication bottlenecks?
- How do communication issues relate to problems?

**Investigation:**
```markdown
## Communication Analysis

### Communication Channels
| Channel | Used For | Effectiveness |
|---------|----------|---------------|
| Slack/Teams | Daily comms | [Rating] |
| Email | Formal comms | [Rating] |
| Meetings | Decisions | [Rating] |
| Documentation | Knowledge | [Rating] |

### Bottlenecks Identified
| Bottleneck | Symptom | Impact |
|------------|---------|--------|
| [bottleneck] | [how it manifests] | [delays/errors caused] |

### Communication Improvements
1. [Improvement]
2. [Improvement]
```

---

### 5. Introspection

**Key Questions:**
- Does the team reflect on the process?
- Are there mechanisms to propose improvements?
- Is feedback acted upon?

**Investigation:**
```markdown
## Introspection Analysis

### Reflection Mechanisms
- [ ] Regular retrospectives held: [Yes/No, Frequency]
- [ ] Process feedback mechanism exists: [Yes/No]
- [ ] Improvement suggestions tracked: [Yes/No]

### Feedback Loop
- Feedback → Action time: [Typical duration]
- Feedback acted upon: [Percentage]
- Barriers to acting on feedback: [List]

### Team Engagement
- Team involvement in process decisions: [High/Medium/Low]
- Psychological safety for raising concerns: [High/Medium/Low]
```

---

### 6. Learning and Onboarding

**Key Questions:**
- How do new team members learn the process?
- Is there training or documentation?
- How long until new members are productive?

**Investigation:**
```markdown
## Learning Analysis

### Onboarding
- Onboarding documentation exists: [Yes/No/Partial]
- Onboarding time to productivity: [Duration]
- Mentorship program: [Yes/No]

### Knowledge Transfer
| Knowledge Area | Documented | Verbal Only | Gap |
|----------------|------------|-------------|-----|
| [area] | [Yes/No] | [Yes/No] | [risk] |

### Training
- Formal training available: [List]
- Training gaps: [List]
- Self-service learning resources: [List]
```

---

### 7. Tool Support

**Key Questions:**
- What tools support the process?
- Are there unsupported areas?
- Are the tools effective?

**Investigation:**
```markdown
## Tool Analysis

### Current Tools
| Tool | Purpose | Effectiveness | Issues |
|------|---------|---------------|--------|
| [tool] | [what it does] | [rating] | [problems] |

### Unsupported Areas
| Process Area | Current Method | Tool Opportunity |
|--------------|----------------|------------------|
| [area] | [manual/workaround] | [potential tool] |

### Tool Improvements
1. [Improvement/replacement/addition]
2. [Improvement/replacement/addition]

### Integration Issues
- Tools that don't integrate: [List]
- Manual data transfer needed: [List]
```

---

## Analysis Summary Template

```markdown
## Process Analysis Summary

**Date**: YYYY-MM-DD
**Scope**: [What was analyzed]

### Aspect Ratings

| Aspect | Rating (1-5) | Priority |
|--------|--------------|----------|
| Adoption | [X] | [Low/Med/High] |
| Practice | [X] | [Low/Med/High] |
| Constraints | [X] | [Low/Med/High] |
| Communication | [X] | [Low/Med/High] |
| Introspection | [X] | [Low/Med/High] |
| Learning | [X] | [Low/Med/High] |
| Tool Support | [X] | [Low/Med/High] |

### Top Issues
1. [Most critical issue]
2. [Second issue]
3. [Third issue]

### Recommended Actions
1. [Action for top issue]
2. [Action for second issue]
3. [Action for third issue]
```

---

## Checklist

Before completing process analysis:

- [ ] All 7 aspects investigated
- [ ] Evidence collected (not just opinions)
- [ ] Multiple perspectives gathered
- [ ] Root causes identified (not just symptoms)
- [ ] Issues prioritized by impact
- [ ] Actionable recommendations made
