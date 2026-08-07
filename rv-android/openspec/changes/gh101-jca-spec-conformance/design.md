# Design — JCA Specification Conformance, Cipher Tables, and the Predicate Graph

GitHub Issue: #101

## Context

Almost all source work happens in the sibling Java reactor: the 23 `.mop` files of the `jca_android` set, one enum in `rvsec-core`, and one new class beside it. In `rv-android` itself the change touches one file — `rv-experiment`'s configuration, to make the derived set selectable by name — plus the OpenSpec artefacts and the three records this change commits (the conformance verdicts, the predicate inventory, and the divergence record).

The premise that shapes everything below is the freeze. The `jca` set produced published measurements, so it is an instrument and not merely code: it stays byte-identical to its state at this change's base commit, and every correction lands in the derived set alone. That single constraint decides three things that would otherwise be open. Edits happen once rather than twice, so the work halves. The verification that used to be a parity check — the sets must not differ outside allow-lists — inverts into a freeze check plus an enumeration, because divergence is now the intended result and only *unrecorded* divergence is a defect. And `isValid`, the one item that is not a one-line edit, stops being a parameterisation problem: it is called by the frozen set's `CipherSpec`, so it cannot be touched at all, and the derived set gets a utility of its own.

Two properties of the material survive the change of premise. The defect classes overlap **inside the same file**: `TrustManagerFactorySpec.mop:65` is simultaneously the third `gtm1` copy-paste defect and one of the two wrong `Property` constants of the predicate graph. And most individual edits are one line while the count is large — 37 graph edges plus the authoring defects plus 23 conformance checks. That combination argues for partitioning by file rather than by defect class, and for verification by arithmetic rather than by review.

Relevant requirements: FR03 (specification set support), FR01/FR02 (the specifications feed monitor generation and instrumentation), NFR07.

## Architecture

```
   MetaCrySL generated rules (33 .cryptsl, API 30)   [read-only reference]
                    |
            conformance check (per .mop)
                    |
                    v
  jca (23 .mop)             jca_android (23 .mop)
  FROZEN at base   --diff-->  every repair lands here
        |            |                  |
        |     divergence record         |
        |   (each non-allow-list hunk   |
        |    with its reason)           |
        |                               |
        v                               v
                rvsec-core
  jca/util/CipherTransformationUtil          FROZEN
  jca/util/AndroidCipherTransformationUtil   derived API 30 tables
        \                               /
         \      Property.java          /
          \  (additive constants only) /
                    |
            predicate inventory + write/read guard

  rv-android: specification_set gains "jca_android"
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| conformance check | Verdict per `.mop` against its generated rule | `.mop` allow-list, `.cryptsl` constraint | anchored / uncontradicted / no-anchor + evidence |
| freeze check | Enforce INV-INS-109 (a) | base commit, the frozen paths | failure on any byte changed under `jca/` or in its `CipherTransformationUtil` |
| divergence record | Enforce INV-INS-109 (b) | the two set directories | every non-allow-list hunk named with its reason, or failure |
| `Property.java` | The predicate vocabulary | — | enum constants (23 today, 32 after), additive only |
| `ExecutionContext` | The predicate store | writes from `.mop` | reads from `.mop` |
| predicate inventory | Every write, read and removal with file, line, spec, event, constant | the 23 `.mop` of a set | versioned CSV |
| write/read guard | Enforce INV-INS-111 | the inventory | failure on an unread, unrecorded constant |
| `jca/util/AndroidCipherTransformationUtil` | Transformation verdict under the derived rule | transformation string | boolean |
| `specification_set` mapping | Make the derived set selectable by name | `"jca_android"` | its `mop_specs_dir` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Derivation Provenance of the Android Set | conformance record artefact | verdict present for all 23 |
| The Java SE Set Is Frozen | no edit under the frozen paths | freeze check against the base commit, run after every task group |
| INV-INS-109 (a) freeze | same | `git diff <base> -- <frozen paths>` is empty |
| INV-INS-109 (b) enumeration | divergence record | every non-allow-list hunk of the set diff is named by an entry |
| INV-INS-113 (verdict per file) | conformance record | 23/23 rows, no blanks |
| Event Membership in the Automaton | `fsm` rows in `jca_android`'s `TrustManagerFactorySpec`, `SSLContextSpec` | generated monitor's transition table has no all-`fail` row for a bound event |
| INV-INS-110 | same | monitor-generation assertion over the derived set |
| Cipher Tables of the Derived Set | new `jca/util/AndroidCipherTransformationUtil` | Android verdicts follow the derived rule; the frozen class is untouched |
| INV-INS-112 | same | no hand-maintained table, and no runtime selection over a shared one |
| Predicate Contract | `Property.java` + `jca_android` `.mop` reads | write/read guard derived from the inventory |
| INV-INS-111 | write/read guard | fails on a constant written and never read |
| Specification Set Support (FR03) | `specification_set` mapping in `config.py` | `"jca_android"` resolves without `custom_specs_dir` |

## Goals / Non-Goals

**Goals:**

- The derived set free of the layer-2 authoring defects, with the frozen set demonstrably untouched.
- `Cipher` transformation tables for the derived set sourced from the generated rule, in a utility the derived specification names directly.
- The predicate graph reconnected where it is a defect, and recorded where it is not.
- A conformance verdict for all 23 derived specifications, and a divergence record that keeps every difference between the sets attributable.
- The derived set selectable by name, so the corrected instrument cannot be missed by a mistyped path.

**Non-Goals:**

- Correcting the `jca` set. Its defects are real and stay, because it is the instrument the published numbers were measured with; the debt is recorded, not paid here.
- Changing any cryptographic judgement. Where a derived rule is more permissive than the previous allow-list, following it is a conformance decision, not an endorsement.
- Editing the MetaCrySL tree or its generator. The generated rules are read-only input; their known defects were adopted deliberately and are recorded elsewhere.
- Migrating to a newer CrySL release. Both sides stay anchored to the same release, so the comparison does not straddle two.
- Re-measuring the corpus. What the corrections change in the reported numbers is a separate question from making the corrections.
- Repairing the weaver. That is issue #100.

## Decisions

### D-S0 — the `jca` set is frozen; corrections land in the derived set alone

The layer-2 defects are present in both sets, byte for byte, because they sit in the portion the derivation copies unchanged. Repairing both was the original plan, accepting that the numbers published from `jca` would stop reproducing exactly.

**Decision: freeze `jca`.** It is the instrument the published measurements were taken with, and an instrument altered after the fact makes those measurements irreproducible — a worse outcome than a known defect in a set whose results are already interpreted with care. Nothing under `rvsec-mop/src/main/resources/jca`, and nothing in the `CipherTransformationUtil` its `CipherSpec` calls, changes in this change. Every correction lands in `jca_android`.

Two costs are accepted and recorded rather than mitigated. The `jca` set keeps its defects and the spurious reports they cause, so its results stay reproducible without becoming correct. And the sets stop differing along one axis: an outcome difference between them can now come from the platform allow-list or from a repair present in one set only, and nothing separates the contributions after the fact. This is why the parity check inverts into a freeze check plus an enumeration — see D-S7.

This reverses decision D1 of `docs/20260806_plano_specs_jca_android.md`, which had accepted the replication cost. The reversal is deliberate and is the user's: reproducibility of published work outranks the tidiness of a single correction landing everywhere it applies.

### D-S1 — partition the work by file, not by defect class

The natural grouping (one pass for bindings, one for the graph) collides inside `TrustManagerFactorySpec`, where `:65` belongs to both. **Decision: one pass per specification file**, applying every defect that file carries — authoring, `fsm`, graph edges. Each task carries the number of edges expected for that file, taken from the inventory, so completion is checked by counting rather than by reading. Under D-S0 each pass happens once, in the derived set, and its result is entered in the divergence record.

### D-S2 — the inventory is produced first and versioned

The write/read inventory (85 sites: 49 writes, 27 reads, 9 removals) exists only in an ephemeral session scratchpad. Everything downstream — the per-file edge counts, the guard, the deliberate-omission list — depends on it. **Decision: regenerate it as the first task and commit it**, together with the script that produces it, so it can be re-derived after the edits and compared.

### D-S3 — a separate class for the derived set, not a parameterised shared one

Two ways to give the Android set its own transformation tables: parameterise the existing utility by the active specification set, or give the derived set a class of its own.

Parameterising was the earlier decision, on the grounds that a parallel utility duplicates parsing and validation logic. D-S0 removes that option outright: `jca/CipherSpec.mop` and `jca_android/CipherSpec.mop` are identical today, both importing `br.unb.cic.mop.jca.util.CipherTransformationUtil` and calling `isValid(...)` at five sites, so parameterising the signature means editing the frozen set's call site. The only way to parameterise without touching it would be a mutable switch read at runtime — which puts the frozen set's verdict under the control of state set elsewhere, exactly the failure mode the freeze exists to prevent.

**Decision: add `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`**, holding the eight algorithms of the generated API 30 `Cipher` rule with their per-algorithm mode and padding tables as immutable class-level data.

It lands **beside** the frozen class in the package that already exists, rather than in a `jca_android` package mirroring the specification directory. Both forms satisfy INV-INS-112 equally, because what selects the tables is the specification naming the class; the sibling form simply costs less. It adds no package, raises no question about an underscore in a package name, and lets the new class call `alg`, `mode` and `pad` directly, with no import at all. The freeze is unaffected either way: it covers the *file* `jca/util/CipherTransformationUtil.java`, not the directory, and a new class no `jca` specification imports leaves the frozen set's generated monitor unchanged.

The `.mop` side is a single line whichever form is chosen, and the reason is worth recording because it is not obvious: `CipherSpec.mop` reaches the utility through a **static wildcard import** (`import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*;`) and calls bare `isValid(transformation)`. Redirecting that import to the new class leaves all five call sites byte-identical. Nothing else from the utility is used in the `.mop`, so the wildcard imports one symbol in practice.

The duplication objection is answered rather than accepted: `alg`, `mode` and `pad` are `public static` and correct, so the new class calls them instead of restating them. What differs is only the tables and the admissibility decision — and those genuinely differ in shape, since the frozen implementation branches over two algorithm families while the derived rule expresses eight with per-algorithm implications from mode to padding.

One behaviour of the frozen class is carried over deliberately rather than inherited by accident: it folds the padding to upper case before comparing (`pad(transformation).toUpperCase()`). The corpus contains `Cipher.getInstance("AES/CBC/PKCS5PADDING")`, which is accepted today only because of that fold, so a transcription that compared the rule's literals exactly would regress it. The derived class folds case on all three components, which is a repair rather than a transcription and is recorded as such — the wider question of case and alias handling across the other specifications is left open and is not part of this change.

Two hygiene defects in the frozen class — `PKCS5PADDING` listed twice for both `CBC` and `PCBC`, and a commented `rsaECBPaddings` block duplicating the live code — are consequently **not** repaired here. They are inside the freeze. They are recorded as knowingly retained, with the rest of the frozen set's debt.

### D-S4 — the conformance check covers all 23, not only the 13 verbatim

Ten files were anchored to a generated rule during the derivation and thirteen were carried verbatim, of which three have a stated reason. Checking only the thirteen would leave the ten verified on one axis by one pass with no record that can be re-run. **Decision: produce a verdict for all 23**, each naming the rule that was checked, so the record is complete and re-derivable.

### D-S5 — the guard is derived from the inventory, not hand-written

A hand-written list of expected write/read pairs would drift from the specifications the first time one changes. **Decision: the guard reads the committed inventory and the specifications, recomputes the pairing, and fails on any constant written and neither read nor present in the deliberate-omission list.** The omission list is data, versioned beside the inventory.

### D-S7 — the parity check becomes a freeze check plus an enumeration

The original verification was a single mechanical criterion: the diff between the sets contains allow-list content only. D-S0 makes that criterion false by design, so it cannot simply be dropped — dropping it would leave the sets free to drift with nothing recording why.

**Decision: split it in two.** The first half is a freeze check — `git diff` from this change's base commit over `rvsec-mop/src/main/resources/jca` and `jca/util/CipherTransformationUtil.java` must be empty. It is mechanical, cheap, and fails on any edit reaching the frozen paths whatever its merit. The second half is the divergence record: every hunk by which the sets differ outside allow-list content carries an entry naming it, its reason, and the task that introduced it, and a hunk without an entry fails the check.

The enumeration is what preserves the property the parity check was protecting. The sets are no longer identical outside allow-lists, but the ways in which they differ remain finite, named, and attributable — so a later reader comparing results across the sets can tell which differences are platform and which are repair. An unenumerated difference would make the sets incomparable rather than merely differently scoped.

Both halves run at the end of every task group, as the parity check did.

### D-S8 — the derived set becomes a first-class `specification_set` value

`ExperimentConfig.specification_set` admits `jca`, `generic` and `custom`; `jca_android` is reachable only by pointing `custom_specs_dir` at its directory. That was a cosmetic gap while the sets were identical outside allow-lists.

D-S0 makes it a hazard. The derived set is now the only one carrying the corrections, so a mistyped or stale `custom` path silently selects the uncorrected instrument and the experiment reports under `jca` while believing it ran under `jca_android`. **Decision: add `jca_android` to the accepted values and to the directory mapping**, so the corrected set is selected by name.

This is the one part of the change that writes Python inside `rv-android`, which the change did not originally do. It is admitted because the alternative is a correctness hazard in exactly the set this change exists to correct.

### D-S6 — the empirical verification of the two hot specifications is last, and is not relaxed

The corrected allow-list of `SSLContextSpec` and `TrustManagerFactorySpec` is compared against a variable the wrapper collision prevents from being written, so their corrections have no observable effect until issue #100 task 5.3 lands. **Decision: place that verification in the final task group**, and if #100 has not landed, record the task as blocked citing the artefact rather than substituting a weaker check. Every other task in this change is independent of #100.

## API Design

### `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil.isValid(transformation: String) -> boolean`

- **Signature**: identical to the frozen utility's, so `jca_android/CipherSpec.mop` redirects its static import and nothing else — the five call sites stay as they are.
- **Precondition**: none. The transformation string arrives from the monitored application.
- **Postcondition**: returns whether the transformation's algorithm, mode and padding are jointly admissible under the generated API 30 `Cipher` rule — eight algorithms, each with its own admissible modes and, per mode, its admissible paddings. Where the rule places no padding implication on a pair (`AES/ECB`, `AES/CTS`, `DESede/ECB`, `DESede/CTS`, `BLOWFISH/ECB`, `BLOWFISH/CTS`), the padding is unconstrained, which is what the rule says and is a divergence from the frozen class's behaviour rather than an oversight. Comparison folds case on all three components.
- **Error**: a malformed transformation returns `false`, as the frozen utility does; it does not raise, because the call site is a monitor guard.

The tables are class-level and immutable, not method locals rebuilt per call. Parsing is delegated to the frozen utility's `alg`, `mode` and `pad`, which are `public static` and correct and in the same package, so the split of a transformation string is defined in one place for both sets and reached without an import.

`br.unb.cic.mop.jca.util.CipherTransformationUtil` is unchanged, including its two hygiene defects, which are inside the freeze.

### `Property` (enum, `rvsec-core`)

Gains **9** constants for the predicates that have no vocabulary today: `preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA`, `preparedDSA`, `preparedEC`, `generatedManagerFactoryParameters`, `cipheredInputStream` and `cipheredOutputStream`. Nine constants close the eleven edges of the inventory's capability-absent bucket, because `generatedCipher` accounts for three of them — one `ENSURES` in `Cipher` and one `REQUIRES` in each stream rule — and `generatedManagerFactoryParameters` for two. Each new constant lands together with the read that consumes it, in the same task — a constant added without a reader is exactly the defect this change removes.

The additions are admissible under the freeze because no `jca` specification references them: an enum that grows does not change the monitor generated from a set that never names the new members. The readers themselves are `.mop` edits and land in `jca_android` only.

### Predicate inventory (CSV)

`property, kind, file, line, spec, event, snippet` — one row per `ExecutionContext` site, `kind ∈ {WRITE, READ, REMOVE}`. Produced by a committed script over a set's `.mop` files. Two inventories are taken at the start: the `jca` one is the frozen baseline and must be identical at the end of the change, and the `jca_android` one is the working baseline the edits move away from.

### Divergence record

`file, hunk, kind, reason, task` — one row per hunk by which `jca_android` differs from `jca` outside allow-list content. Produced from the set diff and checked against it: a hunk with no row fails, a row with no hunk is stale. `kind` distinguishes a layer-2 repair from a predicate-graph edge from the `CipherSpec` import, so the record answers "which of these differences are platform and which are repair" without re-reading the diff.

## Data Flow

Preparation: the generated rules and the two specification sets → the conformance check produces a verdict per file; the inventory script produces the write/read/remove table for each set. Both are committed before any edit, together with the freeze baseline.

Editing: per file in `jca_android`, apply every defect that file carries → enter the resulting hunks in the divergence record → run the freeze check and the record check → move on. The expected edge count per file comes from the inventory.

Verification: regenerate the `jca_android` inventory → the write/read guard passes or names the offending constant → generate monitors from the derived set and assert no bound event has an all-`fail` transition row → the frozen paths are byte-identical to the base commit and the `jca` inventory is unchanged → every non-allow-list hunk of the set diff is named in the divergence record → `specification_set = "jca_android"` resolves to the derived directory → finally, once #100 lands, the two hot specifications are verified empirically.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| A byte changed under a frozen path | freeze check | Fail the task group | Revert it and re-apply the edit to `jca_android` alone |
| Non-allow-list hunk with no record entry | divergence record check | Fail the task group | Add the entry with its reason, or revert the hunk |
| Record entry naming no hunk | divergence record check | Fail | Remove the stale entry — the edit it described was reverted or never landed |
| Constant written and never read | write/read guard | Fail | Add the reader, or record the omission with its reason |
| Bound event with an all-`fail` transition row | monitor-generation assertion | Fail | Add the event to the `fsm` |
| No generated rule corresponds to a `.mop` | conformance check | Record "no anchor" with the reason | None needed — it is a verdict, not a failure |
| #100 task 5.3 not landed | final task group | Record as blocked citing the artefact | Resume when it lands; do not substitute a weaker check |

## Risks / Trade-offs

- [The frozen set keeps defects that produce spurious reports] → accepted by D-S0 and recorded as knowingly retained; the alternative is making published measurements irreproducible.
- [Comparisons across the sets now confound platform allow-lists with layer-2 repairs, and nothing separates them after the fact] → the sharpest cost of D-S0. Mitigated only partly: the divergence record makes every difference attributable, so a reader can see which is which, but no post-hoc measurement can decompose an observed difference. Any report comparing the sets must say so.
- [Following a derived rule can widen an allow-list] → the derived profile models availability, not recommendation; the caveat is written into the requirement so a falling violation count is not misread as improvement.
- [23 files, one-line edits, high count] → partition by file with expected counts from the inventory; verification is arithmetic, and the freeze and record checks run after every group.
- [A correction could be applied to the frozen set out of habit, since the defect is visibly there] → the freeze check runs after every group and fails on any byte, so the window is one group wide.
- [Two utilities could drift apart as the derived rules are regenerated] → the frozen one is frozen, so drift is one-directional and is the derived one following its rule, which is the intended behaviour rather than a hazard.
- [The inventory could drift from the specifications after the edits] → it is regenerated at verification time and compared against the committed one, for both sets.
- [9 new `Property` constants, closing 11 edges, could repeat the original defect] → each lands with its reader in the same task, and the guard fails on any constant that does not.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Contract | Frozen paths unchanged (INV-INS-109 a) | `git diff` from the base commit over `jca/` and its `CipherTransformationUtil` | 1 check, run per task group |
| Contract | Every non-allow-list hunk recorded (INV-INS-109 b) | Set diff cross-checked against the divergence record, both directions | 1 check, run per task group |
| Contract | Conformance verdict present for all 23 (INV-INS-113) | Assertion over the conformance record | 1 check |
| Contract | Write/read guard (INV-INS-111) | Guard derived from the committed inventory | 1 check |
| Generation | No bound event has an all-`fail` transition row (INV-INS-110) | Assert over the monitor generated from the derived set | 1 check |
| Generation | The frozen set's monitor is unchanged | Compare against the monitor generated at the base commit — this is what proves the additive `Property` constants are invisible to it | 1 check |
| Unit (Java) | The derived utility follows the generated rule | Table-driven test over the eight admitted algorithms, with rejected cases per algorithm | ~20 cases |
| Unit (Python) | `specification_set = "jca_android"` resolves to the derived directory without `custom_specs_dir` | Test beside the existing `get_monitored_operations_config` tests | 2 cases |
| Empirical | The two hot specifications report as intended | Blocked on #100 task 5.3 | 2 checks |

No pinning test is written for the frozen `isValid`. Its behaviour is preserved by the file not being edited, and a test asserting that an unedited function still returns what it returned is verification theatre — the freeze check is the real guarantee.

## Open Questions

- Whether the aliases the 2022 translation added outside upstream — dashless and case variants — are legitimate adaptations to Android provider names or accidental looseness. They are carried over today as declared translation artefacts; the conformance check will list them, and each needs a verdict. Under D-S0 any verdict acts on the derived set only.
- Whether the deliberate deviations from upstream present in both CrySL releases (OAEP with MD5 and without SHA-1; `NoPadding`/`PKCS1Padding` for RSA) are corrected here or recorded for later. Correcting them is deviating from upstream knowingly, which is a different kind of decision from repairing a translation defect. D-S0 narrows but does not settle it: the question is now only whether the derived set corrects them, since the frozen set cannot.
- Whether the two deliberate omissions of the predicate graph stay omissions. The substitution they rest on is half-built: the accepting-state mechanism they were replaced by is never read from any `.mop`, so the set is inert at runtime.
