# Design: [Change Name]

## Context

[Brief context: which change this design supports, which FRs/NFRs it addresses,
and any relevant constraints or decisions from the specs.]

## Architecture

[High-level view of how the components interact. Include a diagram:]

```
[Component A] → [Component B] → [Side-effect]
       ↓
[Component C]
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `module.function` | What it does | Type | Type |

## Mapping: Spec → Implementation

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR01: Name | `module.function()` | `test_fr01_*` |
| INV-XX-01 | Enforced by `module.guard()` | `test_inv_xx_01` |

## API Design

### `function_name(param: type) -> ReturnType`

[Description of the function's contract. Include:]
- **Preconditions**: What must be true before calling
- **Postconditions**: What is guaranteed after successful return
- **Error behavior**: What exceptions can be raised and when

## Data Flow

[Describe how data flows through the components in this change:]

```
Input → [Step 1: description] → [Step 2: description] → Output
                                        ↓
                                  Side-effect
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ErrorClass` | When it occurs | How handled | How to recover |

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Logic without I/O | Mock dependencies | ~N tests |
| Integration | Component interaction | Real dependencies | ~N tests |
| PBT | Invariants | Hypothesis | ~N tests |
