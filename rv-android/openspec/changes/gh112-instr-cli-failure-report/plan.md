# Change Plan: gh112-instr-cli-failure-report

**Date**: 2026-09-06
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: [#112](https://github.com/PAMunb/rvsec/issues/112)
**PRD Reference**: FR02 (APK instrumentation with monitors), NFR06 (observability)
**Domains**: instrumentation

## 1. Context

`instr-cli`, the DEX-native weaver's command line (`rvsec-instrumentation-dexlib2/cli`), reports a
failed instrumentation as if it had succeeded, and throws away the cause of the failure on the way.

`BatchRunner.runPipeline` never throws. Any `RuntimeException` becomes
`PerApkResult(success=false, phase=uncaught, message=…)` and any `IOException` becomes
`phase=io_error`. That part is by design; the class Javadoc calls it a "well-formed failure" and
expects the Python wrapper to read the per-APK JSON. Three things go wrong with that result:

1. **The process exits 0.** `Instrument.run()` and `Batch.run()` are `void`. picocli returns 0
   for a `Runnable` that returns, and `main` passes that to `System.exit`. So `exit 0` with
   `success=false` is by construction, for every failure phase.
2. **The cause is discarded.** The `catch` keeps only `ex.getMessage()`. dexlib2's `DexWriter`
   wraps the original exception in `ExceptionWithContext`, whose constructor
   (`ExceptionWithContext(Throwable cause, String message, …)`) passes only `message` to `super`
   and never folds the cause's message in. The JSON receives "Exception occurred while writing
   code_item for method …"; the real cause, "Unsigned short value out of range: 65536", sits
   further down the `getCause()` chain and nobody reads it. No stack trace is printed anywhere.
3. **The counters are zeroed, twice over.** `failed()` replaces the accumulated `counts` with
   `Map.of()`, so `weaveCounts={}` means "an exception happened" and whatever was already
   measured (advices, DEX count, input API, wrappers) is lost. And even with `counts` passed
   through, the per-DEX statistics would still be missing: `matchesApplied`, `classesSeen`,
   `methodsSeen`, `wrappersSubstituted`, `plansSkipped*` and the coverage pair accumulate in
   local `int` variables (`:232-243`) that are only written into `counts` **after** the weave
   loop ends (`:323-341`). A failure inside the loop drops every one of them.

Concrete case: in the `rerun-corpus-jca-android` campaign (2026-09-05), 6 of 170 APKs failed with
`exit 0` and `weaveCounts={}`. Five carried only the `code_item` message. The cause, a DEX at the
65,536 `method_ids` ceiling, had to be reconstructed by reading DEX headers by hand. The same
diagnosis had already been rebuilt from scratch on 2026-08-12
(`docs/20260812_registro_execucao_prontidao_e3.md` §2.5). Downstream, the Python wrapper only
raises on a non-zero exit, so it labels every well-formed failure "silent javac/d8 failure" with
`phase=dexlib2_pipeline`; that false diagnosis is what the campaign's `instrument_errors.json`
recorded.

The measured shape of that case, which the acceptance criteria below rely on: in
`info.dvkr.screenstream_44000.apk` the class named in the message,
`androidx/core/view/WindowInsetsCompat$Impl20`, is defined in `classes28.dex`, whose header
(offset `0x58`) reports `method_ids_size = 65521` — 15 slots below the ceiling. The APK has 29
DEXes, so the failure lands near the end of the weave loop, with 27 DEXes already fully woven and
their statistics held in exactly the local variables item 3 describes.

**Scope decision (researcher, 2026-09-06): Java side only.** With the CLI exiting 1, the wrapper's
per-APK path (the only one rv-experiment uses) records "instr-cli exited with code 1" plus the
stderr, which will now carry the stack trace, with no Python change. The wrapper's `batch` path
would raise on a batch with one failure; rv-experiment never uses it (it always passes
`apk_paths`). Wrapper and rv-experiment pre-processor changes are deferred to a separate issue,
if the full-chain run ever needs them.

## 2. Scope

One Maven module in the sibling repo `rvsec/` (rooted at
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/`):
`rvsec-android/rvsec-instrumentation-dexlib2/cli`. Two production classes, one test class, one
Javadoc table, one option description and two architecture paragraphs. Nothing in `rv-android`
changes except this change directory itself.

Four behaviours change, all in the CLI glue, none in the weaver:

- exit code 1 when any `PerApkResult` has `success=false` (0 otherwise); the JSON is still written
  first, so "exit 1 with JSON" is a well-formed failure and "no JSON" is a dead JVM;
- failure `message` carries the cause chain down to the innermost exception, and the stack trace
  goes to stderr;
- failure `weaveCounts` keeps every counter accumulated up to the failure, the per-DEX ones
  included — which means the weave loop must accumulate into `counts` itself rather than into
  local variables copied in afterwards;
- a failure inside `DexPool.writeTo` gets its own phase, `dex_write`, naming the DEX entry.

**Decision — `dex_only` and `build_only` exit 1 as well.** Both carry `success=false` today, and
the exit rule above does not carve them out. They are not weave failures: they are the outcome of
an invocation that deliberately withheld `--monitor-src-dir` or the signing flags, and the Javadoc
and `architecture.md` both describe their artifacts as consumable downstream. The rule still
covers them, for one reason: neither produced an installable APK, and the exit code answers "did
this invocation instrument the APK", not "did the weaver misbehave". Verified as safe: nothing in
either repo reads that exit code — `docker/rvandroid/Dockerfile`, the compose files, the rvsec CI
workflow and `rv-android/scripts/v2_woven_dex_events.py` (which invokes the fat jar only for its
bundled baksmali) are the only consumers of the jar, and the Python wrapper already fails a
`dex_only` run on its `output_apk.is_file()` guard regardless of the exit code. Because this
widens what a non-zero exit means, the `--monitor-src-dir` option description has to say so.

Out of scope (verify, do **not** touch): the weaver modules (`dex-mutator`, `advice-emitter`,
`coverage-weaver`), any preflight on the `method_ids` ceiling, the Python wrapper
`modules/rv-instrumentation-dexlib2/`, the rv-experiment pre-processor, the `PerApkResult` JSON
shape (field names and types stay as they are; only the insertion order of `weaveCounts` keys
moves, and nothing reads them positionally).

## 3. File Inventory

All paths relative to `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` in the `rvsec/` repo.

| File | Action | Detail |
|------|--------|--------|
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (lines 232-243, 274-341) | Edit | Delete the twelve local `int` accumulators and accumulate straight into `counts`: `counts.merge("matchesApplied", wr.matchesApplied(), Integer::sum)` and one such call per counter, inside the loop, with `counts.put("wrappersAliasedToSubtype", wr.wrappersAliasedToSubtype())` for the APK-scoped one and the coverage pair still guarded by `coverageWeaver != null`. `counts.put("wovenDexes", …)` stays after the loop. This is what makes a mid-loop failure keep its statistics — a helper taking twelve parameters would say the same thing worse (P1). Every key is still written on the first iteration even when its value is 0, so the `plansSkippedUnresolvedBinding` jq guard in `run_phase5_validators.sh` keeps reading a present key; what changes is the insertion order of `weaveCounts` in the JSON, which no consumer reads positionally. |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (lines 389-396) | Edit | In both `catch` blocks, build the message with a new package-private helper `causeChain(Throwable)` and call `ex.printStackTrace()` so the trace reaches stderr. Change `failed(Path, String, String)` to `failed(Path, String, String, Map<String, Integer>)`, **and widen it from `private` to package-private** so the test can call it directly. Pass the live `counts` from every call site (`:157`, `:171`, and the two catches). The early returns at `:157` (`config_validation`) and `:171` (`apk_read`) pass the same `counts`. |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (new helper) | Add | `static String causeChain(Throwable ex)` walks `getCause()` and joins the messages with `"; caused by: "`. The walk stops after 10 links: a cause chain that points back at itself would otherwise spin forever, and the result is a JSON field, so a bounded string is wanted anyway. `ExceptionWithContext` also overrides `printStackTrace` to print its context lines, so the stderr trace carries more than the chain does. |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (line 319) | Edit | Wrap `DexPool.writeTo(outDex.toString(), mutator.toDexFile())` in `try { … } catch (RuntimeException ex)` that prints the trace and returns `failed(apk, "DEX write failed for " + ed.entryName + ": " + causeChain(ex), "dex_write", counts)`. This is the failure the campaign hit; naming the entry tells the reader which DEX is at the ceiling without opening the APK, and with the accumulation change above, `counts` here holds the 27 DEXes' worth of statistics that the current code drops. |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (lines 93-99, 115-131) | Edit | `instrumentOne` returns `boolean` (`result.success()`); `instrumentBatch` returns `boolean` (every result `success()`). Both still write the JSON and print the summary before returning. |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` (Javadoc, lines 20-60) | Edit | Add `phase=dex_write` to the phase-outcome list, and one sentence stating the exit-code contract: 0 when every result succeeded, 1 otherwise — `dex_only` and `build_only` included — JSON always written first. Replace the phrase "the Python wrapper continues onto the next APK" with the current behaviour (the wrapper records the failure from the exit code and stderr, and continues). P4: describe what the code does now, no history. |
| `cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java` (lines 124-146) | Edit | `Instrument` and `Batch` implement `Callable<Integer>` instead of `Runnable`; `call()` returns `BatchRunner.instrumentOne(...) ? 0 : 1` (resp. `instrumentBatch`). `main` (`:149-151`) is unchanged: picocli propagates the returned integer, and still returns its own non-zero code for usage errors and uncaught exceptions — including the `IllegalArgumentException` `ConfigResolver` throws when no android.jar resolves. The sibling `ValidationCli` calls `System.exit` from inside a `Runnable`; that idiom is not copied here, because it would make the exit code untestable in-process. |
| `cli/src/main/java/br/unb/cic/rv/cli/InstrumentationCli.java` (lines 97-102) | Edit | `--monitor-src-dir` description: after "the pipeline stops at written DEXes (phase=dex_only)", state that such a run exits 1, because it produced no instrumented APK. Without this the flag's own help contradicts the new exit contract. |
| `cli/src/test/java/br/unb/cic/rv/cli/ResultsJsonReportingTest.java` | Edit | Add three tests. (a) `instrumentExitsOneWhenTheWeaveFails`: `new CommandLine(new InstrumentationCli()).execute("instrument", apk, "--android-jar", dummy, "--results-json", out)` with no `--descriptor` returns 1 and the JSON still says `success=false`, `phase=config_validation`. **`--android-jar` is not optional in this test**: without it `ConfigResolver.resolve` throws before `BatchRunner` runs, picocli prints the trace and returns 1 anyway, so the assertion would pass for the wrong reason and the JSON assertion would then fail for the wrong reason — on any host without an Android SDK, which is what the rvsec CI runner is (`ci.yml` lines 55-60). `requirePath` only checks for null, so any path under `@TempDir` works and the run still stops at `config_validation`. (b) `failureMessageCarriesTheInnermostCause`: `BatchRunner.causeChain(new RuntimeException("outer", new RuntimeException("middle", new IllegalStateException("inner"))))` contains `"inner"` and the two `"; caused by: "` separators. (c) `failureKeepsTheCountersAccumulatedSoFar`: `BatchRunner.failed(apk, "m", "uncaught", Map.of("advices", 3))` serialises with `weaveCounts.advices == 3` — this is the test that needs `failed` package-private. Keep the existing test `instrumentWritesResultsJsonWhenTheWeaveFails` as is; it asserts the JSON shape, which does not change. |
| `architecture.md` (lines 370-378, "Phase-tagged partial results") | Edit | Add `dex_write` to the phase list; state that the exit code is 1 whenever a result is not a success, `dex_only`/`build_only` included, and that the phase tag is what still distinguishes a withheld flag from a broken weave. The same paragraph's "The Python wrapper parses these into `InstrumentationResults` (INV-INS-55) and continues to the next APK" carries the same stale reading as the Javadoc sentence and gets the same correction. Line 640 ("a silent `javac`/`d8` failure (zero exit, no `.dex`) is caught downstream by the Python wrapper") stays: that case is a `success=true` with no output, which this change does not touch. |

## 4. Execution Order

Single linear sequence, one module, no parallel groups.

1. Write the three tests in `ResultsJsonReportingTest` and run them: (a) fails (exit is 0),
   (b) and (c) fail to compile (helper does not exist, `failed` is private and has three
   parameters). RED.
2. Edit `BatchRunner` (helper, `failed` signature and visibility, catches, counter accumulation,
   `dex_write` wrap, return values) and `InstrumentationCli` (`Callable<Integer>`, option help).
   Run `mvn -pl cli test` from the module root. GREEN.
3. Update the Javadoc table and `architecture.md`.
4. Run `mvn -pl cli -am package -DskipTests=false` so `cli/target/instr-cli.jar` is rebuilt;
   the Docker image picks the jar up on its next build (`docker/rvandroid/build.sh`), which is
   not part of this change.

Maven note: all three commands run from `rvsec-instrumentation-dexlib2/` as written. The root
`CLAUDE.md` warns that `${main.basedir}` "only resolves correctly when building from the root
reactor"; that warning does not apply here — `directory-maven-plugin`'s `directory-of` resolves
`br.unb.cic:rvsec-parent` by walking the filesystem, not the reactor session (verified:
`mvn -o -pl cli initialize` prints "Directory of br.unb.cic:rvsec-parent set to: …/rvsec"), and
the sibling module snapshots are installed in the local repository.

## 5. Acceptance Criteria

- [ ] `mvn -pl cli test` in `rvsec-instrumentation-dexlib2` passes with the three new tests green and no regression in `ResultsJsonReportingTest`, `BatchRunnerSmokeTest`, `DexVersionPreservationTest`.
- [ ] `instrumentExitsOneWhenTheWeaveFails` passes with `ANDROID_HOME` unset in the test process, proving it does not depend on a local Android SDK.
- [ ] `java -jar cli/target/instr-cli.jar instrument <empty.apk> --android-jar <any path> --results-json out.json` (no descriptor) exits 1, writes `out.json` with `success=false`, and prints a stack trace on stderr.
- [ ] Running the rebuilt jar on `info.dvkr.screenstream_44000.apk` from `rvsec-dataset/head_apks` (with the campaign's descriptor and paths, and a fresh work dir) yields `phase=dex_write`, a message naming `classes28.dex` and containing `Unsigned short value out of range`, exit 1, and a `weaveCounts` that carries `matchesApplied`, `classesSeen` and `methodsSeen` with non-zero values — the 27 DEXes woven before the failing one. A merely non-empty `weaveCounts` does not satisfy this criterion; the pre-loop keys alone are what the current code would already have. This is the only run that touches a real APK; it needs no emulator.
- [ ] `grep -n "Map.of()" BatchRunner.java` returns no hit inside `failed`; every `failed(...)` call passes `counts`; no local `int` accumulator survives the weave loop.
- [ ] Javadoc phase list, the `--monitor-src-dir` option description and `architecture.md` all mention `dex_write` and the exit-code contract, and agree that `dex_only`/`build_only` exit 1; no migration wording (P4).
- [ ] `git status --porcelain -- rvsec/rvsec-android/rvsec-instrumentation-dexlib2` lists only `cli/src/main/java/.../BatchRunner.java`, `cli/src/main/java/.../InstrumentationCli.java`, `cli/src/test/java/.../ResultsJsonReportingTest.java` and `architecture.md`. A bare `git status` proves nothing here: `rvsec` and `rv-android` are one repository (branch `modules`) whose tree already carries unrelated modifications from other work.
- [ ] Final commit in the `rvsec/` tree with `closes #112`, made with an explicit pathspec, no `Co-Authored-By` trailer.
