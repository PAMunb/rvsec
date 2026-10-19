<!-- Subagent dispatch plan. The main session orchestrates; each subagent edits only its group's files.
     - Groups 1, 2 and 3 are independent and run in parallel, one subagent each:
         Group 1 owns RvsecStamp.java, RvsecStampCallbackTest.java and its fixtures (rvsec Java);
         Group 2 owns derive_mop_artifact.py and test_derive_mop_artifact.py (aperv-tool);
         Group 3 owns the .md docs.
     - Group 4 (main) integrates after Groups 1 and 2: worktree build, all tests, the A/B equivalence check.
     - Group 5 (lint, verify, review) runs after Group 4: the test before the review.
     - Critical path: 1 -> 4 -> 5.
     - Every subagent prompt MUST forbid git commands that change state (stash, checkout, switch, restore,
       reset, branch, rebase, merge, clean, commit); only diff/status/log/show/grep are allowed.
     - Work only in the worktree /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-stamp/callback
       (branch wip/stamp-callback, based on isolate-guidance-groups c6865a73). Never touch the `modules` branch or the
       main tree at workspace-rv/rvsec, and never `mvn install` (it would overwrite SNAPSHOTs in the shared local repo).
     - No emulator, no device run, no campaign. Never compare with or run the ajc weaver. -->

## 1. Stamp: app callback behind a library dispatcher (subagent A — rvsec Java)

- [x] 1.1 Check `RvsecStamp.callback()` and its helpers (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java`) against INV-INS-181 step by step: the app-class test, the order (a)–(d), the `NavigationView`/`NavigationBarView` result with no further step, the toolbar fallback to the options menu, and the options-menu rule. Report every difference; change the code only where the spec delta and the code disagree, and keep the resolution logic otherwise as it ran in the A/B.
- [x] 1.2 Check `Delegate.onInitializeAccessibilityNodeInfo` against amended INV-INS-178/179: the substitution happens only for a non-null `click`, the lookup is inside `catch (Throwable)`, and `kind=callback` is logged once per change of the resolved class, with the fields of the instrumentation delta's Data Contracts.
- [x] 1.3 Javadoc and comments in current-state terms (P4): no mention of the A/B or of "the patched stamp"; the `callback()` Javadoc states the resolution order and the R8 limit. The source still compiles at `-source 1.8` against `android.jar` alone.
- [x] 1.4 Review `monitor-builder/src/test/java/br/unb/cic/rv/builder/RvsecStampCallbackTest.java` (7 tests) against the JVM-testable scenarios of the instrumentation delta: the preference chain (click → change → tree-click), the menu-provider and options-menu paths, the app-bound listener not looked behind, a throwing read keeping the listener's class. Add a test for each gap that needs no real `View`; list in the report the scenarios left to the device (menu item, navigation, toolbar, dialog).
- [x] 1.5 Run `mvn -o test -DskipMopAgent -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder` from the worktree root with `JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem` and record the counts.

## 2. Derive: callback methods fill `click` (subagent B — aperv-tool)

- [x] 2.1 In `rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`, add the eight callback names to `HANDLER_METHOD_PATTERN` and a module constant mapping each name to its parameter list (INV-DRV-11; design D6). In `_handler_events`, map an exact name and parameter-list match to `(CLICK_EVENT_TYPE,)`. `onClick(android.content.DialogInterface,int)` shares the name with `onClick(android.view.View)` and is told apart by its parameter list.
- [x] 2.2 Rewrite the comment above `HANDLER_METHOD_PATTERN` and the `_handler_events` docstring in current-state terms: which methods the stamp names and why each fills its event. No mention of the A/B, of `experimento-stampcb` or of an experiment copy.
- [x] 2.3 Add the three scenarios of the `aperv` delta to `rv-android/modules/aperv-tool/tests/test_derive_mop_artifact.py`: the callbacks are recorded under `click` with their pairs; a callback name with another parameter list is not a handler; a class with `onClick(View)` and `onOptionsItemSelected(MenuItem)` merges both into one `click` record (OR of flags, minimum per target). Update `test_derive_cryptoapp_ground_truth` to the four `handlers` keys of the delta's cryptoapp scenario.
- [x] 2.4 Check that `derive()` on the six A/B documents (`rvsec-study03-replication-package/data/raw/e6-corpus/<apk>.json`, each under 5 MB) gives the same `handlers` as the A/B treatment derive (`experimento-stampcb/mount/treatment/derive_mop_artifact.py`), and the same output as the control derive for every other member. Use a scratchpad script; report any difference.
- [x] 2.5 Run `/rv-test-run aperv-tool` (pytest with `--import-mode=importlib -o "addopts="`).

## 3. Documentation (subagent C — .md files only)

- [x] 3.1 `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` and `architecture.md`, "Handler stamp": replace the "library dispatchers" limit with the callback resolution and the new known limits of the instrumentation delta (not reached, coarser than the item, renamed library fields), and document the `RVSEC-BIND view kind=callback` line. Current-state wording only (P4).
- [x] 3.2 `rv-android/modules/aperv-tool/CLAUDE.md` and `docs/architecture.md`: where the `handlers` table or its handler methods are described, add the callback methods of INV-DRV-11 and the id-key consequence of design D8. Leave a file unchanged when it does not describe them.
- [x] 3.3 `rv-android/experimento-stampcb/README.md`: add one sentence after "Resultados" pointing to this change as the implementation of option 1, without rewriting the measured results.

## 4. Integration (main session — after 1 and 2)

- [x] 4.1 Build in the worktree only: from the worktree root, with JDK 21 in the prefix, `mvn -o package -DskipMopAgent -DskipTests -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli -am`; confirm that the worktree's `rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` was rewritten and record its sha256. No `install`.
- [x] 4.2 From the worktree root, with `JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem` in the prefix, run `mvn -o test -DskipMopAgent -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder,rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator` and record the counts; nothing may be skipped.
- [x] 4.3 A/B equivalence: compare `br/unb/cic/rv/builder/stamp/RvsecStamp.java` inside the new `instr-cli.jar` with the one inside `experimento-stampcb/jar/instr-cli-treatment.jar`. If they differ only in comments, record that the A/B is the device evidence for the device scenario of the instrumentation delta. If any statement differs, stop and ask the researcher whether a device smoke is run; do not run one without that answer.
- [x] 4.4 Run `openspec validate gh-tbd-stamp-app-callback`.

## 5. Verification and review (main session — after 4)

- [x] 5.1 Run `/rv-qa-lint-fix aperv-tool`
- [x] 5.2 Run `/rv-verify aperv-tool`
- [x] 5.3 Invoke `/rv-code-reviewer` via the Skill tool over the diff of this change (stamp, derive, tests, docs, OpenSpec artifacts)
- [x] 5.4 After group 6, report to the researcher. Commit only when asked, by path (`git commit -- <paths>`), on `wip/stamp-callback`, with no co-author trailer. Archive only after `isolate-guidance-groups` is archived (design D9).

## 6. Declaring-class callback (D10) — after the first review, before the re-review

- [x] 6.1 (subagent A) In `RvsecStamp.java`, `optionsMenuCallback` returns the nearest app class of the activity's hierarchy that declares `onOptionsItemSelected(android.view.MenuItem)`, and `preferenceCallback`'s tree-click step returns the nearest app class of the tree-click listener's hierarchy that declares `onPreferenceTreeClick(androidx.preference.Preference)`, else `null` (INV-INS-181, design D10). Javadoc follows. Source still compiles at `-source 1.8` against `android.jar` alone.
- [x] 6.2 (subagent A) Tests in `RvsecStampCallbackTest`: an activity allocated without a constructor whose base app class declares `onOptionsItemSelected(MenuItem)` resolves to the base; a one-parameter `onOptionsItemSelected(int)` does not count; a tree-click fragment that declares `onPreferenceTreeClick(Preference)` is named, one that does not resolves to `null`. Run `mvn -o test -DskipMopAgent -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder` from the worktree root with the JDK 21 prefix.
- [x] 6.3 (subagent C) Update the dexlib2 `CLAUDE.md` and `architecture.md` text of the options-menu and tree-click rules to D10.
- [x] 6.4 (main) Repeat 4.1, 4.2 and 4.4; record the new `instr-cli.jar` sha256.
- [x] 6.5 (main) Device smoke, approved by the researcher on 2026-10-19 (`experimento-stampcb/smoke-d10/`): instrument `app.michaelwuensch.bitbanana_79.apk` with `--stamp-handlers` by the A/B treatment jar with only `RvsecStamp.java` replaced by the 6.1 source (`smoke-d10/jar/instr-cli-d10.jar`, so the stamp is the only difference from the A/B), check that only the monitor DEX differs from the A/B treatment APK, place its `.apk.json` beside it, and run `aperv:mop`, 1 repetition × 300 s, through `rv-experiment` (the platform manages the emulator). Pass: at least one `RVSEC-BIND view kind=callback` line, a `callback=app.michaelwuensch.bitbanana.baseClasses.BaseAppCompatActivity` line if the up button is reached, no line naming a `BaseAppCompatActivity` subclass as the callback, no crash with a `mop.RvsecStamp` frame, no `VerifyError`. Result: 86 `kind=callback` lines naming 17 classes, all keys of the derived `handlers` (13 lines name `BaseAppCompatActivity`), none naming a subclass that inherits its callback, no `mop.RvsecStamp` frame, no `VerifyError`; the one crash is the app's (`WatchtowerDetailsActivity` launched without its extra).
- [x] 6.6 (main) Re-run 5.1–5.3 over the D10 diff.
