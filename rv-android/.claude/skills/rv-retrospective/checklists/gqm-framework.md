# Goal-Question-Metric (GQM) Framework

A structured approach to defining meaningful measurements for process improvement.

---

## Overview

The GQM paradigm answers three critical questions:

1. **Why** are we introducing process improvement? → **Goals**
2. **What** information do we need? → **Questions**
3. **What** do we measure? → **Metrics**

```
┌─────────────────────────────────────────────────────────┐
│                    GOALS                                │
│         (What we want to achieve)                       │
│                                                         │
│   Examples:                                             │
│   - Improve product quality                             │
│   - Reduce development time                             │
│   - Increase customer satisfaction                      │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   QUESTION 1  │ │   QUESTION 2  │ │   QUESTION 3  │
│               │ │               │ │               │
│ What do we    │ │ Where are     │ │ How effective │
│ need to know? │ │ problems?     │ │ are changes?  │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   METRIC 1    │ │   METRIC 2    │ │   METRIC 3    │
│               │ │               │ │               │
│ Defect count  │ │ Time per      │ │ Before/after  │
│ by phase      │ │ activity      │ │ comparison    │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## Step 1: Define Goals

Goals describe what the organization wants to achieve. Good goals are:

- **Focused on outcomes** (not process attributes)
- **Measurable** (can verify achievement)
- **Relevant** (aligned with business needs)

### Goal Categories

| Category | Focus | Examples |
|----------|-------|----------|
| **Product Quality** | Software characteristics | Reduce defects, improve reliability |
| **Process Efficiency** | Development activities | Reduce time, lower costs |
| **Customer Satisfaction** | User experience | Better usability, fewer complaints |
| **Team Effectiveness** | Developer productivity | Faster onboarding, less rework |

### Goal Template

```markdown
## Goal: [Name]

**Purpose**: [What we want to improve]
**Object**: [What is being measured - process, product, resource]
**Viewpoint**: [From whose perspective]
**Context**: [Environment/constraints]

**Statement**: Improve [attribute] of [object] from the viewpoint of [stakeholder] in [context]
```

### Example Goals

```markdown
## Goal 1: Reduce Production Defects
- Purpose: Improve
- Object: Product quality
- Viewpoint: End users
- Context: Production environment

Statement: Reduce the number of defects discovered in production from the viewpoint of end users.

## Goal 2: Accelerate Development
- Purpose: Decrease
- Object: Development time
- Viewpoint: Project manager
- Context: Feature development

Statement: Decrease the time from requirements to deployment from the viewpoint of project management.
```

---

## Step 2: Derive Questions

Questions refine goals by identifying areas of uncertainty. Each goal typically has 3-5 questions.

### Question Categories

| Type | Purpose | Examples |
|------|---------|----------|
| **Characterization** | Understand current state | "How long does testing take?" |
| **Evaluation** | Assess against criteria | "Are we meeting quality targets?" |
| **Prediction** | Forecast future | "Will we meet the deadline?" |
| **Comparison** | Compare alternatives | "Which approach is faster?" |

### Question Template

```markdown
## Questions for Goal: [Goal Name]

### Q1: [Question text]
- **Type**: Characterization/Evaluation/Prediction/Comparison
- **What it tells us**: [How answering helps achieve the goal]

### Q2: [Question text]
- **Type**: [Type]
- **What it tells us**: [How answering helps achieve the goal]
```

### Example Questions

```markdown
## Questions for Goal: Reduce Production Defects

### Q1: What types of defects are most common in production?
- Type: Characterization
- What it tells us: Where to focus prevention efforts

### Q2: At what phase are these defects introduced?
- Type: Characterization
- What it tells us: Where process needs improvement

### Q3: What percentage of defects are caught before production?
- Type: Evaluation
- What it tells us: How effective our quality gates are

### Q4: How does our defect rate compare to industry benchmarks?
- Type: Comparison
- What it tells us: Whether we need significant improvement
```

---

## Step 3: Identify Metrics

Metrics are the measurements needed to answer the questions.

### Metric Types

| Type | Description | Examples |
|------|-------------|----------|
| **Direct** | Measured directly | Lines of code, defect count |
| **Indirect** | Calculated from direct | Defects per KLOC, velocity |
| **Subjective** | Based on judgment | Satisfaction rating, complexity estimate |

### Metric Template

```markdown
## Metric: [Name]

**Question(s)**: [Which questions this helps answer]
**Definition**: [Precise definition of what is measured]
**Collection**: [How and when data is collected]
**Unit**: [Unit of measurement]
**Baseline**: [Current/historical value]
**Target**: [Desired value]
**Frequency**: [How often measured]
```

### Example Metrics

```markdown
## Metrics for Goal: Reduce Production Defects

### M1: Production Defect Count
- Questions: Q1, Q3
- Definition: Number of defects reported by users in production
- Collection: Bug tracking system, filtered by "production" tag
- Unit: Count per release
- Baseline: 15 per release
- Target: <5 per release
- Frequency: Per release

### M2: Defect Origin Phase
- Questions: Q2
- Definition: Development phase where defect was introduced
- Collection: Root cause analysis during bug fix
- Unit: Count by phase (requirements, design, coding, testing)
- Baseline: 40% coding, 30% requirements, 20% design, 10% testing
- Target: <20% from requirements
- Frequency: Per release

### M3: Defect Detection Rate
- Questions: Q3
- Definition: Percentage of total defects found before production
- Collection: (Dev defects + Test defects) / Total defects × 100
- Unit: Percentage
- Baseline: 70%
- Target: >90%
- Frequency: Per release

### M4: Defect Density
- Questions: Q4
- Definition: Defects per thousand lines of code
- Collection: Production defects / (LOC / 1000)
- Unit: Defects per KLOC
- Baseline: 2.5 per KLOC
- Target: <1.0 per KLOC
- Frequency: Per release
```

---

## GQM Worksheet

Use this template to develop a complete GQM hierarchy:

```markdown
# GQM Worksheet

## Goal 1: [Goal Statement]

### Questions

| ID | Question | Type |
|----|----------|------|
| Q1.1 | [Question] | [Type] |
| Q1.2 | [Question] | [Type] |
| Q1.3 | [Question] | [Type] |

### Metrics

| ID | Metric | Questions | Unit | Baseline | Target |
|----|--------|-----------|------|----------|--------|
| M1.1 | [Metric] | Q1.1, Q1.2 | [unit] | [value] | [value] |
| M1.2 | [Metric] | Q1.2 | [unit] | [value] | [value] |
| M1.3 | [Metric] | Q1.3 | [unit] | [value] | [value] |

---

## Goal 2: [Goal Statement]

### Questions
...

### Metrics
...
```

---

## Measurement Interpretation

Collecting metrics is not enough—interpretation matters:

### Avoid These Pitfalls

| Pitfall | Description | Example |
|---------|-------------|---------|
| **Correlation vs Causation** | Change in metric may not be due to process change | Time improved but due to simpler requirements, not process |
| **Hawthorne Effect** | Behavior changes because it's being measured | Metrics improve temporarily due to attention |
| **Gaming** | Optimizing metric instead of goal | Closing bugs as "won't fix" to reduce count |
| **Missing Context** | Ignoring factors that affect metric | Comparing projects of different complexity |

### Interpretation Questions

- [ ] Could something else explain this change?
- [ ] Is the trend consistent or anomalous?
- [ ] What qualitative feedback supports/contradicts this?
- [ ] Are there confounding factors?

---

## Common GQM Sets

### Quality Improvement

| Goal | Key Questions | Key Metrics |
|------|---------------|-------------|
| Reduce defects | Where do defects come from? | Defects by phase, defect density |
| Improve reliability | What causes failures? | MTBF, failure rate |
| Enhance maintainability | How hard to change? | Cyclomatic complexity, coupling |

### Efficiency Improvement

| Goal | Key Questions | Key Metrics |
|------|---------------|-------------|
| Reduce time | Where are bottlenecks? | Cycle time by phase |
| Lower cost | Where is effort spent? | Person-days by activity |
| Increase velocity | How much delivered? | Story points per sprint |

### Process Improvement

| Goal | Key Questions | Key Metrics |
|------|---------------|-------------|
| Better estimation | How accurate are estimates? | Estimated vs actual |
| Reduce rework | How much rework? | Rework percentage |
| Improve reviews | Are reviews effective? | Defects found in review |

---

## Checklist

Before finalizing GQM:

- [ ] Goals are outcome-focused (not activity-focused)
- [ ] Each goal has 3-5 questions
- [ ] Questions are answerable with data
- [ ] Metrics are precisely defined
- [ ] Collection method is specified
- [ ] Baseline values are known or planned
- [ ] Targets are realistic
- [ ] Interpretation guidance documented
