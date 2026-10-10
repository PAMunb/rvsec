<!-- Subagent dispatch plan — the main session orchestrates and dispatches; subagents edit only the files of their group.
     - Group 0 (main) runs first: it freezes the baseline jar the equivalence check of Group 4 compares against.
     - Groups 1, 2 and 3 are independent and run in parallel, one subagent each, after Group 0:
         Group 1 owns RvsecStamp.java; Group 2 owns the new test class and its fixtures; Group 3 owns the .md docs.
     - Group 4 (main) integrates: reactor build, all monitor-builder tests, equivalence against the baseline. Needs 1 + 2.
     - Group 5 runs the device smoke after Group 4; its three APKs are instrumented and run in parallel.
     - Group 6 (lint, verify, review, issue, commit) runs after Group 5 — smoke before review.
     - Critical path: 0 -> 1 -> 4 -> 5 -> 6. Group 2's red run (2.4) happens before Group 1 lands; its green run is 4.3.
     - Every subagent prompt MUST forbid git commands that change state (stash, checkout, switch, restore, reset,
       branch, rebase, clean, commit); only diff/status/log/show/grep. The working tree is shared with other sessions.
     - Never compare with or run the ajc weaver. Never start, stop or manage an emulator by hand. -->

## 0. Baseline (main session)

- [x] 0.1 Copy the current `rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` to `rv-android/experimento-smk124/baseline/instr-cli.jar` before any build, and record its sha256 in `experimento-smk124/baseline/SHA256`. The equivalence check of 4.4 compares against this file; it must not live under `/tmp`.

## 1. Helper resolution (subagent A — `RvsecStamp.java` only)

- [x] 1.1 In `composeHandler` (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java`), take the owner from `this$0` when present, otherwise from `f$0` only when `isA(value, "androidx.compose.foundation.AbstractClickableNode")` (spec INV-INS-178 node step; design D1). Keep the `this$0` branch unchecked.
- [x] 1.2 Add `private static Object materialUnwrap(Object handler)` per design "API Design" (class name prefix `androidx.compose.material`, exactly one non-static declared field with declared type name prefix `kotlin.jvm.functions.Function`, non-null value whose class does not start with `androidx.`), with the matching `Field` (or its absence) cached in `MEMBERS` under `<class>#materialFn`; apply it to the handler resolved by the node step, including the action-lambda fallback (design D2).
- [x] 1.3 Update the Javadoc of `composeNode` and `composeHandler` to describe the two steps and why (`f$0` from D8 in foundation ≥ 1.9, the type check, the Material wrapper), in current-state terms (P4). Keep the source compiling at `-source 1.8` against `android.jar` alone, with no androidx/Kotlin type referenced at compile time.

## 2. JVM tests of the Compose resolution (subagent B — new test files only)

- [x] 2.1 Add fixture sources under `monitor-builder/src/test/resources/stamp-fixtures/` (compiled by the test, not by Maven): `androidx.compose.foundation.AbstractClickableNode`, `ClickableNode`, `CombinedClickableNode`, `androidx.compose.foundation.selection.ToggleableNode` with the real field names (`onClick`, `onLongClick`, `onValueChange`); `kotlin.jvm.functions.Function0`/`Function1`; Material wrappers `androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6` (`f$0: Function1`, `f$1: boolean`), `CheckboxKt$Checkbox$1$1` (`$checked`, `$onCheckedChange`), a DatePicker-like wrapper holding an `androidx.` function, and a two-function wrapper; app-like classes outside `androidx.`; a fake configuration/action pair exposing `contains`, `get`, `getAction` (design D3).
- [x] 2.2 Add `monitor-builder/src/test/java/br/unb/cic/rv/builder/RvsecStampComposeTest.java`: compile the source written by `StampSourceEmitter.emit` together with the fixtures against `android.jar` in one `javac` call (`-source 1.8 -target 1.8`), load with a `URLClassLoader` over the output and `android.jar`, and invoke the private static `composeHandler` reflectively. `@EnabledIf("canCompile")` as in `StampSourceEmitterTest`.
- [x] 2.3 Cover every branch listed in design "Mapping": `this$0` owner as before; `f$0` clickable node; `f$0` `ToggleableNode` with `onValueChange`; `f$0` `CombinedClickableNode` long click; `f$0` non-node object with an `onClick` field not read; Checkbox D8 form; Checkbox kotlinc form; wrapper of a library function kept; two-function wrapper kept; non-Material handler not unwrapped; null captured function kept; absent action → `null`. Use the concrete class names of the spec scenarios.
- [x] 2.4 Run the new test class against the unmodified helper (before Group 1 lands, or against `git show HEAD:<RvsecStamp.java>` copied to the scratchpad) and record which tests fail: the `f$0` and Material tests must fail, the `this$0`, non-node and kept-wrapper tests must pass. Report the list to the main session.

## 3. Documentation (subagent C — `.md` files only)

- [x] 3.1 Update the Compose stamp description in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` and `architecture.md` (node step with `this$0`/`f$0` and the type check, Material step, the known limits added by the spec delta). Current-state wording only (P4).
- [x] 3.2 Add a short paragraph to `rv-android/docs/20261009_e03mini-smoke.md` ("Achado 2") pointing to issue #124 and this change as the repair, without rewriting the measured results.

## 4. Integration build and equivalence (main session — after 1 and 2)

- [x] 4.1 Build the reactor: `mvn clean install -o -DskipMopAgent -DskipTests` at the rvsec root with JDK 21 in the prefix; confirm `rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` was rewritten and record its sha256.
- [x] 4.2 Run `mvn -o test` in `rvsec-instrumentation-dexlib2` (all submodules) and record the counts; no test may be skipped by `-DskipTests`.
- [x] 4.3 Confirm `RvsecStampComposeTest` is green and that `StampSourceEmitterTest.theSourceCompilesAgainstAndroidJarAtJava8` passes.
- [x] 4.4 Instrument `com.luk.saucenao_27.apk` with `--stamp-handlers` by the baseline jar (0.1) and by the new jar: every app `classes*.dex` MUST be byte-identical and `weaveCounts` equal; the monitor DEX MUST differ only inside `mop.RvsecStamp`. Record in `experimento-smk124/RELATORIO.md`.

## 5. Device smoke (after 4 — instrumentation and runs in parallel)

- [x] 5.1 Instrument, with the new jar and `--stamp-handlers`, the original APKs of `com.luk.saucenao_27`, `at.techbee.jtx_216000015` and one foundation 1.7/1.8 app that calls `Checkbox` (`app.plugbrain.android_154` or `com.kin.easynotes_14`) through `DexlibInstrumentation`, reusing `data/e03mini_a2/instrument_ab.py`'s configuration (copied into `experimento-smk124/scripts/`; `jca_android` monitors). Copy each APK's `.apk.json` next to it (the MOP arms need it).
- [x] 5.2 Write `experimento-smk124/docker-compose.yml` from `docker/docker-compose.e03mini-a2.yml` (image `1f34ddec` or the current 0.9.5, `restart: "no"`, one container per APK, `aperv:mopd_on_llm_off`, 300 s, 1 rep) and launch it; emulators are managed by rv-platform only.
- [x] 5.3 For each APK, from the task logcat and the derived MOP artifact: count Compose `RVSEC-BIND` lines by handler package; list every distinct app class named and check it is a key of `handlers`; confirm no line names `AbstractClickableNode$$ExternalSyntheticLambda*` (saucenao, jtx) or `CheckboxKt$$ExternalSyntheticLambda6` / `CheckboxKt$Checkbox$1$1`; report `stampHits` and decisions with `src=MOP`.
- [x] 5.4 List every node where the Material step changed the stamp (Material class → app class), separating those reached through the action-lambda fallback (design D2), and every remaining `androidx.compose.material*` handler, by class.
- [x] 5.5 Check that no crash carries a `mop.RvsecStamp` frame and no `VerifyError` is logged; write the results of 5.3–5.5 in `experimento-smk124/RELATORIO.md`.

## 6. Lint, verify, review and close (after 5)

- [x] 6.1 Run `/rv-qa-lint-fix rv-instrumentation-dexlib2` (the Python wrapper is unchanged; this confirms nothing drifted)
- [x] 6.2 Run `/rv-verify rv-instrumentation-dexlib2`
- [x] 6.3 Invoke `/rv-code-reviewer` via Skill tool on the diff of `RvsecStamp.java` and the new test
- [x] 6.4 Check off the acceptance criteria satisfied in the body of issue #124 (`test -s` on the body file before `gh issue edit --body-file`)
- [x] 6.5 Commit by path (`git commit -- <paths>`), `refs #124`, without any co-author trailer; the change archive (`/opsx:archive`) closes #124
