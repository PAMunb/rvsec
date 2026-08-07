<!-- Execution notes:
     - Groups run in order. Group 1 produces the two records everything downstream depends on
       (the conformance verdicts and the predicate inventory); nothing else starts before it.
     - Groups 3 to 5 edit the .mop files one file at a time, applying every defect that file
       carries, and porting each edit to the other set. The parity check (INV-INS-109) runs at the
       end of every group, not once at the end.
     - Group 7 is the only part that depends on issue #100 (its task 5.3, the wrapper-collision
       fix). If that has not landed, task 7.1 is recorded as blocked citing the artefact — the
       criterion is not relaxed and no weaker check is substituted.
     - All source files are in the sibling Java reactor:
       $MOP = $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}
       $CORE = $RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop
       Reference rules are read-only at MetaCrySL/generated/api30/ — that tree is not modified.
     - 46 .mop files are touched. Per-file edit counts come from Group 1's inventory, so each task
       is checked by counting rather than by reading. -->

## 1. Records that everything else depends on

- [ ] 1.1 Regenerate the predicate inventory over one specification set — every `ExecutionContext` write, read and removal with property, file, line, spec, event and snippet — and commit it together with the script that produced it (D-S2)
- [ ] 1.2 Generate the same inventory over the other set and confirm it is identical modulo the directory prefix; a difference here is already a parity violation
- [ ] 1.3 Derive the per-file expected edge counts from the inventory, so each editing task in Groups 3 to 5 carries the number of edges it must close
- [ ] 1.4 Produce the conformance verdict for all 23 `jca_android` specifications against the generated API 30 rules: anchored to a named rule, uncontradicted with the rule that was checked, or no anchor with the reason (D-S4, INV-INS-113). Commit the record with the script
- [ ] 1.5 List, in the conformance record, the aliases the 2022 translation added outside upstream — dashless and case variants carried over as declared translation artefacts — so each can receive a verdict
- [ ] 1.6 Write the parity check: the diff between the two set directories must contain allow-list differences only (INV-INS-109). It runs at the end of every group from here on
- [ ] 1.7 Run the parity check against the current tree and record the baseline — it must already pass

## 2. Cipher transformation tables

- [ ] 2.1 Pin the current `jca` behaviour with a table-driven test over `isValid`: every transformation the current implementation accepts, and a sample of those it rejects
- [ ] 2.2 Parameterise `CipherTransformationUtil.isValid` by a table set selected from the active specification set, with the tables sourced from the derivation and held as immutable class-level data rather than method locals rebuilt per call (D-S3, INV-INS-112)
- [ ] 2.3 Populate the Android table set from the generated `Cipher` rule for API 30 — the eight admitted algorithms with their own mode and padding tables
- [ ] 2.4 Update the `condition(isValid(...))` guards in `CipherSpec.mop` for the new signature, in both sets
- [ ] 2.5 Remove the duplicated `PKCS5PADDING` entries and the commented `rsaECBPaddings` block (P4)
- [ ] 2.6 Run 2.1 again: the `jca` verdicts must be unchanged for every input
- [ ] 2.7 Add the Android table test: an algorithm the derived rule admits is accepted, and the set no longer generates keys for algorithms whose use it rejects
- [ ] 2.8 Run the parity check

## 3. The two hot specifications

- [ ] 3.1 `TrustManagerFactorySpec`: rename the `g3` binding at `:44`, add `g3` to the `fsm`, and correct the three `gtm1` defects at `:62-65` — the wrong `Property` constant at `:65`, the `TrustManager[][]` binding at `:62`, and the `KeyManager[]` return type at `:63` — plus every predicate-graph edge the inventory assigns to this file
- [ ] 3.2 Port 3.1 to the other set, identically
- [ ] 3.3 `SSLContextSpec`: add `returning(SSLContext ctx)` at `:46`, add `unsafe_protocol` to the `fsm`, and close the three unread `REQUIRES` the inventory assigns to this file
- [ ] 3.4 Port 3.3 to the other set, identically
- [ ] 3.5 Generate monitors from both sets and assert that no bound event has an all-`fail` transition row (INV-INS-110) — this is what proves the `fsm` half of the correction landed
- [ ] 3.6 Run the parity check

## 4. Predicate graph — `.mop` only

- [ ] 4.1 Correct the remaining translation defects, one file at a time, applying every edge the inventory assigns to that file — including the wrong constant at `KeyPairSpec.mop:38`
- [ ] 4.2 Port each file's edits to the other set as it is completed, not in a batch at the end
- [ ] 4.3 Record the two deliberate omissions with their reason, including that the accepting-state mechanism they were replaced by is never read from any `.mop` and is therefore inert at runtime
- [ ] 4.4 Record `randomized[lSeed]` as inexpressible — a provenance predicate over a primitive cannot be represented by a map keyed on `equals` — together with the matching unsoundness on the write side, where marking small `int` values as randomised marks every equal literal in the process through the boxed-integer cache
- [ ] 4.5 Run the parity check

## 5. Predicate graph — new vocabulary

- [ ] 5.1 Add each of the 11 `Property` constants **together with the read that consumes it**, in the same task; a constant added without a reader is the defect this change removes
- [ ] 5.2 Port each specification-side edit to the other set
- [ ] 5.3 Regenerate the inventory and confirm every new constant has both a writer and a reader
- [ ] 5.4 Run the parity check

## 6. Guards and records

- [ ] 6.1 Write the write/read guard: it reads the committed inventory and the specifications, recomputes the pairing, and fails on any constant written and neither read nor listed in the deliberate-omission list (D-S5, INV-INS-111)
- [ ] 6.2 Commit the deliberate-omission list as versioned data beside the inventory
- [ ] 6.3 Run the guard against both sets; it must pass, and it must fail if a constant is deliberately mistyped in a scratch copy
- [ ] 6.4 Regenerate the inventory after all edits and diff it against the Group 1 baseline; every difference must correspond to a task in this change
- [ ] 6.5 Record in the replication package that exact reproduction of the published numbers no longer holds, and why (decision D1)
- [ ] 6.6 Record that the derived Android profile models availability rather than recommendation — `MessageDigest` admits `MD5` and `SHA-1` — so a fall in the violation count across the sets is not evidence of better analysed code

## 7. Empirical verification — depends on issue #100

- [ ] 7.1 Once issue #100 task 5.3 (wrapper registry key) has landed, verify empirically that the corrected `TrustManagerFactorySpec` and `SSLContextSpec` report as intended. If it has not landed, record this task as blocked citing the artefact — do not substitute a weaker check (D-S6)
- [ ] 7.2 Confirm the corrected allow-lists become observable, in particular that the `SSLContextSpec` label stops depending on a variable that is never written

## 8. Verification

- [ ] 8.1 Build the sibling reactor from its root and confirm both specification sets generate monitors without error
- [ ] 8.2 Run the full conformance record check: 23 of 23 verdicts present, no blanks (INV-INS-113)
- [ ] 8.3 Run the parity check a final time (INV-INS-109)
- [ ] 8.4 Run `/rv-qa-lint-fix rv-monitor-generator` for any Python touched by the verification scripts
- [ ] 8.5 Run `/rv-verify rv-monitor-generator`
- [ ] 8.6 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 8.7 Run `/rv-docs-sync rv-monitor-generator` if module docs need updating
