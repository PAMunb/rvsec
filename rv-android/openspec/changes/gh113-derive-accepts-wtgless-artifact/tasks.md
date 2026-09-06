<!-- This change touches 4 files in a single module (aperv-tool). No subagent
     orchestration: the groups are sequential and small enough for one session.
     Critical path: 1 -> 2 -> 3 -> 4. -->

## 1. Remove the sentinel precondition

- [x] 1.1 Delete the `complete` refusal at `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py:249-253`, together with the three-line comment above it that justifies it ("The sentinel is the producer's 'write finished' bit…"). Keep the non-object check, the `package` check and every `_require_section` call exactly as they are.
- [x] 1.2 Update the `derive()` docstring `Raises:` block (~lines 234-238) so it lists only the surviving causes — non-object document, missing `package`, section of the wrong type. Remove the sentence promising that a truncated analysis must fail generation; it no longer describes the code (P4).
- [x] 1.3 Update the `DerivationError` class docstring at `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py:150-155`, which still opens with "Raised for a missing completion sentinel, a missing package, or a section whose type contradicts the schema". The sentinel clause goes; the other two stay, as does the sentence explaining that a malformed entry inside a well-typed section is skipped rather than raised. This is the second stale promise in the file and it is easy to miss, because it sits on the exception class rather than on `derive()` (P4).
- [x] 1.4 Confirm by grep that no other line of `aperv-tool` reads `document["complete"]` for control flow: `grep -rn 'get("complete")\|\["complete"\]' modules/aperv-tool/src/`. `analysis/static_artifact.py` carries it as a data field and MUST stay untouched.

## 2. Unit tests for the derivation contract

- [x] 2.1 In `modules/aperv-tool/tests/test_derive_mop_artifact.py`, delete the two tests that pin the removed behaviour: the one at line ~266 that does `del document["complete"]` and expects `DerivationError`, and `test_derive_refuses_incomplete_document` at line ~271.
- [x] 2.2 Add `test_derive_accepts_document_without_sentinel`: a well-formed document with `transitions: []` and no `complete` key derives; assert `artifact["wtg"] == {}` and `artifact["stats"]["wtgEdges"] == 0`.
- [x] 2.3 Add `test_derive_accepts_false_sentinel`: the same document with `complete: False` written explicitly derives to bytes identical to 2.2 (compare `serialize_canonical()` output), which also pins that `INV-DRV-05` determinism is unaffected.
- [x] 2.4 Add `test_derive_wtgless_still_derives_widget_sections`: assert that `mopActivities`, `optionsMenus` and `widgets` on a sentinel-less document equal what the same document yields with the sentinel present — those sections come from `reachability` and `windows` and must not depend on the WTG.
- [x] 2.5 Verify the surviving refusals still hold: a document with `complete: True` and no `package` raises `DerivationError`, and a document whose `reachability` is an integer raises `DerivationError`. Add them if the existing suite does not already cover both.
- [x] 2.6 Run `/rv-test-run aperv-tool`

## 3. Repurpose the tool-level tests that used the sentinel as a trigger

- [x] 3.1 In `modules/aperv-tool/tests/test_aperv_tool.py`, change `test_failed_derivation_leaves_no_file` (~line 1550) to trigger `DerivationError` with a section of the wrong type instead of `complete: False`. Keep the three assertions that survive the switch: no `<apk>.mop.json` afterwards, no temporary file left, `RVToolExecutionError` raised. The fourth, `assert "complete" in str(raised.value)` at line ~1559, asserts the old refusal's message and cannot survive it — retarget it at the new trigger (the wrong-typed section names itself in the `DerivationError` message) rather than deleting it, so the test keeps pinning that the cause reaches the caller. Update the inline spec-scenario comment to name the new trigger.
- [x] 3.2 Change `test_mop_arm_derivation_error_raises` (~line 1952) the same way, preserving its assertions that nothing is pushed and the jar is never launched.
- [x] 3.3 Add `test_mop_arm_arms_on_wtgless_document`: run the MOP arm over a source document with populated `reachability` and `windows`, `transitions: []` and no `complete` key; assert the artifact is written and pushed, the task does not fail, and the pushed artifact carries `wtg == {}`. Assert it for `mop_on_llm_off` and for `mop_off_llm_off`, since both declare `mop_data: static_analysis` and both failed before this change.
- [x] 3.4 Run `/rv-test-run aperv-tool`

## 4. Specs, verification and review

- [x] 4.1 Apply the delta from `specs/aperv/spec.md` to `openspec/specs/aperv/spec.md` via `/opsx:sync` — the two MODIFIED requirements, the new `INV-DRV-08`, and the `DerivationError` line in the Data Contracts `Error` block (line ~83), which must stop listing "`complete` absent or false" as a cause.
- [x] 4.1b Apply the delta from `specs/analysis/spec.md` to `openspec/specs/analysis/spec.md` in the same `/opsx:sync` pass — the MODIFIED requirement "Derived MOP Artifact as a Device-Only Consumer" (line ~1622), whose prose declared the sentinel a precondition of derivation and whose scenario "truncated analysis yields no artifact" is replaced by the WTG-less and the unparseable cases. Both capability specs must land together: syncing one without the other leaves the two specs contradicting each other.
- [x] 4.2 Run `/rv-qa-lint-fix aperv-tool`
- [x] 4.3 Run `/rv-verify aperv-tool`
- [x] 4.4 Invoke `/rv-code-reviewer` via Skill tool
- [x] 4.5 Sanity-check against the real corpus: run `derive()` over the 45 sentinel-less JSONs of `RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2` and confirm all 45 derive, that none reports `wtgEdges > 0`, and that 18 report `mopActivities > 0` or `flagged > 0`. This is the measurement the proposal claims; it must be reproduced after the change, not assumed.
