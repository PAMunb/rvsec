# Software Quality Attributes

Reference checklist for understanding what our verification tools measure.

---

## The 16 Quality Attributes

Software quality is multidimensional. Different verification checks target different attributes.

| Category | Attribute | Description |
|----------|-----------|-------------|
| **Dependability** | Availability | System operational and ready when needed |
| | Safety | Freedom from conditions that cause harm |
| | Security | Protection against unauthorized access |
| | Reliability | Probability of failure-free operation |
| | Resilience | Ability to recover from failures |
| | Robustness | Behavior under unexpected conditions |
| **Maintainability** | Understandability | Ease of comprehension |
| | Testability | Ease of testing |
| | Adaptability | Ease of modification |
| | Modularity | Independent components |
| | Complexity | Structural simplicity |
| **Usability** | Portability | Ease of moving to new environment |
| | Usability | Ease of use |
| | Reusability | Potential for reuse |
| | Efficiency | Resource utilization |
| | Learnability | Ease of learning |

---

## Tool-to-Attribute Mapping

### Tests (pytest)

| Attribute | How Tests Verify |
|-----------|------------------|
| Reliability | Functional correctness under normal conditions |
| Robustness | Edge case and error handling tests |
| Security | Security-focused test cases |

### Static Analysis (flake8, mypy)

| Attribute | How Verified |
|-----------|--------------|
| Understandability | Naming conventions, code style |
| Complexity | Nesting depth, line length |
| Maintainability | Type annotations (mypy) |

### Security Analysis (bandit, safety)

| Attribute | How Verified |
|-----------|--------------|
| Security | Vulnerability patterns in code (bandit) |
| Security | Known vulnerabilities in dependencies (safety) |

### Metrics (radon)

| Attribute | Metric | Tool |
|-----------|--------|------|
| Complexity | Cyclomatic complexity | radon cc |
| Maintainability | Maintainability index | radon mi |
| Understandability | Halstead metrics | radon hal |

---

## Quality Trade-offs

Not all attributes can be maximized simultaneously. Common trade-offs:

| Optimizing For | May Reduce |
|----------------|------------|
| Efficiency | Understandability, Maintainability |
| Security | Usability, Efficiency |
| Robustness | Efficiency |
| Reusability | Efficiency (extra abstraction) |

**Guidance**: Define which attributes are critical for your project and accept trade-offs for non-critical ones.

---

## Verification Priority by Attribute

### Critical (Always Verify)
- [ ] Reliability - tests pass
- [ ] Security - no critical vulnerabilities

### High (Should Verify)
- [ ] Maintainability - complexity within thresholds
- [ ] Testability - coverage acceptable

### Medium (Verify When Possible)
- [ ] Efficiency - performance acceptable
- [ ] Portability - no platform-specific issues

---

## Thresholds

Recommended thresholds for metrics:

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Cyclomatic Complexity | ≤ 10 | 11-20 | > 20 |
| Maintainability Index | ≥ 65 | 40-64 | < 40 |
| Test Coverage | ≥ 80% | 60-79% | < 60% |
| Nesting Depth | ≤ 4 | 5-6 | > 6 |
| Function Length (lines) | ≤ 50 | 51-100 | > 100 |
| File Length (lines) | ≤ 500 | 501-1000 | > 1000 |

---

## Quick Reference

```
Quality = Function of (Process Quality + Product Attributes)

Internal Attributes          External Attributes
(measurable)                  (experienced)
─────────────────────         ─────────────────────
Cyclomatic Complexity    ─►   Maintainability
Lines of Code            ─►   Reliability
Depth of Inheritance     ─►   Reusability
Coupling (CBO)           ─►   Testability
```

Metrics are internal attributes that *correlate with* (but don't guarantee) external quality attributes.
