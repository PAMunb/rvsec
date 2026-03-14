# Specification Traceability Checklist

Before finalizing architecture documentation, verify SDD alignment.

---

## Domain Spec

- [ ] Domain spec identified using the mapping table in SKILL.md
- [ ] Domain spec read (`openspec/specs/<domain>/spec.md`)
- [ ] PRD read for NFR definitions (`docs/PRD.md` Section 7)

## Functional Requirements

- [ ] All module FRs listed (from domain spec + PRD)
- [ ] Each FR has architectural support documented (component, pattern, or interface)
- [ ] FRs appear in the "Specification Alignment" section
- [ ] No FRs from the spec are left unaddressed

## Non-Functional Requirements

- [ ] NFR table uses PRD IDs (NFR01-NFR08)
- [ ] Each relevant NFR has concrete architectural mechanism listed
- [ ] Trade-offs between conflicting NFRs documented where applicable

## Invariants

- [ ] Key invariants (INV-XX-NN) from domain spec listed (at least 3)
- [ ] Each invariant has an "Enforcement Mechanism" explaining how the architecture ensures it
- [ ] Invariants cover relevant concerns: data consistency, workflow ordering, error recovery, state validity

## Scenarios

- [ ] At least 2 specification scenarios from domain spec traced through the architecture
- [ ] Each scenario trace identifies which components and patterns participate
- [ ] Scenarios validate that Logical, Development, and Process views are cohesive

## Cross-References

- [ ] "Related Documentation" includes link to domain spec (`openspec/specs/<domain>/spec.md`)
- [ ] "Related Documentation" includes link to PRD (`docs/PRD.md`)
- [ ] ADRs referenced where they document decisions linking to FRs/NFRs
