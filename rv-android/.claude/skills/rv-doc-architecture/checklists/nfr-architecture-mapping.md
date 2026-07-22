# NFR-Architecture Mapping

How non-functional requirements influence architectural decisions.

---

## The Architecture-NFR Relationship

Functional requirements are implemented by components.
Non-functional requirements are enabled by the architecture.

```
Functional Requirements ──────► Components (what they do)
                                    │
Non-functional Requirements ──────► Architecture (how they're organized)
```

---

## NFR Architectural Guidelines

### Performance

**If performance is critical**:

| Guideline | Rationale |
|-----------|-----------|
| Localize critical operations | Minimize communication overhead |
| Use fewer, larger components | Reduce inter-component calls |
| Co-locate related components | Avoid network/process boundaries |
| Consider replication | Parallel execution on multiple processors |

**Architectural Patterns**:
- Pipe-and-filter for data processing
- Caching layers
- Asynchronous processing

**Example**:
```markdown
### Performance Optimization
- Critical LLM calls localized in single service
- Batch multiple UI operations in single ADB command
- Screenshot processing co-located with parsing
```

---

### Security

**If security is critical**:

| Guideline | Rationale |
|-----------|-----------|
| Use layered architecture | Defense in depth |
| Protect inner layers | Most critical assets deepest |
| Validate at boundaries | Trust boundaries explicit |
| Minimize attack surface | Fewer entry points |

**Architectural Patterns**:
- Layered with security validation between layers
- Sandbox for untrusted components
- Secure enclave for sensitive data

**Example**:
```markdown
### Security Architecture
- Input validation at API boundary
- Credentials stored in innermost layer
- External tools run in isolated environment
```

---

### Safety

**If safety is critical**:

| Guideline | Rationale |
|-----------|-----------|
| Isolate safety-related operations | Easier to validate |
| Use single/few components | Reduce validation scope |
| Provide protection systems | Graceful shutdown on failure |
| Design for failure | Fail-safe defaults |

**Architectural Patterns**:
- Watchdog patterns
- Redundant monitors
- Safe state fallbacks

**Example**:
```markdown
### Safety Measures
- Timeout on all device operations
- Automatic cleanup on crash
- Safe defaults when state unknown
```

---

### Availability

**If availability is critical**:

| Guideline | Rationale |
|-----------|-----------|
| Include redundant components | Continue if one fails |
| Support hot replacement | Update without downtime |
| Design stateless where possible | Easier recovery |
| Implement health checks | Early problem detection |

**Architectural Patterns**:
- Active-passive redundancy
- Circuit breaker pattern
- Health monitoring

**Example**:
```markdown
### Availability Design
- Stateless LLM client (can switch providers)
- Device connection recovery on disconnect
- Health check before each operation
```

---

### Maintainability

**If maintainability is critical**:

| Guideline | Rationale |
|-----------|-----------|
| Use fine-grained components | Easy to change individual parts |
| Make components self-contained | Changes localized |
| Separate data producers from consumers | Loose coupling |
| Avoid shared data structures | Reduce change impact |

**Architectural Patterns**:
- Microservices/modular architecture
- Event-driven decoupling
- Interface segregation

**Example**:
```markdown
### Maintainability Design
- Each strategy is independent plugin
- Components communicate via events
- No shared mutable state
```

---

## NFR Conflicts and Trade-offs

NFRs often conflict. Document trade-offs explicitly.

### Performance vs Maintainability

| Performance Wants | Maintainability Wants |
|-------------------|----------------------|
| Large components | Small components |
| Tight coupling | Loose coupling |
| Shared state | Isolated state |

**Resolution Strategy**:
```markdown
### Trade-off: Performance vs Maintainability

**Decision**: Prioritize maintainability except for critical path.

**Implementation**:
- Default: Fine-grained components, loose coupling
- Critical path: Optimized with larger components
- Boundary: Clearly marked "hot path" code
```

### Security vs Usability

| Security Wants | Usability Wants |
|----------------|-----------------|
| Strict validation | Minimal friction |
| Limited access | Flexible access |
| Audit everything | Fast operations |

**Resolution Strategy**: Define user roles with appropriate security levels.

---

## NFR Documentation Template

For each significant NFR, document:

```markdown
### NFR: [Name]

**Priority**: P0 | P1 | P2

**Metric**: [How to measure]

**Target**: [Specific threshold]

**Architectural Support**:
- [How architecture enables this NFR]
- [Specific patterns or structures used]

**Trade-offs**:
- [What was sacrificed for this NFR]

**Verification**:
- [How to verify NFR is met]
```

---

## Mapping Checklist

When documenting architecture, verify NFR support:

- [ ] Key NFRs identified with priorities
- [ ] Each NFR has architectural support described
- [ ] Conflicts between NFRs documented
- [ ] Trade-off decisions explained
- [ ] Verification approach defined for each NFR
