# Requirements Validation

Techniques for validating that requirements are correct and complete.

---

## Validation Checks

Every requirement must pass these checks:

| Check | Question | Failure Indicates |
|-------|----------|-------------------|
| **Validity** | Does this solve the actual problem? | Requirement may be unnecessary |
| **Consistency** | Does this contradict other requirements? | Conflicting requirements |
| **Completeness** | Are all aspects covered? | Missing requirements |
| **Realism** | Can this be implemented? | Infeasible requirement |
| **Verifiability** | Can we test this? | Unmeasurable requirement |
| **Traceability** | Why do we need this? | Orphan requirement |

---

## Check 1: Validity

**Question**: Does this requirement address a real need?

### Validation Steps
1. Trace requirement back to problem statement
2. Identify the stakeholder who needs this
3. Confirm the business value

### Red Flags
- Cannot identify who needs this
- Requirement is "nice to have" without clear benefit
- Solving a problem no one has

### Template
```markdown
**Requirement**: [FR-N]
**Traces to**: [Problem/User story]
**Stakeholder**: [Who needs this]
**Value**: [Why this matters]
**Valid**: ✅ / ❌
```

---

## Check 2: Consistency

**Question**: Does this requirement conflict with others?

### Validation Steps
1. List related requirements
2. Check for contradictions
3. Check for resource conflicts
4. Check for timing conflicts

### Conflict Types

| Type | Example |
|------|---------|
| **Direct** | "Must be fast" vs "Must be thorough" |
| **Resource** | Two features need same limited resource |
| **Timing** | Dependencies create impossible order |
| **Semantic** | Same term means different things |

### Template
```markdown
**Requirement**: [FR-N]
**Related to**: [FR-X, FR-Y, NFR-Z]
**Potential conflicts**: [None / List]
**Resolution**: [How to resolve if any]
**Consistent**: ✅ / ❌
```

---

## Check 3: Completeness

**Question**: Are all aspects of this feature covered?

### Completeness Dimensions

| Dimension | Questions |
|-----------|-----------|
| **Inputs** | All input types covered? Edge cases? |
| **Outputs** | All output types defined? Formats? |
| **States** | All system states handled? |
| **Errors** | All error conditions covered? |
| **Users** | All user types considered? |
| **Data** | All data scenarios addressed? |

### Completeness Checklist
- [ ] Normal flow defined
- [ ] Alternative flows defined
- [ ] Error handling defined
- [ ] Empty/null cases handled
- [ ] Maximum limits defined
- [ ] Boundary conditions covered
- [ ] All user roles considered

### Template
```markdown
**Requirement**: [FR-N]
**Normal flow**: ✅ / ❌
**Alternative flows**: ✅ / ❌ [count]
**Error handling**: ✅ / ❌
**Edge cases**: ✅ / ❌ [list]
**Complete**: ✅ / ❌
```

---

## Check 4: Realism

**Question**: Can this requirement be implemented?

### Realism Factors

| Factor | Question |
|--------|----------|
| **Technical** | Is this technically possible? |
| **Time** | Can this be done in available time? |
| **Resources** | Do we have the skills/tools? |
| **Dependencies** | Are required dependencies available? |
| **Integration** | Can this integrate with existing systems? |

### Red Flags
- Requires technology that doesn't exist
- Requires external systems we can't control
- Requires skills we don't have
- Has unrealistic performance targets

### Template
```markdown
**Requirement**: [FR-N] or [NFR-N]
**Technical feasibility**: ✅ / ⚠️ / ❌
**Dependencies available**: ✅ / ❌
**Skills available**: ✅ / ❌
**Realistic**: ✅ / ❌
**Concerns**: [List any concerns]
```

---

## Check 5: Verifiability

**Question**: Can we prove this requirement is met?

### Verifiability Criteria

| Requirement Type | Verifiable | Not Verifiable |
|-----------------|------------|----------------|
| **Functional** | "Returns JSON with fields X, Y" | "Works correctly" |
| **Performance** | "Response < 200ms" | "Is fast" |
| **Reliability** | "99.9% uptime" | "Is reliable" |
| **Usability** | "< 3 clicks to complete" | "Is user-friendly" |
| **Security** | "AES-256 encryption" | "Is secure" |

### Making Requirements Verifiable

| Vague | Verifiable |
|-------|------------|
| "Fast response" | "Response time < 200ms for 95th percentile" |
| "Easy to use" | "New user completes task in < 5 minutes" |
| "Highly available" | "99.9% uptime measured monthly" |
| "Handles many users" | "Supports 1000 concurrent users" |
| "Secure" | "All data encrypted with AES-256 at rest" |

### Template
```markdown
**Requirement**: [FR-N] or [NFR-N]
**Test method**: [How to verify]
**Pass criteria**: [Specific threshold]
**Verifiable**: ✅ / ❌
**If not verifiable**: [How to make it verifiable]
```

---

## Check 6: Traceability

**Question**: Can we trace this requirement to its source and implementation?

### Traceability Links

```
User Need ──► Requirement ──► Design ──► Implementation ──► Test
```

### Traceability Matrix

| Requirement | Source | Design | Implementation | Test |
|-------------|--------|--------|----------------|------|
| FR-1 | User Story #5 | design.md:L45 | service.py:L100 | test_fr1.py |
| FR-2 | Bug #123 | design.md:L67 | handler.py:L50 | test_fr2.py |
| NFR-1 | SLA Document | arch.md:L20 | cache.py | test_perf.py |

---

## Validation Process

### Before Implementation

```
For each requirement:
1. ✅ Check Validity      - Does this solve real problem?
2. ✅ Check Consistency   - No conflicts with others?
3. ✅ Check Completeness  - All aspects covered?
4. ✅ Check Realism       - Can we build this?
5. ✅ Check Verifiability - Can we test this?
6. ✅ Check Traceability  - Can we track this?
```

### Validation Report Template

```markdown
## Requirements Validation Report

### Summary
- **Total requirements**: [count]
- **Passed all checks**: [count]
- **Need revision**: [count]

### Validation Results

| ID | Valid | Consistent | Complete | Realistic | Verifiable | Status |
|----|-------|------------|----------|-----------|------------|--------|
| FR-1 | ✅ | ✅ | ✅ | ✅ | ✅ | Ready |
| FR-2 | ✅ | ⚠️ | ✅ | ✅ | ✅ | Review |
| NFR-1 | ✅ | ✅ | ✅ | ❌ | ✅ | Revise |

### Issues Found

#### Issue 1: [FR-2] Consistency concern
**Description**: Potential conflict with FR-5
**Resolution**: [How to resolve]

#### Issue 2: [NFR-1] Realism concern
**Description**: Target may be too aggressive
**Resolution**: [How to resolve]

### Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
```

---

## Common Validation Problems

| Problem | Solution |
|---------|----------|
| **Ambiguous language** | Replace with specific, measurable terms |
| **Missing edge cases** | Add scenarios for empty, max, error states |
| **Conflicting requirements** | Prioritize and document decision |
| **Unmeasurable NFR** | Add specific metrics and thresholds |
| **Gold plating** | Remove requirements without clear value |
| **Scope creep** | Document what's explicitly OUT of scope |
