# ADR Quality Checklist

Quality criteria for Architecture Decision Records. Ensures ADRs are complete, traceable, and useful for future readers.

## How to Use

1. After drafting an ADR, check each section against the completeness criteria below
2. Verify quality attributes for each section in the order they appear in the ADR
3. Run the anti-pattern check to catch common mistakes
4. Apply the review question: "Would a new team member understand why this decision was made?"

---

## Section Completeness

Every ADR must contain these sections, in the order of `templates/adr.md`. Missing sections indicate an incomplete record.

| Section | Required | Completeness Criteria |
|---------|----------|----------------------|
| Title | Yes | `ADR NNNN — [Decision Title]` format, descriptive verb phrase; file `docs/adr/NNNN-<kebab-title>.md` with a row in the `docs/adr/README.md` index |
| Status | Yes | One of: Proposed, Accepted, Deprecated, Superseded by NNNN |
| Deciders | Yes | Names who decided; an agent proposal is recorded as accepted by the user, never as the agent's decision |
| Supersedes / Superseded by | If applicable | Present when the ADR replaces or is replaced by another; both ADRs point at each other |
| Summary | Yes | One Y-statement paragraph: context, concern, decision, goal, accepted trade-off |
| Context | Yes | Describes forces, constraints, and concerns (not just "we needed X") |
| Decision Drivers | Yes | Each driver ranked must/should/nice-to-have, placed before the options |
| Considered Options | Yes | At least 2 options, keeping the current state among them when the decision changes something |
| Decision | Yes | Clear statement starting with "We will..." |
| Consequences | Yes | Positive, Negative and Risks |
| Revisit When | Yes | At least one assumption with an observable trigger |
| Implementation | Yes | Pointer to the OpenSpec change, or "No tracked change" |
| References | Yes | Links to issue number, specs, related ADRs |

## Summary Quality

- [ ] Follows "In the context of …, facing …, we decided …, to achieve …, accepting …"
- [ ] The "accepting" clause names a real cost, not a restated benefit
- [ ] Agrees with the Decision and Consequences sections — no fact appears here that the body does not support

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

## Decision Drivers Quality

- [ ] Drivers appear before the options and are not edited to fit the chosen option afterwards
- [ ] Each driver is ranked must-have, should-have or nice-to-have (see `decision-drivers.md`)
- [ ] Must-haves were confirmed with the user
- [ ] Every driver is used: each one is judged for every option

## Decision Statement Quality

The decision should be unambiguous and actionable.

**Format**: "We will [action] because [primary reason]."

**Quality checklist**:
- [ ] Uses active voice ("We will..." not "It was decided...")
- [ ] Specific enough to implement without further decisions
- [ ] States the primary rationale in the same sentence, in terms of the drivers
- [ ] Says which must-haves eliminated which options
- [ ] Names the strongest rejected option and why it still loses
- [ ] Does not re-explain the context
- [ ] Implementation scope is clear (what changes, what stays)

## Options Section Quality

Options document the decision space that was explored.

**Quality checklist**:
- [ ] At least 2 options considered (including the chosen one)
- [ ] Keeping the current state is an option whenever the decision changes something
- [ ] Each option has a description and a verdict (Meets / Partly / Fails) per driver, with a reason
- [ ] Rejected options have specific rejection reasons tied to drivers
- [ ] Options are genuinely different approaches (not strawmen)
- [ ] The strongest rejected option is written in its best form (steelman)

**Red flag**: Only one option listed, or rejected options described dismissively.

## Consequences Quality

Consequences predict what will happen after implementing the decision.

**Quality checklist**:
- [ ] Positive consequences listed (at least 2)
- [ ] Negative consequences listed (at least 1 — every decision has trade-offs)
- [ ] Negative consequences include what the strongest rejected option would have provided
- [ ] Consequences are specific and measurable when possible
- [ ] Each risk comes from a concrete pre-mortem scenario (trigger, threshold, chain of effects) and has an early warning sign and a mitigation
- [ ] No consequences contradict the context's stated goals

**Red flag**: Only positive consequences listed — this indicates incomplete analysis.

## Revisit When Quality

- [ ] Each assumption the decision depends on is listed
- [ ] Each trigger is observable — a number, an event, a version, a measurement
- [ ] Assumptions behind the pre-mortem failures appear here

**Red flag**: Triggers like "if requirements change" or "if performance degrades", with no threshold.

## Traceability

| Link Type | Required | Example |
|-----------|----------|---------|
| GitHub Issue | Yes | `GitHub Issue: #13` |
| Affected Specs | If applicable | `openspec/specs/agent/spec.md` |
| Related ADRs | If applicable | `0001: Environment-variable pattern` |
| Affected Code | Recommended | `modules/rv-agent/src/rv_agent/agent/` |
| OpenSpec change | If applicable | `openspec/changes/gh72-diagnostic-events/design.md` |
| architecture.md entry | If the module has one | design decisions entry ending with the ADR path |

## Status Lifecycle

```
Proposed → Accepted → [Deprecated | Superseded by NNNN]
```

- **Proposed**: Draft, under review. May be edited freely.
- **Accepted**: Decision approved and being implemented. Changes require a new ADR.
- **Deprecated**: No longer relevant (module removed, feature abandoned).
- **Superseded**: Replaced by a newer ADR. Must link to successor.

## Anti-Patterns

| Anti-Pattern | Description | Fix |
|-------------|-------------|-----|
| Vague Context | "We need a better way to do X" | Describe specific problems, constraints, triggers |
| Missing Alternatives | Only the chosen option documented | Add at least 1 rejected option with reasoning |
| Missing Status Quo | Doing nothing is never weighed | Add "Keep the current state" and judge it like the others |
| Predetermined Conclusion | Options or drivers arranged so the preferred choice cannot lose; rejected options written as strawmen | Fix drivers first, judge every option against them, steelman the strongest rejected one |
| Criteria After Options | Drivers that only the chosen option satisfies, added after the comparison | Rank drivers before judging options; drop any driver that exists only to justify the choice |
| No Negative Consequences | "This is all upside" | Every decision has trade-offs — find them |
| Untestable Revisit Trigger | "Revisit if things change" | Name a number, event or measurement that would invalidate the assumption |
| Duplicated Design | Implementation detail copied from `design.md` | Keep a pointer to the OpenSpec change |
| Agent as Decider | The agent's preference recorded as the decision | Ask the user; record who decided |
| Orphan ADR | No links to issues, specs, or code | Add traceability links |
| Solution in Context | Context describes the solution, not the problem | Rewrite context to focus on forces and constraints |
| Hindsight Bias | Written after implementation, rationalizing the choice | Write ADRs during design, before implementation |

## Review Question

The ultimate test of ADR quality:

> **Would a new team member, reading this ADR 6 months from now, understand WHY this decision was made and WHAT alternatives were considered?**

If no, revise the Context and Considered Options sections.
