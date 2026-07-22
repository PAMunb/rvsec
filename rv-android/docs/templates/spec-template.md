# Specification: [Domain Name]

## Purpose

[Narrative description of this domain's role in the system. Should answer:
- What problem does this domain solve?
- How does it fit in the overall pipeline?
- What are the key design decisions and constraints?

Write for TWO audiences: (1) developers implementing the system, and (2) LLMs generating
tasks and design artifacts. Include enough context and motivation that either audience
can understand the domain independently.]

[Include data models with field descriptions:]

```
ModelName:
  field_name: type    # description
  field_name: type    # description
```

[Include diagrams or flows when they clarify relationships:]

```
Phase A → [Component] → Phase B
                ↓
         Side-effect (Neo4j, disk, etc.)
```

[Describe relationships with other domains — inputs consumed, outputs produced,
dependencies and contracts.]

## Data Contracts

### Input

- `field_name: type` — description (source/origin)
- `field_name: type` — description

### Output

- `field_name: type` — description (destination/consumer)
- `field_name: type` — description

### Side-Effects

- **[System]**: description of side-effect (file creation, database writes, etc.)

### Error

- `ErrorClass` — when raised and why

## Invariants

- **INV-XX-01**: Description of rule that MUST always hold. Use RFC 2119 keywords.
- **INV-XX-02**: Another invariant.

[Invariants should be testable assertions. Each invariant should be verifiable
by an automated test or code review.]

## Requirements

### Requirement: [Name] ([FR/NFR ID])

[Narrative description of the requirement. Provide enough context that a developer
can understand WHY this requirement exists, not just WHAT it demands.

Use RFC 2119 keywords (MUST, MUST NOT, SHALL, SHOULD, MAY) consistently.]

#### Scenario: [Descriptive Name]

- **WHEN** [concrete precondition with actual values]
- **THEN** [expected behavior with RFC 2119 keyword]
- **AND** [additional assertions]

[Scenarios COMPLEMENT the narrative — they don't replace it. A requirement should
be understandable from the narrative alone; scenarios provide concrete test cases.]
