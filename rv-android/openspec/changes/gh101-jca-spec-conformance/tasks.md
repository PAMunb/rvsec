<!-- Execution notes:
     - The `jca` set is FROZEN (D-S0). Nothing under $MOP/jca and nothing in
       $CORE/jca/util/CipherTransformationUtil.java changes in this change, however visibly
       defective. Every correction lands in jca_android alone. Base commit for the freeze: 7e7acb69.
     - Groups run in order. Group 1 produces the records everything downstream depends on
       (the conformance verdicts, the two inventories, the freeze baseline); nothing else starts
       before it.
     - Groups 3 to 5 edit the jca_android .mop files one file at a time, applying every defect that
       file carries. Each edit is entered in the divergence record as it lands.
     - Two checks run at the end of every group, not once at the end (INV-INS-109): the freeze check
       (the frozen paths are byte-identical to the base commit) and the divergence-record check
       (every non-allow-list hunk of the set diff is named by an entry, and no entry is stale).
     - Group 8 is the only part that depends on issue #100 (its task 5.3, the wrapper-collision
       fix). If that has not landed, task 8.1 is recorded as blocked citing the artefact — the
       criterion is not relaxed and no weaker check is substituted.
     - Source files, all but one in the sibling Java reactor:
       $MOP  = $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}
       $CORE = $RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop
       Reference rules are read-only at MetaCrySL/generated/api30/ — that tree is not modified.
       The exception is Group 6, which touches rv-experiment's config.py.
     - 23 .mop files are touched, all in jca_android. Per-file edit counts come from Group 1's
       inventory, so each task is checked by counting rather than by reading. -->

## 1. Records that everything else depends on

- [x] 1.1 Regenerate the predicate inventory over `jca_android` — every `ExecutionContext` write, read and removal with property, file, line, spec, event and snippet — and commit it together with the script that produced it (D-S2)
- [x] 1.2 Generate the same inventory over the frozen `jca` set and commit it as the freeze baseline; it must be identical to 1.1 modulo the directory prefix, since no edit has landed yet, and it must still be identical to itself at the end of the change
- [x] 1.3 Derive the per-file expected edge counts from the inventory, so each editing task in Groups 3 to 5 carries the number of edges it must close
- [x] 1.4 Produce the conformance verdict for all 23 `jca_android` specifications against the generated API 30 rules: anchored to a named rule, uncontradicted with the rule that was checked, or no anchor with the reason (D-S4, INV-INS-113). Commit the record with the script
- [x] 1.5 List, in the conformance record, the aliases the 2022 translation added outside upstream — dashless and case variants carried over as declared translation artefacts — so each can receive a verdict. Bring the list to the user: it is one of the two open questions design.md leaves to them
- [x] 1.6 Write the freeze check: `git diff` from the base commit over `$MOP/jca` and `$CORE/jca/util/CipherTransformationUtil.java` must be empty (INV-INS-109 a)
- [x] 1.7 Write the divergence-record check: every hunk of the `jca` vs `jca_android` diff that is not allow-list content must be named by an entry in the record, and every entry must name a hunk that exists (INV-INS-109 b)
- [x] 1.8 Create the divergence record with its current content — the allow-list differences of the ten files that already diverge — and run both checks against the current tree to establish the baseline. The freeze check must pass trivially; the record must have no non-allow-list hunks yet

## 2. Transformation tables for the derived set

- [ ] 2.1 Add `br.unb.cic.mop.jca_android.util.CipherTransformationUtil` with `isValid(String)`, transcribing the eight algorithms of the generated API 30 `Cipher` rule with their per-algorithm mode tables and per-mode padding tables, held as immutable class-level data (D-S3, INV-INS-112)
- [ ] 2.2 Delegate parsing to the frozen utility's `alg`, `mode` and `pad` rather than restating the split, so a transformation string is decomposed in one place for both sets
- [ ] 2.3 Point `jca_android/CipherSpec.mop` at the new utility by changing its import only; the five `condition(isValid(...))` call sites keep their current form
- [ ] 2.4 Table-driven test over the derived utility: each of the eight algorithms admitted with a conforming transformation, and rejected with a non-conforming mode or padding
- [ ] 2.5 Assert the specific contradiction this closes: `ChaCha20`, `DESede`, `BLOWFISH` and `ARC4` are accepted by `KeyGeneratorSpec` and are now also accepted by `CipherSpec` in the derived set
- [ ] 2.6 Record in the divergence record that `jca_android/CipherSpec.mop` diverges from `jca` by its import, with the reason
- [ ] 2.7 Record as knowingly retained, in the frozen set's debt list, the two hygiene defects inside the freeze: `PKCS5PADDING` duplicated for `CBC` and `PCBC`, and the commented `rsaECBPaddings` block
- [ ] 2.8 Run the freeze check and the divergence-record check

## 3. The two hot specifications

- [ ] 3.1 `jca_android/TrustManagerFactorySpec.mop`: rename the `g3` binding at `:44`, add `g3` to the `fsm`, and correct the three `gtm1` defects at `:62-65` — the wrong `Property` constant at `:65`, the `TrustManager[][]` binding at `:62`, and the `KeyManager[]` return type at `:63` — plus every predicate-graph edge the inventory assigns to this file
- [ ] 3.2 `jca_android/SSLContextSpec.mop`: add `returning(SSLContext ctx)` at `:46`, add `unsafe_protocol` to the `fsm`, and close the three unread `REQUIRES` the inventory assigns to this file
- [ ] 3.3 Enter every hunk from 3.1 and 3.2 in the divergence record, each with its reason and this task
- [ ] 3.4 Generate monitors from the derived set and assert that no bound event has an all-`fail` transition row (INV-INS-110) — this is what proves the `fsm` half of the correction landed
- [ ] 3.5 Record in the frozen set's debt list that `jca` retains both defects and the spurious `InvalidSequenceOfMethodCalls` they produce
- [ ] 3.6 Run the freeze check and the divergence-record check

## 4. Predicate graph — `.mop` only

- [ ] 4.1 Correct the remaining translation defects in `jca_android`, one file at a time, applying every edge the inventory assigns to that file — including the wrong constant at `KeyPairSpec.mop:38`
- [ ] 4.2 Enter each file's hunks in the divergence record as that file is completed, not in a batch at the end
- [ ] 4.3 Record the two deliberate omissions with their reason, including that the accepting-state mechanism they were replaced by is never read from any `.mop` and is therefore inert at runtime
- [ ] 4.4 Record `randomized[lSeed]` as inexpressible — a provenance predicate over a primitive cannot be represented by a map keyed on `equals` — together with the matching unsoundness on the write side, where marking small `int` values as randomised marks every equal literal in the process through the boxed-integer cache
- [ ] 4.5 Run the freeze check and the divergence-record check

## 5. Predicate graph — new vocabulary

- [ ] 5.1 Add each of the 11 `Property` constants **together with the read that consumes it** in `jca_android`, in the same task; a constant added without a reader is the defect this change removes
- [ ] 5.2 Confirm the additions are invisible to the frozen set: no `jca` specification references any new constant, and the monitor generated from `jca` is unchanged against the one generated at the base commit
- [ ] 5.3 Enter the specification-side hunks in the divergence record
- [ ] 5.4 Regenerate the `jca_android` inventory and confirm every new constant has both a writer and a reader
- [ ] 5.5 Run the freeze check and the divergence-record check

## 6. The derived set becomes selectable by name

- [ ] 6.1 Add `"jca_android"` to `valid_spec_sets` in `ExperimentConfig.validate()` and to the directory mapping in `get_monitored_operations_config()`, resolving to `{mop_base_dir}/jca_android/` (D-S8)
- [ ] 6.2 Test that `specification_set = "jca_android"` resolves to the derived directory and does not require `custom_specs_dir`
- [ ] 6.3 Check whether any documentation enumerates the accepted values — `CLAUDE.md`, `docs/PRD.md`, `.claude/project-info.md` — and update what does

## 7. Guards and records

- [ ] 7.1 Write the write/read guard: it reads the committed inventory and the specifications, recomputes the pairing, and fails on any constant written and neither read nor listed in the deliberate-omission list (D-S5, INV-INS-111)
- [ ] 7.2 Commit the deliberate-omission list as versioned data beside the inventory
- [ ] 7.3 Run the guard against the derived set; it must pass, and it must fail if a constant is deliberately mistyped in a scratch copy
- [ ] 7.4 Regenerate both inventories after all edits: the `jca_android` one diffed against the Group 1 baseline, where every difference must correspond to a task in this change; the `jca` one identical to its baseline, byte for byte
- [ ] 7.5 Record in the replication package that the published numbers reproduce exactly because the `jca` set was frozen, and that the debt this buys is a set that stays reproducible without being correct (D-S0)
- [ ] 7.6 Record that comparisons of violation counts across the two sets now confound two causes — the platform allow-list and the layer-2 repairs present in the derived set only — and that no post-hoc measurement separates them
- [ ] 7.7 Record that the derived Android profile models availability rather than recommendation — `MessageDigest` admits `MD5` and `SHA-1` — so a fall in the violation count across the sets is not evidence of better analysed code

## 8. Empirical verification — depends on issue #100

- [ ] 8.1 Once issue #100 task 5.3 (wrapper registry key) has landed, verify empirically that the corrected `TrustManagerFactorySpec` and `SSLContextSpec` report as intended under the derived set. If it has not landed, record this task as blocked citing the artefact — do not substitute a weaker check (D-S6)
- [ ] 8.2 Confirm the corrected allow-lists become observable, in particular that the `SSLContextSpec` label stops depending on a variable that is never written

## 9. Verification

- [ ] 9.1 Build the sibling reactor from its root and confirm both specification sets generate monitors without error — coordinating with the gh100 session first, since the reactor and `~/.m2` are shared
- [ ] 9.2 Run the full conformance record check: 23 of 23 verdicts present, no blanks (INV-INS-113)
- [ ] 9.3 Run the freeze check and the divergence-record check a final time (INV-INS-109)
- [ ] 9.4 Run `/rv-qa-lint-fix` for the Python touched — `rv-experiment` and any verification scripts
- [ ] 9.5 Run `/rv-verify rv-experiment`
- [ ] 9.6 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 9.7 Run `/rv-docs-sync` for any module whose docs the Group 6 change makes stale
