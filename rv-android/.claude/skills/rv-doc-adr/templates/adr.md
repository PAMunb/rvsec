# ADR NNNN — [Title — Concise Decision Statement]

- **Status**: [Proposed | Accepted | Deprecated | Superseded by NNNN]
- **Date**: [YYYY-MM-DD]
- **Deciders**: [Who decided — e.g. "Pedro", or "Pedro, on the agent's proposal"]
- **Supersedes**: [NNNN: Title — omit the line when this ADR replaces none]
- **Superseded by**: [NNNN: Title — add the line only when a later ADR replaces this one]

## Summary

In the context of [situation], facing [concern or constraint], we decided [chosen option] to
achieve [goal or quality attribute], accepting [the main trade-off].

[One paragraph, one sentence per clause. A reader who stops here knows the decision and its price.]

## Context

[The problem, not the solution. What forces and constraints are at play — technical, timeline,
resource? Why is the decision needed now, and what happens if nothing is done? Name the issue,
the affected specs and the code involved, specifically enough that someone unfamiliar with the
project can follow.]

## Decision Drivers

[Stated before the options, so the options are judged by criteria fixed in advance.
See checklists/decision-drivers.md for categories and ranking.]

| Priority | Driver | Why it matters here |
|----------|--------|---------------------|
| Must-have | [Driver] | [Rationale] |
| Should-have | [Driver] | [Rationale] |
| Nice-to-have | [Driver] | [Rationale] |

## Considered Options

### Option 1: Keep the current state

**Description**: [What the system does today and what keeping it costs]

**Against the drivers**:
- [Driver]: [Meets | Partly | Fails] — [reason]
- [Driver]: [Meets | Partly | Fails] — [reason]

**Other trade-offs**: [Anything the drivers do not capture, or "None"]

### Option 2: [Name]

**Description**: [What this option involves]

**Against the drivers**:
- [Driver]: [Meets | Partly | Fails] — [reason]
- [Driver]: [Meets | Partly | Fails] — [reason]

**Other trade-offs**: [Anything the drivers do not capture, or "None"]

[Write each rejected option in its strongest form — the version a capable advocate would defend.]

## Decision

We will [clear, unambiguous statement of the decision] because [the drivers it satisfies].

[Which must-haves eliminated which options, and which should-haves separated the rest. Then the
strongest rejected option and, in one or two sentences, why it still loses on the drivers. State
what changes and what stays the same.]

## Consequences

### Positive
- [Benefit, tied to a driver]

### Negative
- [What is given up — including what the strongest rejected option would have provided]

### Risks
- [Failure scenario from the pre-mortem] — early warning: [what would be seen first];
  mitigation: [concrete action]

## Revisit When

[The assumptions the decision rests on. Each trigger must be observable: a number, an event, a
version, a measurement — not "if things change".]

| Assumption | Revisit when |
|------------|--------------|
| [What is taken as true] | [Concrete invalidation trigger] |

## Implementation

[Pointer only: `openspec/changes/<change>/design.md`, or the archived change under
`openspec/changes/archive/`. If no change tracks the work, write "No tracked change."]

## References

- GitHub Issue: #N
- Affected specs: [list]
- Related ADRs: [list]
- Affected code: [paths]
