# E2 — re-weave of the frozen descriptor (task 4.6)

**STUB — task 4.6 is the orchestrator's, run after the between-wave `mvn install` that rebuilds
`lib/`.** Group 4 (E2) left the Java and Python edits in place and did not run it; what follows
is everything 4.6 needs, plus the emitter-level measurement Group 4 could take without a
rebuild.

## Fill this table

| run (before\|after) | `instr-cli.jar` sha256 | `wrappersGenerated` | `advicesExcludedByArity` | `MonitorWrappers.java` sha256 | predicted pairs | measured pairs | per-advice breakdown |
|---|---|---|---|---|---|---|---|
| before | `d05a373878c0501d3334b083453435f4445807cda63452f86a9aa76006da948b` (jar as of 2026-08-11, pre-rebuild) | | (key absent — pre-change jar) | | 10 | | |
| after | (hash the rebuilt jar) | | | | 10 | | |

**The parity instrument**: the `MonitorWrappers.java` sha256 must be identical in both rows. An
unchanged `wrappersGenerated` alone cannot see a lost monitor call inside a wrapper; the file
hash can. If either moved, the rule leaked into emission and the group is wrong.

## Command line

⚠️ **Use the `android-37.0` jar, not `android-30`.** The count is a function of descriptor *and*
`android.jar`: `SecureRandom.getInstance(String, ..)` expands to three overloads up to API 34
and six from API 35 on. On android-30 the same descriptor measures **5** pairs and emits **81**
wrappers; on android-36.1/37/37.0 it measures **10** pairs and emits **84** wrappers, and the
emitted file is byte-identical to the frozen control. The frozen control was woven with the
`ConfigResolver` env default, which is the lexicographic maximum under `$ANDROID_HOME/platforms`
— `android-37.0` on this machine. See `e2_reach.md`, "The measurement itself".

```bash
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
RUN=before   # then: after
cp -r results/gh101_group8_jca_frozen_control/monitors $HOME/tmp-gh104/e2-reweave-$RUN/monitors
java -jar modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
  --descriptor results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json \
  --android-jar $ANDROID_HOME/platforms/android-37.0/android.jar \
  --monitor-src-dir $HOME/tmp-gh104/e2-reweave-$RUN/monitors \
  --keystore modules/rv-instrumentation/assets/keystore.jks \
  --keystore-pass <pass> --key-alias <alias> --key-pass <pass> \
  --work-dir $HOME/tmp-gh104/e2-reweave-$RUN \
  --output $HOME/tmp-gh104/e2-reweave-$RUN/out \
  --results-json $HOME/tmp-gh104/e2-reweave-$RUN/instrument_results.json \
  instrument apks_examples/cryptoapp.apk

sha256sum $HOME/tmp-gh104/e2-reweave-before/monitors/mop/MonitorWrappers.java \
          $HOME/tmp-gh104/e2-reweave-after/monitors/mop/MonitorWrappers.java   # MUST be equal
```

`--monitor-src-dir` is a **copy** of `results/gh101_group8_jca_frozen_control/monitors/` made per
run, never the frozen directory itself: the CLI writes `mop/MonitorWrappers.java` into it
(`BatchRunner.java:189-201`). APK: `apks_examples/cryptoapp.apk` — the only APK in the tree and
the one the design names.

Also record the sha256 of `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` after the
rebuild (the "after" row above).

## What Group 4 already measured, without a rebuild

`WrapperEmitter.generate` is a pure function of descriptor + `android.jar`, so the emitter half of
the re-weave was measurable directly from `advice-emitter/target/classes` on 2026-08-19, with the
arity counter in place:

- `android-36.1` / `android-37` / `android-37.0`: `wrappersGenerated` = **84**,
  `advicesExcludedByArity` = **10**, per-advice `TrustManagerFactorySpec_g2` ×1,
  `KeyManagerFactorySpec_g2` ×1, `SecureRandomSpec_g2` ×3, `SecureRandomSpec_g4` ×5 — exactly the
  prediction of D-6 and the design API section.
- The emitted `mop/MonitorWrappers.java` is **byte-identical** to
  `results/gh101_group8_jca_frozen_control/monitors/mop/MonitorWrappers.java`
  (sha256 `6a219bb213f978a1d2755389c88c86b192ba4e57cde5aa7e2b006a24dbe723ab`).

That is a stronger form of the parity instrument than before-vs-after: the post-change emitter
reproduces the frozen artefact itself, bit for bit. It does not replace 4.6, which validates the
whole CLI path and the transport of the counter into `instrument_results.json`.
