# Design — JCA Specification Conformance, Cipher Tables, and the Predicate Graph

GitHub Issue: #101

## Context

All source work happens in the sibling Java reactor: 23 `.mop` files in each of two specification sets, plus two classes in `rvsec-core`. Nothing in `rv-android` changes except the OpenSpec artefacts and the two records this change commits (the conformance verdicts and the predicate inventory).

Three properties of the material shape everything below. First, every edit happens twice — once per set — and the sets must stay identical outside allow-lists, which makes the parity check the load-bearing verification rather than a nicety. Second, the defect classes overlap **inside the same file**: `TrustManagerFactorySpec.mop:65` is simultaneously the third `gtm1` copy-paste defect and one of the two wrong `Property` constants of the predicate graph. Third, most individual edits are one line, while the count is large — 37 graph edges plus the authoring defects plus 23 conformance checks. That combination argues for partitioning by file rather than by defect class, and for verification by arithmetic rather than by review.

The one item that is not a one-line edit is `isValid`. It is shared Java compiled into `rvsec-core` and called at runtime by the monitors of both sets, which is why the previous change stopped at it.

Relevant requirements: FR03 (specification set support), FR01/FR02 (the specifications feed monitor generation and instrumentation), NFR07.

## Architecture

```
   MetaCrySL generated rules (33 .cryptsl, API 30)   [read-only reference]
                    |
            conformance check (per .mop)
                    |
        +-----------+-----------+
        |                       |
  jca (23 .mop)          jca_android (23 .mop)
        |                       |
        +-----------+-----------+
                    |
            parity check: diff == allow-list only
                    |
                rvsec-core
        Property.java        CipherTransformationUtil.java
      (predicate graph)        (tables per spec set)
                    |
            predicate inventory + write/read guard
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| conformance check | Verdict per `.mop` against its generated rule | `.mop` allow-list, `.cryptsl` constraint | anchored / uncontradicted / no-anchor + evidence |
| parity check | Enforce INV-INS-109 | the two set directories | diff restricted to allow-lists, or failure |
| `Property.java` | The predicate vocabulary | — | enum constants (23 today, 34 after) |
| `ExecutionContext` | The predicate store | writes from `.mop` | reads from `.mop` |
| predicate inventory | Every write, read and removal with file, line, spec, event, constant | the 23 `.mop` of one set | versioned CSV |
| write/read guard | Enforce INV-INS-111 | the inventory | failure on an unread, unrecorded constant |
| `CipherTransformationUtil.isValid` | Transformation verdict | transformation string, active set | boolean |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Derivation Provenance of the Android Set | conformance record artefact | verdict present for all 23 |
| INV-INS-109 (allow-list-only diff) | parity script | run after every task group; fails on any non-allow-list hunk |
| INV-INS-113 (verdict per file) | conformance record | 23/23 rows, no blanks |
| Platform-Independent Corrections in Both Sets | the paired edits themselves | parity check + per-file edit count equal across sets |
| Event Membership in the Automaton | `fsm` rows in `TrustManagerFactorySpec`, `SSLContextSpec` | generated monitor's transition table has no all-`fail` row for a bound event |
| INV-INS-110 | same | monitor-generation assertion over both sets |
| Cipher Tables Parameterised | `CipherTransformationUtil` | `jca` verdict table unchanged; Android verdicts follow the derived rule |
| INV-INS-112 | same | no hand-maintained table remains |
| Predicate Contract | `Property.java` + `.mop` reads | write/read guard derived from the inventory |
| INV-INS-111 | write/read guard | fails on a constant written and never read |

## Goals / Non-Goals

**Goals:**

- Both sets free of the layer-2 authoring defects, corrected identically.
- `Cipher` transformation tables sourced from the derivation, selected by set, with `jca` behaviour preserved.
- The predicate graph reconnected where it is a defect, and recorded where it is not.
- A conformance verdict for all 23 derived specifications, and a mechanical parity check that keeps the sets comparable.

**Non-Goals:**

- Changing any cryptographic judgement. Where a derived rule is more permissive than the previous allow-list, following it is a conformance decision, not an endorsement.
- Editing the MetaCrySL tree or its generator. The generated rules are read-only input; their known defects were adopted deliberately and are recorded elsewhere.
- Migrating to a newer CrySL release. Both sides stay anchored to the same release, so the comparison does not straddle two.
- Re-measuring the corpus. What the corrections change in the reported numbers is a separate question from making the corrections.
- Repairing the weaver. That is issue #100.

## Decisions

### D-S1 — partition the work by file, not by defect class

The natural grouping (one pass for bindings, one for the graph) collides inside `TrustManagerFactorySpec`, where `:65` belongs to both. **Decision: one pass per specification file**, applying every defect that file carries — authoring, `fsm`, graph edges — and then porting the same edit to the other set. Each task carries the number of edges expected for that file, taken from the inventory, so completion is checked by counting rather than by reading.

### D-S2 — the inventory is produced first and versioned

The write/read inventory (85 sites: 49 writes, 27 reads, 9 removals) exists only in an ephemeral session scratchpad. Everything downstream — the per-file edge counts, the guard, the deliberate-omission list — depends on it. **Decision: regenerate it as the first task and commit it**, together with the script that produces it, so it can be re-derived after the edits and compared.

### D-S3 — parameterise `isValid` rather than duplicate the utility

Two ways to give the Android set its own transformation tables: a parallel Android-specific utility, or parameterising the existing one.

A parallel utility preserves `jca` trivially but duplicates the parsing and the validation logic, and leaves two tables to be kept in agreement with the derived rules by hand — which is the second hand translation the derivation exists to remove. **Decision: parameterise**, with the tables sourced from the derivation and the active specification set selecting which apply. The cost is that the signature used by the guards in both `.mop` files changes, which is a paired edit like all the others. `jca` behaviour is pinned by a table-driven test asserting the current verdict for every transformation the current implementation accepts and a sample of those it rejects.

### D-S4 — the conformance check covers all 23, not only the 13 verbatim

Ten files were anchored to a generated rule during the derivation and thirteen were carried verbatim, of which three have a stated reason. Checking only the thirteen would leave the ten verified on one axis by one pass with no record that can be re-run. **Decision: produce a verdict for all 23**, each naming the rule that was checked, so the record is complete and re-derivable.

### D-S5 — the guard is derived from the inventory, not hand-written

A hand-written list of expected write/read pairs would drift from the specifications the first time one changes. **Decision: the guard reads the committed inventory and the specifications, recomputes the pairing, and fails on any constant written and neither read nor present in the deliberate-omission list.** The omission list is data, versioned beside the inventory.

### D-S6 — the empirical verification of the two hot specifications is last, and is not relaxed

The corrected allow-list of `SSLContextSpec` and `TrustManagerFactorySpec` is compared against a variable the wrapper collision prevents from being written, so their corrections have no observable effect until issue #100 task 5.3 lands. **Decision: place that verification in the final task group**, and if #100 has not landed, record the task as blocked citing the artefact rather than substituting a weaker check. Every other task in this change is independent of #100.

## API Design

### `CipherTransformationUtil.isValid(transformation: String, tables: TransformationTables) -> boolean`

- **Precondition**: `tables` is the table set of the active specification set, sourced from the derivation.
- **Postcondition**: returns whether the transformation's algorithm, mode and padding are jointly admissible under `tables`. For the `jca` table set the returned verdict is identical to the current implementation's for every input.
- **Error**: a malformed transformation returns `false`, as today; it does not raise, because the call site is a monitor guard.

The tables are class-level and immutable, not method locals rebuilt per call as today. Selection happens once per set, not per invocation.

### `Property` (enum, `rvsec-core`)

Gains 11 constants for the predicates that have no vocabulary today: `preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA`, `preparedDSA`, `preparedEC`, `generatedManagerFactoryParameters`, `cipheredInputStream`, `cipheredOutputStream`, and the two remaining from the inventory's bucket (i-b). Each new constant lands together with the read that consumes it, in the same task — a constant added without a reader is exactly the defect this change removes.

### Predicate inventory (CSV)

`property, kind, file, line, spec, event, snippet` — one row per `ExecutionContext` site, `kind ∈ {WRITE, READ, REMOVE}`. Produced by a committed script over one set's `.mop` files; the other set must produce an identical inventory modulo the directory prefix, which is itself a parity signal.

## Data Flow

Preparation: the generated rules and the two specification sets → the conformance check produces a verdict per file; the inventory script produces the write/read/remove table. Both are committed before any edit.

Editing: per file, apply every defect that file carries → port to the other set → run the parity check → move on. The expected edge count per file comes from the inventory.

Verification: regenerate the inventory → the write/read guard passes or names the offending constant → generate monitors from both sets and assert no bound event has an all-`fail` transition row → the `jca` verdict table for `isValid` is unchanged → the parity diff is allow-list only → finally, once #100 lands, the two hot specifications are verified empirically.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Parity diff outside allow-lists | parity check | Fail the task group | Apply or revert the hunk in both sets |
| Constant written and never read | write/read guard | Fail | Add the reader, or record the omission with its reason |
| Bound event with an all-`fail` transition row | monitor-generation assertion | Fail | Add the event to the `fsm` |
| `jca` verdict change under the parameterised `isValid` | table-driven test | Fail | The Android tables were applied to the `jca` set; fix the selection |
| No generated rule corresponds to a `.mop` | conformance check | Record "no anchor" with the reason | None needed — it is a verdict, not a failure |
| #100 task 5.3 not landed | final task group | Record as blocked citing the artefact | Resume when it lands; do not substitute a weaker check |

## Risks / Trade-offs

- [Correcting both sets breaks exact reproduction of published numbers] → accepted by decision D1 and recorded in the replication package; the alternative is knowingly leaving defects in place.
- [Following a derived rule can widen an allow-list] → the derived profile models availability, not recommendation; the caveat is written into the requirement so a falling violation count is not misread as improvement.
- [46 files, one-line edits, high count] → partition by file with expected counts from the inventory; verification is arithmetic, and the parity check runs after every group.
- [The `isValid` signature change touches guards in both `.mop` sets] → it is a paired edit like every other, and the `jca` verdict table pins the behaviour.
- [The inventory could drift from the specifications after the edits] → it is regenerated at verification time and compared against the committed one.
- [11 new `Property` constants could repeat the original defect] → each lands with its reader in the same task, and the guard fails on any constant that does not.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Contract | Set parity (INV-INS-109) | Diff script over the two directories | 1 check, run per task group |
| Contract | Conformance verdict present for all 23 (INV-INS-113) | Assertion over the conformance record | 1 check |
| Contract | Write/read guard (INV-INS-111) | Guard derived from the committed inventory | 1 check |
| Generation | No bound event has an all-`fail` transition row (INV-INS-110) | Assert over the generated monitor of both sets | 2 checks |
| Unit (Java) | `isValid` under the `jca` tables returns today's verdicts | Table-driven test over accepted and rejected transformations | ~30 cases |
| Unit (Java) | `isValid` under the Android tables follows the derived rule | Table-driven test over the eight admitted algorithms | ~20 cases |
| Empirical | The two hot specifications report as intended | Blocked on #100 task 5.3 | 2 checks |

## Open Questions

- Whether the aliases the 2022 translation added outside upstream — dashless and case variants — are legitimate adaptations to Android provider names or accidental looseness. They are carried over today as declared translation artefacts; the conformance check will list them, and each needs a verdict.
- Whether the deliberate deviations from upstream present in both CrySL releases (OAEP with MD5 and without SHA-1; `NoPadding`/`PKCS1Padding` for RSA) are corrected here or recorded for later. Correcting them is deviating from upstream knowingly, which is a different kind of decision from repairing a translation defect.
- Whether the two deliberate omissions of the predicate graph stay omissions. The substitution they rest on is half-built: the accepting-state mechanism they were replaced by is never read from any `.mop`, so the set is inert at runtime.
