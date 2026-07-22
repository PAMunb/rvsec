# ADR Quality Checklist

Quality criteria for Architecture Decision Records. Ensures ADRs are complete, traceable, and useful for future readers.

## How to Use

1. After drafting an ADR, check each section against the completeness criteria below
2. Verify quality attributes for context, decision, and consequences sections
3. Run the anti-pattern check to catch common mistakes
4. Apply the review question: "Would a new team member understand why this decision was made?"

---

## Section Completeness

Every ADR must contain these sections. Missing sections indicate an incomplete record.

| Section | Required | Completeness Criteria |
|---------|----------|----------------------|
| Title | Yes | `ADR-NNN: [Decision Title]` format, descriptive verb phrase |
| Status | Yes | One of: Proposed, Accepted, Deprecated, Superseded by ADR-XXX |
| Context | Yes | Describes forces, constraints, and concerns (not just "we needed X") |
| Decision | Yes | Clear statement starting with "We will..." |
| Alternatives Considered | Yes | At least 2 alternatives with pros/cons |
| Consequences | Yes | Both positive AND negative consequences listed |
| References | Yes | Links to issue number, specs, related ADRs |

## Context Quality Criteria

The context section is the most important part of an ADR — it explains WHY the decision was needed.

**Good context answers**:
- What problem are we facing?
- What forces or constraints are at play?
- What was the trigger for making this decision now?
- What existing system components are affected?

**Quality checklist**:
- [ ] Describes the problem, not the solution
- [ ] Mentions relevant constraints (technical, timeline, team)
- [ ] References specific code, modules, or architecture affected
- [ ] Explains what happens if no decision is made (status quo consequences)
- [ ] Is understandable without reading the rest of the ADR

**Red flags**: Context that only says "We need to choose X" without explaining why or what forces are at play.

## Decision Statement Quality

The decision should be unambiguous and actionable.

**Format**: "We will [action] because [primary reason]."

**Quality checklist**:
- [ ] Uses active voice ("We will..." not "It was decided...")
- [ ] Specific enough to implement without further decisions
- [ ] States the primary rationale in the same sentence
- [ ] Does not re-explain the context
- [ ] Implementation scope is clear (what changes, what stays)

## Alternatives Section Quality

Alternatives document the decision space that was explored.

**Quality checklist**:
- [ ] At least 2 alternatives considered (including the chosen one)
- [ ] Each alternative has description, pros, and cons
- [ ] Rejected alternatives have specific rejection reasons
- [ ] Alternatives are genuinely different approaches (not strawmen)
- [ ] The chosen option's advantages clearly address the context's forces

**Red flag**: Only one alternative listed, or rejected alternatives described dismissively.

## Consequences Quality

Consequences predict what will happen after implementing the decision.

**Quality checklist**:
- [ ] Positive consequences listed (at least 2)
- [ ] Negative consequences listed (at least 1 — every decision has trade-offs)
- [ ] Consequences are specific and measurable when possible
- [ ] Risks identified with mitigation strategies
- [ ] No consequences contradict the context's stated goals

**Red flag**: Only positive consequences listed — this indicates incomplete analysis.

## Traceability

| Link Type | Required | Example |
|-----------|----------|---------|
| GitHub Issue | Yes | `GitHub Issue: #13` |
| Affected Specs | If applicable | `openspec/specs/agent/spec.md` |
| Related ADRs | If applicable | `ADR-001: Module Boundary Convention` |
| Affected Code | Recommended | `modules/rv-agent/src/rv_agent/agent/` |

## Status Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded by ADR-NNN]
```

- **Proposed**: Draft, under review. May be edited freely.
- **Accepted**: Decision approved and being implemented. Changes require a new ADR.
- **Deprecated**: No longer relevant (module removed, feature abandoned).
- **Superseded**: Replaced by a newer ADR. Must link to successor.

## Anti-Patterns

| Anti-Pattern | Description | Fix |
|-------------|-------------|-----|
| Vague Context | "We need a better way to do X" | Describe specific problems, constraints, triggers |
| Missing Alternatives | Only the chosen option documented | Add at least 1 rejected alternative with reasoning |
| No Negative Consequences | "This is all upside" | Every decision has trade-offs — find them |
| Orphan ADR | No links to issues, specs, or code | Add traceability links |
| Solution in Context | Context describes the solution, not the problem | Rewrite context to focus on forces and constraints |
| Hindsight Bias | Written after implementation, rationalizing the choice | Write ADRs during design, before implementation |

## Review Question

The ultimate test of ADR quality:

> **Would a new team member, reading this ADR 6 months from now, understand WHY this decision was made and WHAT alternatives were considered?**

If no, revise the context and alternatives sections.
