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
| `ExecutionContext` | The predicate store, keyed by object identity so it agrees with the monitor index | writes from `.mop` | reads from `.mop` |
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
| Event Membership in the Automaton | `fsm` rows in `jca_android` for all 18 all-`fail` events — `TrustManagerFactorySpec` and `SSLContextSpec` in Group 3, the other 16 over 8 files in Group 3b | generated monitor's transition table has no all-`fail` row for a bound event |
| INV-INS-110 | same | monitor-generation assertion over the derived set, run once after Group 3b |
| Cipher Tables of the Derived Set | new `jca/util/AndroidCipherTransformationUtil` | Android verdicts follow the derived rule; the frozen class is untouched |
| INV-INS-112 | same | no hand-maintained table, and no runtime selection over a shared one |
| Predicate Contract | `Property.java` + `jca_android` `.mop` reads | write/read guard derived from the inventory |
| Events are 1:1 with the rule's events | fused pointcuts split in four files | the regenerated monitor's alphabet matches the rule's event count, and INV-INS-110 still holds |
| Predicate store agrees with the monitor index | identity-keyed `ExecutionContext` | two `equals` objects do not share a mark |
| Shared repair does not branch by set | one `ExecutionContext` for both sets | no `specification_set` reaches `rvsec-core` |
| INV-INS-111 | write/read guard | fails on a constant written and never read |
| Specification Set Support (FR03) | `specification_set` mapping in `config.py` | `"jca_android"` resolves without `custom_specs_dir` |

## Goals / Non-Goals

**Goals:**

- The derived set free of the layer-2 authoring defects — all eighteen all-`fail` events among them, not only the two that were visible when the change was written — with the frozen set demonstrably untouched.
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

What the freeze covers is **specification content**: the `.mop` files and the transformation tables the frozen `CipherSpec` calls, which together are the instrument's statement of what a misuse is. It does not extend to the runtime the instrument executes on — issue #100 repairs a weaver defect on this same branch, which changes what the frozen set reports without being read as a break of the freeze. D-S10 settles the one shared-runtime repair this change makes and states the criterion that separates the two.

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

### D-S9 — all eighteen all-`fail` events are repaired, not only the two that were visible

The change was written around two events that can never behave. Writing task 3.4's check — the INV-INS-110 assertion over a generated monitor — showed the frozen set has **eighteen**, of which sixteen remain in the derived set after Group 3, in eight specifications this change had not planned to touch: `IvParameterSpecSpec.c3`/`c4`, `KeyPairGeneratorSpec.initError`, `MessageDigestSpec.reset`, `PBEKeySpecSpec.f1`/`f2`/`err1`/`err2`/`err3`, `PBEParameterSpecSpec.c3`, `SecretKeySpecSpec.c3`/`c4`, `SecureRandomSpec.c3`/`g4`/`setSeed3`, `SignatureSpec.g3`.

They are one pattern, not sixteen accidents. Fifteen of them are error-reporting events whose guard is a negation or a violation — `condition(!ExecutionContext.instance().validate(...))`, `condition(!algorithms.contains(alg))` — which do their reporting in the event body and were never given a row in the automaton. Each is the violating branch of an event the CrySL rule states once: the translation split `c1: PBEKeySpec(password, salt, iterationCount, keylength)` into a conforming `c1` and three violating `err1`/`err2`/`err3`, and only the conforming half reached the automaton. Most of them bind the monitored object, so the automaton does see them fire, from whatever state the object is in, and sends it to `fail`. The report the author intended then arrives accompanied by an `InvalidSequenceOfMethodCalls` that no one authored.

The sixteenth, `MessageDigestSpec.reset`, is not of that shape and is treated separately below.

In the published corpus the eight specifications carry 23,292 `InvalidSequenceOfMethodCalls` and the two of Group 3 carry 26,525 — together 49,817 of 70,760, **70.4% of the category and 51.3% of all 97,018 reported errors**. That number is a **ceiling on what the eighteen events can explain, not a measurement of what they caused.** The `@fail` handler emits no message identifying the event that triggered it, so the published record cannot separate an error caused by one of the eighteen from an error caused by the same specification's language being left legitimately — `MessageDigestSpec` also accuses `digest()` without a preceding `update()`, which is ordinary code and has nothing to do with `reset`. Deciding the split would require re-measuring the corpus, which this change does not do.

Two ways to close it. Narrow INV-INS-110 to the two events the change named and record the sixteen as a finding for later; or repair all sixteen here.

**Decision: repair all sixteen, in the derived set, as Group 3b.** The repair is not new work — it is the `unsafeAlg` idiom Group 3 already established, applied sixteen more times, one file per task with the events named so completion is counted rather than reviewed. Against that, a carve-out would leave the invariant true only of the part of the set someone happened to look at, and would leave the dominant error type of the dataset misattributed with the mechanism already known and written down.

**INV-INS-110 is not weakened.** Repairing all sixteen is exactly what makes it true of the derived set as authored, so it keeps its full form: an event in a specification's event list must appear in that specification's automaton. The invariant does not acquire an exception list, and a carve-out would have been the only alternative reading of the same evidence.

**The repair form is the one Group 3 established, and it is not stricter.** Fourteen of the sixteen live in specifications whose automaton is an `ere`, where the shape the set already uses for a violating branch is a Kleene prefix on that branch — `(g3* g1 | g3* g2)` in `MacSpec`, `KeyGeneratorSpec`, `KeyStoreSpec` and `MessageDigestSpec`, whose own comment says it exists precisely so the unsafe branch stops emitting `InvalidSequenceOfMethodCalls`. It is the `ere` counterpart of the `unsafeAlg` state of `CipherSpec`, `KeyManagerFactorySpec` and, since Group 3, `TrustManagerFactorySpec` and `SSLContextSpec`. Applying it here needs no automaton to be re-derived: each file takes one line.

The alternative considered was an absorbing state — the violating event poisons the object and nothing afterwards can accuse it, which an `fsm` can express and an `ere` cannot. It was **rejected**, for two reasons that only became visible by reading the repair Group 3 had already landed. First, it is stricter than that repair: `TrustManagerFactorySpec`'s `unsafeAlg` admits `g1`, `g2` and `g3` and nothing else, so `getInstance` with an unlisted algorithm followed by `init` still reaches `fail`. Adopting absorption for four files would leave the set with two repair philosophies and a divergence record that has to explain which file got which. Second, absorption trades a false positive for a false negative: after poisoning, a genuine misuse of the same object — `sign()` with no preceding `update()` — goes unreported.

What this leaves standing is a residue, and it is recorded rather than repaired: in every specification of the set, the state reached by a violating branch does not admit the calls that legitimately follow it, so the accusation is removed from the violating call itself and reappears one call later. That is a property of the whole set — `CipherSpec`, `KeyManagerFactorySpec`, `MacSpec`, `KeyGeneratorSpec`, `KeyStoreSpec`, the two files of Group 3 and the seven of Group 3b — and predates this change. Group 3b does not widen it and does not narrow it. It belongs in the frozen set's debt list and in an issue of its own, not inside a change scoped to INV-INS-110, which asks only that a bound event have a row that is not `fail` from every state.

**`MessageDigestSpec.reset` is removed rather than placed.** It is the one of the sixteen that is not a violating branch. No generated rule models it: `MessageDigest.cryptsl` for API 30 declares `getInstance`, `update` and `digest` and nothing else, so CogniCrypt ignores `reset()` calls entirely. Its `.mop` event has an empty body — it writes no property, reads none, reports nothing — and it is absent from the `ere`. The whole of its effect is therefore the all-`fail` row: a legitimate API call becomes a sequence violation and the monitor is reset. Placing it in the automaton would mean deciding, without the rule's support, where `reset()` belongs in the order; the rule's answer is that it belongs nowhere because it is not modelled. Removing the event restores exactly the generated rule's behaviour, and it is entered in the divergence record as a removal with the rule as its reason. (MetaCrySL does model `reset` for a different family, the BouncyCastle digests, and there too it is declared in `EVENTS` and left out of the `ORDER` — the same shape as this defect, one level up.)

Two things this decision inherits from how the sixteen were found, and they belong in the design rather than in a task note. First, `PBEKeySpecSpec.f1` and `f2` carry the Group 3 binding defect as well — neither has a `returning` clause, so both land in the empty parameter slice — and therefore need both halves, the binding and the `fsm`, as `TrustManagerFactorySpec.gtm1` did. Second, the check that found them passed the frozen set until it was taught that events landing in the empty parameter slice generate an `AbstractSynchronizedMonitor` rather than an `AbstractAtomicMonitor`, which is precisely where the defective events live. A check that agrees with a set known to be defective is a bug in the check, so the frozen set — where the answer is known to be 18 — is the baseline every extension of it is run against first.

### D-S10 — the predicate store is keyed by identity, in the shared class

Two halves of one mechanism disagree about what "the same object" means, and the disagreement is what makes the predicate graph report wrongly even where every edge is correctly written and correctly read.

The monitor index keys by **identity**. `CachedWeakReference` caches `System.identityHashCode(ref)` at construction, and the lookup confirms the match with `key == wref.get()` in `BucketNode.findByStrongRef`. So JavaMOP hands a specification one monitor per instance, and it never confuses two instances however alike they are.

`ExecutionContext` keys by **`equals`**. Its store is a `Map<Property, Set<Object>>` over `HashSet`, as are `acceptingState` and the set `hasEnsuredPredicate` scans. So the facts those per-instance monitors record about their own object land in a store that cannot tell two equal objects apart.

The failure is three-sided and quiet in each direction. A write over an object equal to one already stored adds nothing, so two monitors share one mark. A read succeeds for an object no monitored sequence ever produced, as long as an equal one was produced — the `REQUIRES` reports satisfied when it is not, which is a false negative in exactly the clauses this change exists to connect. And a removal in one monitor's `@fail` takes the mark belonging to another monitor's object.

It bites only where `equals` is value-based, which makes the affected surface enumerable rather than hypothetical. Across the frozen set's 27 reads, eight change their answer:

| read | object | why it is affected |
|---|---|---|
| `CipherSpec.i2` (three reads) | `java.security.Key` | `SecretKeySpec.equals` compares key material and algorithm |
| `MacSpec.i1`, `MacSpec.i2` | `java.security.Key` | same |
| `SecretKeySpec.e1` | `SecretKey` | same |
| `SecureRandomSpec` seed reads | `long` | boxed; the `Integer` cache makes equal small values one object |
| `RandomStringPasswordSpec.vo`, `.gb` | `String` | value equality |

The remaining reads are over `byte[]` and `char[]`, whose `equals` is already identity, and are unaffected. The direction is uniform: today an unmarked object validates because an equal marked one exists, so identity keying makes the store **stricter** and the sets report more, not less. The case it closes is concrete — `SecretKeySpecSpec` writes `GENERATED_KEY` over the spec it accepted, and an application that builds a second `SecretKeySpec` with the same material through the *violating* branch has that second one validated at `Cipher.init` by the first.

**Decision: re-key `ExecutionContext` by identity, in the shared class.** `IdentityHashMap` is Java 1.4 and Android API 1, and `Collections.newSetFromMap` is Java 6 and API 9, so neither is a modern-language dependency of the kind that has caused trouble here before; where API 1 is wanted, an `IdentityHashMap<Object, Boolean>` serves directly. `acceptingState` and the scan behind `hasEnsuredPredicate` carry the same defect and are re-keyed with it.

A sibling class was considered, on the D-S3 precedent, and rejected. D-S3 gave the derived set its own transformation tables because the *tables themselves* differ between the sets — the derivation computes them per API level. Here nothing differs: an `equals`-keyed store is wrong for both sets in the same way. Duplicating it would rename some eighty-five call sites across the derived `.mop` files, flood the divergence record with mechanical hunks, and leave a second store whose only distinguishing feature is a defect.

**This is not a deviation from D-S0.** D-S0 freezes the specification set — the `.mop` content and the transformation tables the frozen `CipherSpec` calls — because that is where the instrument states what a misuse is. It does not freeze the runtime the instrument executes on. Issue #100 is repairing a weaver defect on this same branch, which also changes what the frozen set reports, and that was never read as breaking the freeze; a defect in the shared predicate store stands on the same footing. What D-S0 forbids is a correction of *specification content* landing in `jca`, and none does.

What follows from it is recorded rather than mitigated: the eight reads above are the observable surface, and any later comparison against the published numbers has to know the store changed underneath them.

**The delta's own prohibition was too wide and is narrowed rather than excepted.** The requirement text said that a change to a symbol the frozen set already references "does not qualify, however narrow". It was protecting against the D-S3 hazard — shared code made to behave differently depending on which set is active, which would put the frozen set's verdict under state set elsewhere — and over-generalised into a rule that would forbid repairing any defect in `rvsec-core`, the weaver defect of issue #100 included. The criterion it should state is the one it was actually protecting: **shared code MUST NOT branch on the active specification set.** A repair that applies equally to both sets is admissible, and its effect on the frozen set is enumerated rather than assumed absent.

**A blind spot this exposes, named rather than closed.** Task 5.2 checks that the monitor generated from `jca` is unchanged against the base commit. That check still passes after this decision, because `ExecutionContext` is a separate class and the generated monitor source does not mention its internals. Byte-identity of the frozen paths and of the generated monitor therefore does not establish that the frozen set *behaves* as it did. Closing the gap would mean re-measuring the corpus, which is an explicit non-goal, so INV-INS-109 states the limit instead of pretending to cover it.

**The one-argument `remove(Property)` is a separate defect, and identity keying does not touch it.** It deletes the entire set for a property (`ExecutionContext.java:50`, already `@Deprecated`), so one monitor's `@fail` erases every other monitor's mark for that predicate. Four sites carry it in the derived set — `KeyManagerFactorySpec:91`, `MacSpec:87` and `TrustManagerFactorySpec:117-118` — and it now matters, because Group 3 made `SSLContextSpec.init` read `GENERATED_TRUST_MANAGERS`, so one failing factory produces a false `UnsatisfiedConstraint` for every other. That defect *is* specification content, so it is repaired in `jca_android` alone and recorded in the divergence record, exactly as D-S0 requires. Three of the four need a monitor field to hold the object being unmarked, because the value is a local of the event that wrote it.

### D-S11 — event granularity follows the rule's bindings, not its signatures

Four of Group 4's twenty edges, and two of Group 5's, fall on arguments that no pointcut binds. They are unreachable not because the translation forgot to read them but because it destroyed the events that carry them.

CrySL declares **one event per method signature**, with parameters named and typed in `OBJECTS`. The generated `Cipher` rule states eight init events, which are exactly the eight `Cipher.init` overloads Android publishes, and the names are not interchangeable: `params` is `AlgorithmParameterSpec` and `param` is `AlgorithmParameters`, and the `REQUIRES` gives each a *different* predicate — `preparedIV`/`preparedGCM` over the first, `preparedAlg` over the second. Only after the events does the rule define aggregates over them, `IWOIV := i1 | i2 | i3 | i8` and `IWIV := i4 | i5 | i6 | i7`, with `Inits := IWOIV | IWIV`; CogniCrypt resolves each event to a concrete method signature and binds its arguments positionally and statically.

The translation kept the aggregate and dropped the events: `Inits` became two pointcuts with `..`. The fusion survived because for the `ORDER` it is **lossless** — the `ORDER` mentions only `Inits`, never `i4` — so nothing in the part of the rule the automaton models looks wrong. What it loses is everything that quantifies over individual events:

| the rule states | needs bound | modelled today |
|---|---|---|
| `REQUIRES randomized[ranGen]` | `ranGen` (i2, i6, i7, i8) | no |
| `REQUIRES preparedIV[params]`, `preparedGCM[params]` | `params` (i4, i6) | no |
| `REQUIRES preparedAlg[param, …]` | `param` (i5, i7) | no |
| `… && encmode != 1 => noCallTo(IWOIV)` | the named subset itself | no |
| `… && encmode == 1 => callTo(iv)` | a `getIV()` event, absent from the `.mop` | no |

The first three are this change's edges. The last two are `CONSTRAINTS` and outside its scope, and they are listed here because they establish that the rule's granularity is structural rather than stylistic: a rule can only say "with a CBC-family mode in a decrypt, do not call an init without an IV" because *init without an IV* is a named subset of its events. Fusing the events removes the ability to state it at all.

**Decision: one event per distinct binding profile, not one event per rule signature.** An event earns a place in a specification's alphabet when it carries a binding or a body no other event carries. Where several of the rule's signatures share a profile, one pointcut covers them — the weaver resolves overloads itself, on owner, method name, return type and parameter types, with `T+` subtype-aware and `..` for the tail, so overload granularity is free at weave time and buys nothing when spent.

This is a revision. The decision first written here was to transcribe 1:1 with the rule, and for three of its four applications that is what a binding profile analysis produces anyway: `KeyGeneratorSpec` (init 1 → 5), `KeyManagerFactorySpec` (init 1 → 2) and `TrustManagerFactorySpec` (init 1 → 2) are all landed and validated under it. **`CipherSpec` is the exception, and it is narrowed here, because the literal transcription is not executable.**

The reason is a hard limit in the monitor generator, measured rather than inferred. Every `(state, event)` pair a specification does not declare is sent to `fail`, and a `.mop` with an `@fail` handler makes `fail` a category, so `FSMCoenables` walks backwards from a state to which everything is co-reachable and records **the full powerset of the alphabet**: exactly `n × (2ⁿ − 1)` sets, confirmed to the unit at `n=17` (2,228,207) and `n=18` (4,718,574). At 17 events `CipherSpec` generates in 53 s and 3.3 GB; at 18 it dies with a `StackOverflowError` inside `EnableSet.parseSets`, whose regex has nested quantifiers and recurses once per repetition over a 184 MB string; the launcher already passes `-Xss1g` and the JVM refuses to start above it. At the 24 events a 1:1 transcription needs, the coenable string would run to roughly 1.5 × 10¹⁰ characters against Java's maximum `String` length of 2³¹ − 1, so it is not slow — it cannot be built. Rewriting the automaton as an `ere` does not help: `EREPlugin` rewrites into `fsm` and the logic repository re-dispatches it, so `ere`, `ltl` and `ptltl` all reach the same `FSMCoenables` — measured identical counts, identical wall-clock and the identical failure. **The ceiling is 17 events, and `CipherSpec` is already standing on it.** INV-INS-115 states it as a constraint on specification design, and D-S12 records why the generator is not repaired instead.

So `CipherSpec` is re-budgeted rather than transcribed. Grouping the rule's events by binding profile and then by arity yields **14 events** where the specification has 17 and the literal transcription needs 24, and it binds every argument the rule's clauses quantify over — `ranGen`, `params`, `param` and `plainText` all become reachable. Each candidate pointcut was verified with the production `PointcutMatcher` against all 28 `javax.crypto.Cipher` members published by `android-30/android.jar`: the three `init` candidates partition all eight overloads, the five `doFinal` candidates partition all seven, and nothing reaches `updateAAD`, `unwrap` or `getIV`. It generates in 6.1 s and 1.0 GB.

Two defects fall out of the same table at no cost in slots. `byte[] doFinal(..)` matches `f1`, `f2` **and** `f4`, so a plain `doFinal()` takes two transitions and the rule's `f4` has no event of its own; the replacement candidates are disjoint. And the invalid-transformation event is `getInstance(String)`, arity 1, so `getInstance(transformation, provider)` over an unsafe algorithm fires nothing at all and is later misreported as a sequence violation rather than as `UnsafeAlgorithm`; `getInstance(String, ..)` closes it.

**What this costs, stated plainly, because the earlier decision rejected it.** Discrimination between overloads moves out of the pointcut and into an `instanceof` in the event body — the very idiom task 3.1 used in `TrustManagerFactorySpec` and that this decision previously ruled out. Two of the three objections to it stand and are what shape the design: it is inapplicable across arities, since `args(a, b, third, ..)` requires arity ≥ 3 and drops the shorter overload out of the automaton entirely, and inapplicable to a primitive, since `Object+` rejects `int` — which is why the candidates are grouped by arity first and why `KeyGeneratorSpec` still needs its five events. The third objection, that it re-creates at runtime a distinction the pointcut makes statically, is true and is now accepted as the price: the predicate reads are identical either way, and the `ORDER` never distinguished the events, so what is lost is a static guarantee about *which* overload was called, not any clause of the rule. Where a fused event spans two of the rule's aggregates — one candidate covers members of both `IWOIV` and `IWIV` — that is recorded, since `noCallTo(IWOIV)` would need the same `instanceof` to be recovered if it ever comes into scope.

**`TrustManagerFactorySpec` is retrofitted rather than left as the exception.** The `Object`-and-`instanceof` idiom is correct there, because its two overloads happen to share an arity and take reference types, but it is a special case of the general form rather than a second philosophy. Leaving it would make the set explain, file by file, which of two shapes applies; replacing it makes the set 1:1 with the rules throughout and lets Group 5's `generatedManagerFactoryParameters` be bound statically. Its divergence-record entries are rewritten, since their digests change with their content.

**The double firing, for the record.** `CipherSpec.f1` is `call(public byte[] Cipher.doFinal())` and `f2` is `call(public byte[] Cipher.doFinal(..))`. In AspectJ `(..)` matches zero arguments, so a plain `doFinal()` fires **both** events — verified in the generated aspect, `MultiSpec_1MonitorAspect.aj:250` and `:255`, and again with the matcher, which returns `[f1, f2, f4]` for that one pointcut. It is `f4` that binds the `plainText` the `!macced[_, plainText]` clause needs.

### D-S12 — the generator is not repaired; the alphabet is budgeted against its ceiling

The 17-event ceiling comes from a computation that, for this family of specifications, produces nothing. `EnableSet.parseSets` maps the coenable sets to *specification parameters*, and every one of the 23 specifications has at most one; in `CipherSpec` every event carries that same `Cipher c`, so all 2,228,207 sets collapse to a single line in the generated monitor, `//alive_parameters_0 = [Cipher c]`. `OptimizedCoenableSet.optimize` already reaches the same value for free through its `if (enables == null) enables = getFullEnable()` fallback. A repair in `FSMCoenables` that skipped the saturated `fail` category would therefore be verifiable by byte-diffing the monitor generated from the frozen `jca`, which is exactly what task 5.2 checks.

**Decision: do not repair `rv-monitor`.** It is out of this change's scope, it would raise the ceiling only to roughly 20 events — still short of the 24 a literal transcription needs, since the `String` limit is a separate wall — and it enlarges the blast radius of a change whose whole discipline is that the frozen set's instrument does not move. The ceiling is instead **recorded as a measured constraint on specification design**, and the alphabet is budgeted under it.

The method and the two harnesses that produced these numbers live in the `rv-analyze-spec` skill (`.claude/skills/rv-analyze-spec/`, commit `3d093592`): `CoenableProbe` prices a property against the production `FSMCoenables` without generating code, and `PointcutBudget` runs the production `PointcutMatcher` over a class's real overloads and reports coverage, overlap and leakage. Anything asserted here about what a pointcut matches or what a specification costs is reproducible with them.

### D-S13 — `!macced[_, plainText]` is transcribed, and the projection is faithful

The `Cipher` rule requires `!macced[_, plainText]` of its `doFinal` events, and `macced` is produced by the `Mac` rule, which ensures it three times: `macced[output1, inp]`, `macced[output1, pre_input]`, `macced[output2, input]`. It is a **two-place** predicate — `macced[M, D]` says *M is the MAC of D*.

`ExecutionContext` represents one-place predicates only: a `Set<Object>` per `Property`. So the two-place relation had to be projected onto one place, and `MacSpec` projected it onto the **first**: it writes `GENERATED_MAC` over the MAC it produced. The `Cipher` clause quantifies over the **second** — its first place is `_` — so it reads *this plaintext was never MACed*, and there is no set of MACed data to read it against. Binding `plainText`, which task 4.6 now does in `f2` and `f5`, gives the argument and nothing to compare it with. This is a **missing predicate**, not a granularity defect, and it is the one thing the re-budget was expected to fix and does not.

**Decision: transcribe it.** A new `Property` over the MACed data, written where the data enters `MacSpec` and read in `CipherSpec`.

**The projection is faithful, which is why this is a transcription rather than an approximation.** The clause's first place is anonymous, so the one-place projection onto the *second* argument is exactly what it asks for. What a one-place store loses is the ability to say *which* MAC — and this clause does not ask which. That reasoning does not generalise: a clause naming both places would still be inexpressible, and `randomized[lSeed]` remains so for a different reason (task 4.4).

**The cost, measured.** The data enters `MacSpec` at two points that bind nothing today: `event update` is `call(public void Mac.update(..))` with no `args`, and `event f1` fuses `doFinal(byte[])` with `doFinal()`. Android publishes four `update` overloads and three `doFinal`. Under the alphabet-budget method that is about three further events — `update(byte[], ..)` covering the rule's `u2`, `u3` and `u4`, a separate `update(byte)` because `Object+` rejects a primitive, and `doFinal(byte[])` split out of the fused `f1`. `MacSpec` has 8 events, so it lands near 11, comfortably under the ceiling of 17 (INV-INS-115).

**Two residues, recorded rather than mitigated.** `Mac.update(java.nio.ByteBuffer)` is not among the rule's events, so data entering through it is never marked and the clause is silent about it — a false negative. And `update(byte)` marks a boxed primitive, which carries exactly the unsoundness task 4.4 records for `randomized`: inside the `Byte` cache identity and equality coincide, so one MACed byte marks every equal literal in the process.

The two alternatives were put to the user with this material and declined: recording it as inexpressible beside `randomized[lSeed]`, which would have been the cheaper reading of a clause that turns out to be expressible; and reading `!validate(GENERATED_MAC, plainText)`, which is cheap and already available but states a *different* clause — "do not encrypt a MAC" rather than "do not encrypt what you MACed" — and would have had to be recorded as a deliberate divergence rather than as the rule's.

### D-S14 — Group 5 adds one constant; the rest of its bucket is recorded

The inventory's capability-absent bucket has eleven edges over nine predicates, and the plan was to add all nine constants, each with its reader. Checking which of them the derived set can actually *close* changed the answer, and the criterion turns out not to be the CrySL anchor but whether **both ends of the edge are modelled by a `.mop` in this set of 23**.

Six predicates — `preparedAlg`, `preparedRSA`, `preparedDSA`, `generatedManagerFactoryParameters`, `preparedEC`, `preparedOAEP` — have their consumer in the set and their producer outside it: `AlgorithmParameters`, `RSAKeyGenParameterSpec`, `DSAGenParameterSpec`, `CertPathTrustManagerParameters`/`KeyStoreBuilderParameters`, `ECGenParameterSpec` and `OAEPParameterSpec` have no specification here. Every read this change has added sits in an event body rather than a `condition(...)`, precisely so that a failing requirement reports instead of vanishing (D-S9). A body read of a predicate nothing in the set writes therefore fails on every execution and reports every legitimate use. That is not a recorded gap; it is a new defect of the same family this change exists to remove.

Two — `cipheredInputStream` and `cipheredOutputStream` — have their producer in the set and no consumer anywhere: no rule in either CrySL anchor requires them. They would be writes with no reader, which INV-INS-111 forbids unless recorded, and recording them is the honest outcome rather than a reader invented to satisfy the guard.

One is fully expressible: **`generatedCipher`**, produced by `Cipher` and required by both stream rules, all three modelled here. **Decision: Group 5 adds `GENERATED_CIPHER` alone**, and the remaining eight predicates are recorded with the mechanical reason above.

**This reopens task 4.3's deliberate omission, and must.** The predicate's three edges sit in two buckets: the two `REQUIRES` are Group 5's, while the `ENSURES generatedCipher[this]` was recorded as deliberately omitted because `CipherSpec.mop:323` substitutes `setObjectAsInAcceptingState(cipher)` — a mechanism the same record measured as inert, with nineteen writes and no readers of `isInAcceptingState` in either set. Adding the two reads against that producer would reproduce exactly the false-positive trap that disqualifies the other six, so the `ENSURES` becomes a real write of `GENERATED_CIPHER` and task 4.3's record keeps only `generatedMessageDigest`. That one stays omitted under the identical criterion: its consumers would be `DigestInputStream` and `DigestOutputStream`, and neither has a specification here.

**The anchor question is therefore nearly moot.** Of the two predicates the API 30 rules do not name, `preparedOAEP` is excluded for want of a producer regardless of anchor, so the choice decides only `generatedCipher`. The derivation's 33 rules omit `OAEPParameterSpec` altogether, against 47 rules in CrySL 1.5.2 — a matter of corpus coverage rather than of platform, which is the same reasoning that anchored `predicate_edges.csv` to 1.5.2 in the first place.

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

### `ExecutionContext` (singleton, `rvsec-core`)

- **Change**: the three `HashSet<Object>` stores — the per-`Property` sets, `acceptingState`, and the set `hasEnsuredPredicate` scans — become identity-keyed. Every method signature stays as it is, so no `.mop` in either set changes.
- **Postcondition**: `validate(p, o)` is true exactly when `setProperty(p, o)` was called with **that** object and no `remove(p, o)` has taken it since. Two distinct objects that are `equals` no longer share a mark.
- **Why the shared class**: the defect is identical in both sets, so a per-set store would duplicate correct code to isolate a repair neither set benefits from missing (D-S10).
- **Effect on the frozen set**: eight of its 27 reads change answer, all in the direction of reporting more; they are enumerated in D-S10 rather than assumed absent.

### `Property` (enum, `rvsec-core`)

Gains **2** constants: `generatedCipher` and `macced`.

`generatedCipher` closes three edges — the two `REQUIRES` the inventory's capability-absent bucket assigns to the stream specifications, and the `ENSURES` in `CipherSpec` that task 4.3 had recorded as a deliberate omission. It is the only predicate of that bucket's nine whose producing rule *and* consuming rules are all modelled by a specification in this set, which is what makes it the only one addable without inventing a reader or a writer; D-S14 records the criterion and the eight exclusions. `macced` is not from that bucket at all: its edge is counted among Group 4's twenty as a translation defect, because a constant *does* exist for the predicate and simply holds the wrong end of it (D-S13).

The other eight predicates of the bucket gain no constant. Six have no producer in the set, so a reader would report on every execution; two have no consumer in any rule, so a writer would be a write with no reader. Both cases are recorded with their reason rather than approximated, which leaves nine of the bucket's eleven edges open and documented.

Each new constant lands together with the read that consumes it **and** the write that produces it, in the same task — a constant added without a reader is exactly the defect this change removes, and a reader added without a writer is the defect D-S14 refuses to introduce in its place.

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
- [2 new `Property` constants — `generatedCipher` closing 3 edges and `macced` closing one of Group 4's — could repeat the original defect] → each lands with its reader and its writer in the same task, and the guard fails on any constant that does not.
- [Nine of the eleven capability-absent edges stay open, so the derived set still cannot state most of that bucket] → accepted and recorded under D-S14 rather than mitigated, because the six without a producer would report on every execution and the two without a consumer would be writes with no reader. Closing the six needs seven further specifications (`AlgorithmParameters`, `RSAKeyGenParameterSpec`, `DSAGenParameterSpec`, `ECGenParameterSpec`, `OAEPParameterSpec`, `CertPathTrustManagerParameters`, `KeyStoreBuilderParameters`), which is a change of its own and is named as such rather than half-started here.
- [Splitting a fused pointcut could change the automaton's language rather than only its alphabet] → each new event takes exactly the transitions of the event it replaces, and INV-INS-110 is re-run over the regenerated monitor, where every new event must have a row that is not `fail` from every state.
- [Re-keying the shared predicate store changes what the frozen set reports, and the freeze check cannot see it] → the effect is enumerated site by site in D-S10 rather than mitigated, and INV-INS-109 states the limit: byte-identity of the frozen paths and of the generated monitor does not establish unchanged behaviour. Closing the gap would need the corpus re-measured, which is a non-goal.
- [A repair to shared Java could be made to depend on the active specification set, reintroducing the D-S3 hazard] → the criterion is stated as a prohibition on branching, not on touching: shared code may be repaired, and may not behave differently by set.
- [The defect counts written into the tasks were floors, not ceilings — `gtm1` had four defects where three were enumerated, and the all-`fail` pattern eighteen events where two were] → every count in this change comes from a script run over the material rather than from the prose that motivated it, and each such check is run against the frozen set first, where the answer is independently known. A check that agrees with a set known to be defective is a bug in the check, which is how the transition checker was found to be skipping a whole monitor kind.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Contract | Frozen paths unchanged (INV-INS-109 a) | `git diff` from the base commit over `jca/` and its `CipherTransformationUtil` | 1 check, run per task group |
| Contract | Every non-allow-list hunk recorded (INV-INS-109 b) | Set diff cross-checked against the divergence record, both directions | 1 check, run per task group |
| Contract | Conformance verdict present for all 23 (INV-INS-113) | Assertion over the conformance record | 1 check |
| Contract | Write/read guard (INV-INS-111) | Guard derived from the committed inventory | 1 check |
| Generation | No bound event has an all-`fail` transition row (INV-INS-110) | Assert over the monitor generated from the derived set, after Group 3b; the same check over the frozen set must still report 18, which is what proves the check itself still sees both monitor kinds | 1 check, two sets |
| Generation | The frozen set's monitor is unchanged | Compare against the monitor generated at the base commit — this is what proves the additive `Property` constants are invisible to it | 1 check |
| Unit (Java) | The predicate store distinguishes two `equals` objects | Two `SecretKeySpec` with the same material: marking one leaves the other unmarked, and removing one leaves the other marked | 3 cases |
| Unit (Java) | The derived utility follows the generated rule | Table-driven test over the eight admitted algorithms, with rejected cases per algorithm | ~20 cases |
| Unit (Python) | `specification_set = "jca_android"` resolves to the derived directory without `custom_specs_dir` | Test beside the existing `get_monitored_operations_config` tests | 2 cases |
| Empirical | The two hot specifications report as intended | Blocked on #100 task 5.3 | 2 checks |

No pinning test is written for the frozen `isValid`. Its behaviour is preserved by the file not being edited, and a test asserting that an unedited function still returns what it returned is verification theatre — the freeze check is the real guarantee.

## Open Questions

- Whether the aliases the 2022 translation added outside upstream — dashless and case variants — are legitimate adaptations to Android provider names or accidental looseness. They are carried over today as declared translation artefacts; the conformance check will list them, and each needs a verdict. Under D-S0 any verdict acts on the derived set only.
- Whether the deliberate deviations from upstream present in both CrySL releases (OAEP with MD5 and without SHA-1; `NoPadding`/`PKCS1Padding` for RSA) are corrected here or recorded for later. Correcting them is deviating from upstream knowingly, which is a different kind of decision from repairing a translation defect. D-S0 narrows but does not settle it: the question is now only whether the derived set corrects them, since the frozen set cannot.
- Whether the two deliberate omissions of the predicate graph stay omissions. The substitution they rest on is half-built: the accepting-state mechanism they were replaced by is never read from any `.mop`, so the set is inert at runtime.
