# E2 — re-weave of the frozen descriptor (task 4.6)

The whole CLI path, run once against the frozen `jca` descriptor with the arity counter in place.
It answers the question the emitter-level measurement could not: does the counter reach
`instrument_results.json`, and does the rule stay a *measurement* — nothing excluded from what is
actually emitted — once the weaver, the dexer and the signer have all run.

**Verdict: yes, on both counts.** The APK instrumented and signed; `advicesExcludedByArity` is 10,
the number D-6 predicted; and the emitted `mop/MonitorWrappers.java` is byte-identical to the
frozen control's.

## The run

| item | value |
|---|---|
| `instr-cli.jar` sha256 | `cfd4a34b0b2b3261dffc70a51499a5da27d34baa13b34d5fed5659fac13cfc34` (rebuilt 2026-08-19 11:03) |
| descriptor | `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json` |
| `android.jar` | `$ANDROID_HOME/platforms/android-37.0/android.jar` |
| APK | `apks_examples/cryptoapp.apk` |
| `wrappersGenerated` | **84** |
| `advicesExcludedByArity` | **10** |
| `advices` | 115 |
| `matchesApplied` | 32 · `wrappersSubstituted` 74 · `constructorInlineApplied` 11 |
| `mop/MonitorWrappers.java` sha256 | `6a219bb213f978a1d2755389c88c86b192ba4e57cde5aa7e2b006a24dbe723ab` |
| outcome | `success=true, phase=signed` |

## The parity instrument, and why it is not a before/after row

The plan called for two runs, `before` on the pre-change jar and `after` on the rebuilt one, with
the `MonitorWrappers.java` sha256 equal in both rows: an unchanged `wrappersGenerated` alone
cannot see a lost monitor call *inside* a wrapper, but the file hash can.

The pre-change jar no longer exists. `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` is
gitignored and was overwritten by the between-waves `mvn clean install`; no copy survives in
`backup/`. Rebuilding one from the pre-change Java sources would mean checking the reactor out at
an earlier revision to reproduce a hash we already have a stronger check for.

The stronger check is the one used here: the post-change emitter reproduces the **frozen control's
own** `mop/MonitorWrappers.java`, byte for byte —
`6a219bb213f978a1d2755389c88c86b192ba4e57cde5aa7e2b006a24dbe723ab` on both sides. A before/after
pair proves two runs agree with each other; this proves the run agrees with the artefact the
published measurements were woven from, which is what the parity instrument was standing in for.
Group 4 had already established the same equality at the emitter level (`e2_reach.md`); 4.6 shows
it survives the full CLI.

## The `android.jar` is part of the measurement

`android-37.0`, not `android-30`. The count is a function of descriptor *and* `android.jar`:
`SecureRandom.getInstance(String, ..)` expands to three overloads up to API 34 and six from API 35
on. On `android-30` the same descriptor measures **5** pairs and emits **81** wrappers; on
`android-36.1`/`37`/`37.0` it measures the **10** pairs above and emits the **84** wrappers that
match the control. The frozen control was woven with the `ConfigResolver` env default, the
lexicographic maximum under `$ANDROID_HOME/platforms` — `android-37.0` on this machine.

The 10 excluded pairs, from the emitter-level run of `e2_reach.md`: `TrustManagerFactorySpec_g2`
×1, `KeyManagerFactorySpec_g2` ×1, `SecureRandomSpec_g2` ×3, `SecureRandomSpec_g4` ×5.

## Command line

`--classpath` is **required** and was missing from the earlier draft of this file. Without it the
CLI compiles `MultiSpec_1RuntimeMonitor.java` against no runtime and dies with 2,442 errors on
`com.runtimeverification.rvmonitor.java.rt.*` and `br.unb.cic.mop.*`. `dexlib_instrumentation.py`
resolves the same three jars through its allow-list (`rv-monitor-rt`, `rvsec-core`,
`rvsec-logger-logcat`); driving the CLI by hand means supplying them by hand.

```bash
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
M=$HOME/desenvolvimento/repository
W=$HOME/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec
CP="$M/br/unb/cic/rvmonitor/rv-monitor-rt/0.9.3-SNAPSHOT/rv-monitor-rt-0.9.3-SNAPSHOT.jar"
CP="$CP,$W/rvsec-core/target/rvsec-core-0.9.3-SNAPSHOT.jar"
CP="$CP,$W/rvsec-android/rvsec-logger-logcat/target/rvsec-logger-logcat-0.9.3-SNAPSHOT.jar"

R=$HOME/tmp-gh104/e2-reweave-after
rm -rf $R && mkdir -p $R
cp -r results/gh101_group8_jca_frozen_control/monitors $R/monitors
java -jar modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
  --descriptor results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json \
  --android-jar $ANDROID_HOME/platforms/android-37.0/android.jar \
  --monitor-src-dir $R/monitors --classpath "$CP" \
  --keystore modules/rv-instrumentation/assets/keystore.jks \
  --keystore-pass password --key-alias server --key-pass password \
  --work-dir $R --output $R/out --results-json $R/instrument_results.json \
  instrument apks_examples/cryptoapp.apk

sha256sum $R/monitors/mop/MonitorWrappers.java   # must equal the frozen control's
```

`--monitor-src-dir` is a **copy** of `results/gh101_group8_jca_frozen_control/monitors/` made per
run, never the frozen directory itself: the CLI writes `mop/MonitorWrappers.java` into it
(`BatchRunner.java:189-201`).

Paths must be given as `/home/pedro/...`. The session's working-directory alias `/pedro/...` is
not a path the JVM can open, and the CLI fails late with `classpath entry not a file`.
