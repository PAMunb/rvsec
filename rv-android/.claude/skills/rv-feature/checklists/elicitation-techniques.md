# Elicitation Techniques

Techniques for discovering and capturing feature requirements.

---

## Overview

Requirements elicitation follows a cycle:

```
Discovery ──────► Classification ──────► Prioritization ──────► Specification
    │                                                                │
    └────────────────────── Iteration ◄──────────────────────────────┘
```

Use multiple techniques for complete coverage.

---

## Technique 1: Structured Questions

### Problem-Focused Questions

Start with the problem, not the solution:

| Question | Purpose |
|----------|---------|
| What problem does this solve? | Core motivation |
| Who experiences this problem? | Stakeholders |
| How do they currently work around it? | Existing behavior |
| What happens if we don't solve it? | Priority signal |
| How will we know it's solved? | Acceptance criteria |

### Stakeholder Questions

| Question | Purpose |
|----------|---------|
| Who uses this feature? | Primary users |
| Who is affected by this feature? | Secondary stakeholders |
| Who provides input data? | Data sources |
| Who consumes output data? | Data consumers |
| Who maintains this feature? | Operations perspective |

### Constraint Questions

| Question | Purpose |
|----------|---------|
| What technology must we use? | Technical constraints |
| What existing systems must we integrate with? | Integration requirements |
| What standards must we follow? | Compliance needs |
| What are the performance expectations? | NFR discovery |
| What are the security requirements? | Security needs |

---

## Technique 2: Scenarios

Scenarios describe user interactions as narratives.

### Scenario Template

```markdown
### Scenario: [Name]

**Actor**: [Who performs the action]
**Goal**: [What they want to achieve]
**Context**: [When/where this happens]

**Main Flow**:
1. [Actor does X]
2. [System responds with Y]
3. [Actor does Z]
4. [System completes with W]

**Alternative Flows**:
- **If [condition]**: [What happens instead]
- **If [error]**: [Error handling]

**Pre-conditions**: [What must be true before]
**Post-conditions**: [What must be true after]
```

### Scenario Example

```markdown
### Scenario: Export Test Results

**Actor**: Developer
**Goal**: Export test results for external analysis
**Context**: After running tests, want to share results with team

**Main Flow**:
1. Developer views test results in dashboard
2. Developer clicks "Export" button
3. System shows format selection (JSON, CSV, HTML)
4. Developer selects JSON format
5. System generates JSON file
6. System prompts for save location
7. Developer chooses location
8. System saves file and shows confirmation

**Alternative Flows**:
- **If no tests selected**: Show "Select tests to export" message
- **If export fails**: Show error with retry option

**Pre-conditions**: At least one test result exists
**Post-conditions**: Valid JSON file exists at chosen location
```

### Scenario Types

| Type | Purpose | Focus |
|------|---------|-------|
| **Normal** | Happy path | Expected behavior |
| **Alternative** | Valid variations | Other valid paths |
| **Exception** | Error handling | Invalid inputs, failures |
| **Edge Case** | Boundary conditions | Limits, empty states |

---

## Technique 3: Use Cases

Formal specification of system interactions.

### Use Case Template

```markdown
## Use Case: [UC-N] [Name]

**Actor**: [Primary actor]
**Scope**: [System boundary]
**Level**: [User goal / Subfunction]

### Preconditions
- [What must be true before]

### Postconditions (Success)
- [What must be true after success]

### Postconditions (Failure)
- [What must be true after failure]

### Main Success Scenario
1. [Actor action]
2. [System response]
3. [Actor action]
4. [System response]

### Extensions
**2a. [Condition]:**
  1. [System does X]
  2. [Return to step 3]

**3a. [Error condition]:**
  1. [System shows error]
  2. [Use case ends]

### Special Requirements
- [NFR-1]: [Performance requirement]
- [NFR-2]: [Security requirement]

### Technology/Data Variations
- Input: JSON or YAML format
- Output: File or stream
```

---

## Technique 4: Existing Code Analysis

Learn from existing patterns in the codebase.

### Analysis Questions

| Question | What to Look For |
|----------|------------------|
| How are similar features implemented? | Patterns to follow |
| What interfaces exist? | Integration points |
| What data structures are used? | Data models |
| How are errors handled? | Error patterns |
| How are features tested? | Testing patterns |

### Skills to Use

```
/rv-analyze-module [module-name]   # Understand structure
/rv-analyze-file [file-path]       # Study patterns
/rv-analyze-dependencies [module]  # Find integration points
```

---

## Technique 5: Prototyping (Spike)

For unclear requirements, build a quick prototype.

### Spike Guidelines

| Aspect | Guideline |
|--------|-----------|
| **Time-box** | Max 30-60 minutes |
| **Goal** | Answer specific question |
| **Output** | Decision document, not code |
| **Throw away** | Spike code is disposable |

### Spike Template

```markdown
## Spike: [Question to Answer]

**Time-box**: [X minutes]
**Question**: [Specific question to answer]

### Approach
1. [What we'll try]
2. [What we'll measure]

### Findings
- [Finding 1]
- [Finding 2]

### Decision
[What we decided based on findings]

### Implications for Requirements
- [New requirement discovered]
- [Requirement clarified]
```

---

## Elicitation Process

### Step 1: Initial Discovery
- [ ] Ask problem-focused questions
- [ ] Identify stakeholders
- [ ] Document initial requirements list

### Step 2: Scenario Development
- [ ] Write normal scenario(s)
- [ ] Write alternative scenarios
- [ ] Write exception scenarios
- [ ] Identify edge cases

### Step 3: Requirement Extraction
- [ ] Extract functional requirements from scenarios
- [ ] Identify non-functional requirements
- [ ] Document constraints

### Step 4: Validation
- [ ] Review scenarios with stakeholders
- [ ] Confirm requirements are complete
- [ ] Prioritize requirements

### Step 5: Specification
- [ ] Classify requirements (FR/NFR)
- [ ] Add metrics to NFRs
- [ ] Document acceptance criteria

---

## Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| **Assuming you understand** | Always ask clarifying questions |
| **Solution bias** | Focus on problem first, solution later |
| **Missing stakeholders** | Ask "who else is affected?" |
| **Vague requirements** | Add specific metrics and criteria |
| **Missing edge cases** | Explicitly ask about empty, max, error states |
| **Scope creep** | Document what's OUT of scope |
