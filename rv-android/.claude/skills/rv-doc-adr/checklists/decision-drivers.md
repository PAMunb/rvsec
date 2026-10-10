# Decision Drivers

Framework for identifying and articulating the forces that drive architectural decisions. Use before any option is judged, to fix what the decision will be measured by.

## How to Use

1. Before listing options, identify drivers from each category below
2. Rank each driver must-have, should-have or nice-to-have, and confirm the must-haves with the user
3. Use the template to articulate each driver clearly
4. Judge every option against every driver, then apply the decision rule

## Why Drivers Come First

Drivers chosen after the options are on the table tend to be the ones the preferred option already wins — the comparison then only decorates a conclusion reached beforehand. Fixing and ranking the drivers first makes the comparison able to reject the favourite. Once options are being judged, do not add a driver that only one option satisfies; if a genuinely missed force appears, add it, re-judge every option against it, and say so in the Context.

---

## Driver Categories

### Technical Drivers

Forces related to the technology itself.

| Driver Type | Example Questions |
|------------|-------------------|
| Performance | Does response time, throughput, or resource usage matter? |
| Scalability | Will this need to handle more load in the future? |
| Technology Constraints | Are we locked into specific frameworks, languages, or versions? |
| Compatibility | Must this work with existing systems or APIs? |
| Complexity | How much complexity does each option add to the system? |

### Quality Attribute Drivers

Non-functional requirements that influence the decision.

| Driver Type | Example Questions |
|------------|-------------------|
| Maintainability | How easy will this be to change later? |
| Testability | Can we test this effectively? |
| Reliability | What happens when this component fails? |
| Observability | Can we monitor and debug this in production? |
| Security | What attack surface does this expose? |

### Constraint Drivers

Fixed limitations that narrow the decision space.

| Driver Type | Example Questions |
|------------|-------------------|
| Existing Infrastructure | What's already deployed that we must work with? |
| Team Expertise | What does the team know and what is unfamiliar? |
| Third-Party Limitations | What do our dependencies support or restrict? |
| Standards | Are there coding standards, protocols, or regulations we must follow? |
| Backward Compatibility | Must existing clients/users continue to work unchanged? |

### Risk Drivers

Uncertainties that could affect the outcome.

| Driver Type | Example Questions |
|------------|-------------------|
| Unknowns | What don't we know that could change the decision? |
| External Dependencies | What relies on systems outside our control? |
| Migration Complexity | How hard is it to switch if this choice is wrong? |
| Failure Modes | What are the worst-case scenarios? |

### Stakeholder Drivers

People and organizational forces.

| Driver Type | Example Questions |
|------------|-------------------|
| Thesis Timeline | Does this affect the PhD defense schedule? |
| Review Board | Will this satisfy academic reviewers? |
| Future Maintainers | Will someone else need to work with this? |

## rv-android Common Drivers

These drivers appear frequently in rv-android decisions:

| Driver | Priority | Rationale |
|--------|----------|-----------|
| P1 Simplicity | Must-have | Minimum complexity for current task |
| Thesis Timeline | Must-have | Academic deadline constraints |
| Module Boundaries | Must-have | Clean separation between uv workspace modules |
| LLM Compatibility | Should-have | Must work with Qwen3-VL via SGLang |
| Single Developer | Context | Architecture must be understandable by one person |
| Reproducibility | Should-have | Experiments must produce reproducible results |
| Resource Constraints | Context | Limited GPU, single desktop machine |

## Driver Prioritization

### Must-Have vs Nice-to-Have

| Priority | Definition | Decision Impact |
|----------|-----------|----------------|
| Must-have | Non-negotiable. If not satisfied, the option is rejected. | Eliminates options |
| Should-have | Important but trade-offs are acceptable. | Differentiates options |
| Nice-to-have | Desirable but not a deciding factor. | Tiebreaker only |

### Decision Rule

An option that fails any must-have is eliminated. Among the remaining options, the should-haves decide; nice-to-haves only break ties. When no option wins on every should-have, the Decision section names the should-have that was traded away. Keeping the current state is judged by the same rule as every other option.

### Weighted Scoring (Optional)

For decisions with many drivers, assign weights:

| Driver | Weight (1-5) | Option A Score | Option B Score |
|--------|-------------|---------------|---------------|
| Simplicity | 5 | 4 | 2 |
| Testability | 3 | 3 | 4 |
| Performance | 2 | 2 | 5 |
| **Weighted Total** | | **35** | **32** |

Use only when drivers conflict and the decision is not obvious. Most rv-android decisions can be resolved by P1 Simplicity alone.

## Driver Articulation Template

For each driver, write:

> **This decision is driven by [driver] because [rationale].**

Examples:
- "This decision is driven by **module boundary clarity** because rv-agent must remain independently testable without rv-platform running."
- "This decision is driven by **P1 Simplicity** because the calibration system has only one execution mode and does not benefit from a strategy pattern."
- "This decision is driven by **thesis timeline** because the defense is in Q3 2026 and we need working calibration results by Q2."

## Connecting Drivers to ADR Sections

| Driver Location | How to Reference |
|----------------|-----------------|
| ADR Context | "The primary forces driving this decision are: [list drivers]" |
| ADR Decision Drivers | The ranked table, written before the options |
| ADR Considered Options | One verdict per driver per option: "[Driver]: Fails — [reason]" |
| ADR Decision | "We will adopt Option A because it best satisfies [top drivers]; Option B fails [must-have]" |
| ADR Consequences | "Positive: satisfies [driver]. Negative: partially compromises [driver]" |
