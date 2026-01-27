# Dependability Analysis Checklist

A systematic framework for analyzing and verifying software dependability properties.

---

## Overview

Dependability is the degree to which a system can be trusted. It encompasses multiple complementary properties that must be analyzed together.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Dependability Framework                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │ AVAILABILITY  │  │  RELIABILITY  │  │    SAFETY     │           │
│  │ System ready  │  │ Correct under │  │ No harmful    │           │
│  │ when needed   │  │ normal use    │  │ states        │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
│                                                                     │
│                      ┌───────────────┐                              │
│                      │   SECURITY    │                              │
│                      │ Protected from│                              │
│                      │ unauthorized  │                              │
│                      │ access/damage │                              │
│                      └───────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Four Dimensions of Dependability

### 1. Availability

The probability that a system is operational and able to deliver services when requested.

| Aspect | Description | Verification |
|--------|-------------|--------------|
| Uptime | System is running and accessible | Monitor uptime metrics |
| Responsiveness | System responds within acceptable time | Performance tests |
| Service delivery | Core functions are working | Health checks, smoke tests |

**Checklist:**
- [ ] Critical services have health check endpoints
- [ ] Failover mechanisms exist for critical components
- [ ] Graceful degradation when dependencies fail
- [ ] Recovery procedures documented and tested

### 2. Reliability

The probability of failure-free operation over a specified time, under specified conditions.

| Aspect | Description | Verification |
|--------|-------------|--------------|
| Correctness | Produces correct outputs for valid inputs | Unit/integration tests |
| Consistency | Same inputs produce same outputs | Determinism tests |
| Fault tolerance | Continues operating despite faults | Chaos testing |

**Checklist:**
- [ ] All business logic has test coverage
- [ ] Edge cases and boundary conditions tested
- [ ] Error handling for all failure modes
- [ ] Retry mechanisms for transient failures

### 3. Safety

Freedom from conditions that can cause harm (to users, environment, or other systems).

| Aspect | Description | Verification |
|--------|-------------|--------------|
| Hazard identification | Known dangerous conditions | Risk analysis |
| Hazard mitigation | Controls to prevent accidents | Safety requirements |
| Fail-safe behavior | Safe state when failure occurs | Failure mode testing |

**Checklist:**
- [ ] Hazards identified and documented
- [ ] Safety-critical code clearly marked
- [ ] Fail-safe defaults for all operations
- [ ] Data validation at system boundaries

### 4. Security

Protection against unauthorized access, modification, or destruction.

| Aspect | Description | Verification |
|--------|-------------|--------------|
| Confidentiality | Data accessible only to authorized | Access control tests |
| Integrity | Data not improperly modified | Input validation |
| Authentication | Identity verified | Auth mechanism tests |
| Authorization | Actions permitted only for authorized | Permission tests |

**Checklist:**
- [ ] Authentication mechanisms in place
- [ ] Authorization checked at all entry points
- [ ] Sensitive data encrypted at rest and in transit
- [ ] Input validation prevents injection attacks

---

## The Fault-Error-Failure Chain

Understanding the causal chain helps in designing effective countermeasures.

```
┌─────────┐        ┌─────────┐        ┌─────────┐
│  FAULT  │───────►│  ERROR  │───────►│ FAILURE │
│         │        │         │        │         │
│ Defect  │        │ Wrong   │        │ Service │
│ in the  │        │ system  │        │ does not│
│ system  │        │ state   │        │ deliver │
└─────────┘        └─────────┘        └─────────┘
     │                  │                  │
     ▼                  ▼                  ▼
 Prevention         Detection          Recovery
 (Avoidance)      (Monitoring)       (Tolerance)
```

### Terminology

| Term | Definition | Example |
|------|------------|---------|
| **Fault** | A defect in the system (bug, misconfiguration) | Null pointer dereference in code |
| **Error** | An incorrect internal state caused by a fault | Variable contains wrong value |
| **Failure** | Externally visible deviation from required service | API returns wrong result |

### Checklist by Chain Stage

**Fault Prevention:**
- [ ] Code review process catches defects
- [ ] Static analysis runs in CI
- [ ] Coding standards enforced
- [ ] Dependencies vetted for vulnerabilities

**Error Detection:**
- [ ] Assertions check internal invariants
- [ ] Logging captures state at critical points
- [ ] Monitoring alerts on anomalies
- [ ] Health checks verify component states

**Failure Recovery:**
- [ ] Automatic retry for transient failures
- [ ] Circuit breakers prevent cascade
- [ ] Graceful degradation preserves core functionality
- [ ] Recovery procedures documented and tested

---

## Three Approaches to Dependability

### 1. Fault Avoidance

Preventing faults from being introduced in the first place.

| Technique | Description | Tools |
|-----------|-------------|-------|
| Code review | Human inspection of changes | GitHub PR reviews |
| Static analysis | Automated code checking | flake8, mypy, bandit |
| Formal methods | Mathematical verification | For critical systems |
| Standards | Coding guidelines | PEP 8, project conventions |

**Checklist:**
- [ ] All changes reviewed before merge
- [ ] Static analysis passes with no errors
- [ ] Security-sensitive code has extra review
- [ ] Dependencies have no known vulnerabilities

### 2. Fault Detection

Finding faults before they cause failures.

| Technique | Description | Tools |
|-----------|-------------|-------|
| Testing | Exercise code paths | pytest |
| Monitoring | Observe runtime behavior | Prometheus, logs |
| Assertions | Runtime invariant checks | Python assert |
| Auditing | Periodic review | Security audits |

**Checklist:**
- [ ] Test coverage meets threshold (e.g., 80%)
- [ ] Critical paths have integration tests
- [ ] Runtime errors are logged
- [ ] Periodic security scans scheduled

### 3. Fault Tolerance

Continuing to operate despite the presence of faults.

| Technique | Description | Implementation |
|-----------|-------------|----------------|
| Redundancy | Multiple instances | Load balancers, replicas |
| Recovery | Restore correct state | Retry, rollback |
| Isolation | Contain fault scope | Process isolation, containers |
| Graceful degradation | Reduced but functioning | Feature flags, fallbacks |

**Checklist:**
- [ ] Critical services have redundancy
- [ ] Retry logic for transient failures
- [ ] Circuit breakers prevent cascade failures
- [ ] Fallback behavior for degraded operation

---

## Security Analysis Framework

### Security Terminology

| Term | Definition | Example |
|------|------------|---------|
| **Asset** | Something of value to be protected | User data, API keys, credentials |
| **Exposure** | Potential loss if asset is compromised | Financial loss, reputation damage |
| **Vulnerability** | Weakness that can be exploited | SQL injection, hardcoded secrets |
| **Attack** | Exploitation of vulnerability | Malicious SQL query |
| **Threat** | Potential for attack (agent + motivation) | External hacker seeking data |
| **Control** | Measure to mitigate threat | Input validation, parameterized queries |

### Security Analysis Checklist

**Asset Identification:**
- [ ] All sensitive data identified and classified
- [ ] Data flow documented (where data goes)
- [ ] Third-party data handling reviewed

**Vulnerability Assessment:**
- [ ] Input validation at all entry points
- [ ] No hardcoded credentials or secrets
- [ ] Dependencies scanned for vulnerabilities
- [ ] Authentication/authorization reviewed

**Threat Mitigation:**
- [ ] Controls in place for identified threats
- [ ] Defense in depth (multiple layers)
- [ ] Principle of least privilege applied
- [ ] Security testing included in CI

---

## Verification Mapping

How verification tools map to dependability properties:

| Tool | Availability | Reliability | Safety | Security |
|------|-------------|-------------|--------|----------|
| pytest | - | X | - | - |
| flake8 | - | X | - | - |
| mypy | - | X | - | - |
| bandit | - | - | - | X |
| safety | - | - | - | X |
| radon | - | X | - | - |
| Health checks | X | - | - | - |
| Load tests | X | X | - | - |
| Chaos tests | X | X | - | - |

---

## Quick Assessment Template

```markdown
## Dependability Assessment: [component-name]

### Availability
- [ ] Health checks implemented
- [ ] Failover/recovery tested
- [ ] SLA defined and measurable

### Reliability
- [ ] Test coverage: [X%]
- [ ] Error handling complete
- [ ] Edge cases covered

### Safety
- [ ] Hazards documented
- [ ] Fail-safe defaults
- [ ] Input validation at boundaries

### Security
- [ ] Authentication in place
- [ ] Authorization checked
- [ ] No known vulnerabilities
- [ ] Secrets properly managed

### Summary
| Dimension | Status | Notes |
|-----------|--------|-------|
| Availability | OK/WARN/FAIL | |
| Reliability | OK/WARN/FAIL | |
| Safety | OK/WARN/FAIL | |
| Security | OK/WARN/FAIL | |
```

---

## Priority by System Type

| System Type | Priority Order |
|-------------|----------------|
| Financial/Banking | Security > Reliability > Availability > Safety |
| Healthcare/Medical | Safety > Security > Reliability > Availability |
| E-commerce | Availability > Security > Reliability > Safety |
| Internal Tools | Reliability > Availability > Security > Safety |

Adjust verification emphasis based on system criticality profile.
