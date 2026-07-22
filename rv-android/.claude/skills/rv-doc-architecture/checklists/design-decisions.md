# Architectural Design Decisions

Key questions to answer when designing or documenting system architecture.

---

## Overview

Architecture is fundamentally about **decisions**. Document the decisions, not just the resulting structure.

---

## The 9 Key Questions

### 1. Application Architecture Template

**Question**: Is there a generic application architecture that can act as a template?

**What to Document**:
- What type of application is this? (CLI tool, web service, library, etc.)
- What reference architectures apply?
- What can be reused from similar systems?

**Example**:
```markdown
### Application Type
CLI-based testing tool with plugin architecture.

### Reference Architecture
Follows the standard tool-with-plugins pattern used by pytest and other testing frameworks.
```

---

### 2. Distribution Strategy

**Question**: How will the system be distributed across processors?

**What to Document**:
- Single machine vs distributed
- Client-server relationships
- Process boundaries

**Example**:
```markdown
### Distribution
- Host: Orchestration and analysis
- Device: App execution and UI interaction
- Communication: ADB bridge over USB/TCP
```

---

### 3. Architectural Patterns

**Question**: What architectural patterns or styles are used?

**What to Document**:
- Primary patterns used
- Rationale for pattern selection
- How patterns are applied

**Example**:
```markdown
### Patterns Used

| Pattern | Application | Rationale |
|---------|-------------|-----------|
| Layered | Core structure | Separation of concerns |
| Repository | Data access | Centralized data management |
| Plugin | Tool integration | Extensibility |
```

---

### 4. Structuring Approach

**Question**: What is the fundamental approach to structure the system?

**What to Document**:
- Modular vs monolithic
- Layering strategy
- Component boundaries

**Example**:
```markdown
### Structuring Approach
Modular architecture with uv workspace:
- Each module is independently versioned
- Clear dependency order
- Minimal coupling between modules
```

---

### 5. Component Decomposition

**Question**: How are structural components decomposed into sub-components?

**What to Document**:
- Decomposition criteria
- Sub-component responsibilities
- Hierarchy of components

**Example**:
```markdown
### Component Decomposition

```
rv-agent
├── agent/ (workflow orchestration)
│   ├── nodes/ (individual workflow steps)
│   └── state/ (state management)
├── strategies/ (exploration strategies)
└── services/ (shared services)
```
```

---

### 6. Control Strategy

**Question**: What strategy controls the operation of components?

**What to Document**:
- Centralized vs distributed control
- Event-driven vs call-based
- Control flow patterns

**Example**:
```markdown
### Control Strategy
- **Primary**: Event-driven via EventBus
- **Workflow**: State machine with LangGraph
- **Components**: Lifecycle managed by executor
```

---

### 7. NFR-Driven Decisions

**Question**: What architectural organization best delivers the non-functional requirements?

**What to Document**:
- Key NFRs and their architectural implications
- Trade-offs between conflicting requirements
- How architecture supports each NFR

**Example**:
```markdown
### NFR Support

| NFR | Architectural Support |
|-----|----------------------|
| Performance | Localized critical operations, batched I/O |
| Maintainability | Fine-grained components, clear interfaces |
| Extensibility | Plugin system, strategy pattern |
```

---

### 8. Architecture Evaluation

**Question**: How is the architectural design evaluated?

**What to Document**:
- Evaluation criteria
- Validation approaches
- Known limitations

**Example**:
```markdown
### Architecture Evaluation
- **Against requirements**: All FR/NFRs traceable to components
- **Against patterns**: Consistent with reference architectures
- **Limitations**: Single-device at a time, synchronous execution
```

---

### 9. Documentation Strategy

**Question**: How should the architecture be documented?

**What to Document**:
- What views to include
- Level of detail
- Maintenance plan

**Example**:
```markdown
### Documentation
- Logical and Development views (always current)
- Process view (updated when concurrency changes)
- Kept in docs/architecture.md per module
```

---

## Decision Documentation Template

For significant architectural decisions, use this format:

```markdown
### Decision: [Decision Name]

**Context**: [Why this decision was needed]

**Decision**: [What was decided]

**Alternatives Considered**:
1. [Alternative 1]: [Rejected because...]
2. [Alternative 2]: [Rejected because...]

**Consequences**:
- Positive: [Benefits]
- Negative: [Trade-offs]

**Status**: Accepted | Deprecated | Superseded
```

---

## Quick Decision Checklist

When reviewing architecture, verify these questions are answered:

- [ ] Application type and template identified
- [ ] Distribution strategy documented
- [ ] Architectural patterns named
- [ ] Structuring approach clear
- [ ] Component decomposition shown
- [ ] Control strategy described
- [ ] NFR support explained
- [ ] Evaluation approach defined
- [ ] Documentation strategy stated

---

## Linking to ADRs

For major decisions, create an ADR using `/rv-doc-adr` skill.

Architecture documentation should reference relevant ADRs:

```markdown
## Related Decisions

- [ADR-001: Use LangGraph for workflow](./adr/ADR-001.md)
- [ADR-002: Event-driven communication](./adr/ADR-002.md)
```
