# Requirements Classification

Guide for classifying and organizing feature requirements.

---

## Requirement Types

### Functional Requirements (FR)

What the system must **do**:
- Features and capabilities
- Business logic and rules
- Data processing operations
- User interactions

**Template**:
```markdown
**FR-[N]**: [Description of what the system must do]

- **Input**: [What triggers this requirement]
- **Processing**: [What the system does]
- **Output**: [Expected result or behavior]
- **Pre-conditions**: [What must be true before]
- **Post-conditions**: [What must be true after]
```

**Example**:
```markdown
**FR-1**: The system shall export test results to JSON format.

- **Input**: User clicks "Export" button with tests selected
- **Processing**: Convert selected TestResult objects to JSON
- **Output**: JSON file saved to user-specified location
- **Pre-conditions**: At least one test result exists
- **Post-conditions**: File exists and is valid JSON
```

---

### Non-Functional Requirements (NFR)

How well the system performs - quality attributes:

| Category | Type | Description |
|----------|------|-------------|
| **Product** | Efficiency | Speed, resource usage |
| **Product** | Reliability | Failure rate, availability |
| **Product** | Security | Access control, data protection |
| **Product** | Usability | Ease of learning, use |
| **Organizational** | Environmental | Platform, language |
| **Organizational** | Operational | Deployment, monitoring |
| **Organizational** | Development | Standards, tools |
| **External** | Regulatory | Laws, standards |
| **External** | Interoperability | Integration requirements |

---

## NFR Metrics

Non-functional requirements must be **measurable**. Use these metrics:

| Property | Metric | Example |
|----------|--------|---------|
| **Speed** | Response time | "< 200ms for 95th percentile" |
| **Speed** | Throughput | "100 requests/second" |
| **Size** | Memory | "< 512MB peak memory" |
| **Size** | Disk | "< 100KB per log entry" |
| **Reliability** | Availability | "99.9% uptime" |
| **Reliability** | Failure rate | "< 1 failure per 1000 operations" |
| **Reliability** | Recovery time | "< 5 seconds to recover" |
| **Security** | Data protection | "AES-256 encryption at rest" |
| **Security** | Access control | "Role-based with 3 levels" |
| **Usability** | Learning time | "< 10 minutes to complete task" |
| **Usability** | Error rate | "< 5% user errors per session" |
| **Portability** | Platforms | "Python 3.10+ on Linux/macOS" |

**Template**:
```markdown
**NFR-[N]**: [Category] - [Property]

- **Metric**: [How to measure]
- **Target**: [Specific threshold]
- **Verification**: [How to test]
```

**Example**:
```markdown
**NFR-1**: Product - Efficiency (Speed)

- **Metric**: Response time for action execution
- **Target**: < 500ms for 95th percentile
- **Verification**: Performance test with 100 iterations
```

---

## Classification Checklist

When capturing requirements:

### Functional Requirements
- [ ] What must the system do?
- [ ] What data does it process?
- [ ] What are the inputs and outputs?
- [ ] What triggers this functionality?
- [ ] What are the business rules?
- [ ] What are the edge cases?

### Non-Functional Requirements
- [ ] How fast must it be? (Speed metrics)
- [ ] How much resource can it use? (Size metrics)
- [ ] How reliable must it be? (Failure metrics)
- [ ] What security constraints exist? (Security metrics)
- [ ] Who uses it and how easily? (Usability metrics)
- [ ] Where must it run? (Portability constraints)

### Constraints
- [ ] Technology constraints (language, framework)
- [ ] Integration constraints (APIs, protocols)
- [ ] Regulatory constraints (standards, laws)
- [ ] Organizational constraints (coding standards)

---

## Priority Levels

| Level | Label | Description |
|-------|-------|-------------|
| P0 | Must Have | Feature won't work without this |
| P1 | Should Have | Important but has workarounds |
| P2 | Could Have | Nice to have, low priority |
| P3 | Won't Have | Out of scope for this iteration |

---

## Output Template

```markdown
## Requirements Classification

### Functional Requirements

| ID | Description | Priority | Pre-conditions | Post-conditions |
|----|-------------|----------|----------------|-----------------|
| FR-1 | [desc] | P0 | [pre] | [post] |
| FR-2 | [desc] | P1 | [pre] | [post] |

### Non-Functional Requirements

| ID | Category | Property | Metric | Target |
|----|----------|----------|--------|--------|
| NFR-1 | Product | Speed | Response time | < 200ms |
| NFR-2 | Product | Reliability | Availability | 99.9% |

### Constraints

| Type | Constraint |
|------|------------|
| Technology | Python 3.10+, uv |
| Integration | Must use existing EventBus |
| Standard | PEP 8 compliance |

### Priority Summary
- **P0 (Must Have)**: [count] requirements
- **P1 (Should Have)**: [count] requirements
- **P2 (Could Have)**: [count] requirements
```
