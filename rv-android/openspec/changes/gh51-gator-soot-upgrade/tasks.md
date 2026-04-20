<!-- Subagent dispatch: NOT needed (Java changes only, ~10 files, sequential dependency). -->

```mermaid
flowchart LR
    G1["1. Prerequisites"] --> G2["2. FIX 3\nSoot 4.7.1"]
    G2 --> G3["3. FIX 1\nSoot options"]
    G2 --> G4["4. FIX 2\nFlowgraph"]
    G3 --> G5["5. Build\nFat JAR"]
    G4 --> G5
    G5 --> G6["6. Smoke\nTest"]
    G6 --> G7["7. Verify"]
```

## 1. Prerequisites — Remove Deprecated Modules

- [x] 1.1 Remove `rvsec-methods-extractor` module entry from `rvsec/rvsec-android/pom.xml` and move `rvsec-methods-extractor/` directory to `backup/`
- [x] 1.2 Remove `rvsec-taint` module entry from `rvsec/rvsec-android/pom.xml` and move `rvsec-taint/` directory to `backup/`
- [x] 1.3 Verify `mvn clean compile -pl rvsec-gator -am -DskipTests -DskipMopAgent` still works with current Soot 3.3.0

## 2. FIX 3 — Soot Version Upgrade (INV-ANA-18)

- [x] 2.1 Update `rvsec/pom.xml` (artifactId=`rvsec-parent`, line 38): `<soot.version>4.4.1</soot.version>` → `<soot.version>4.7.1</soot.version>`
- [x] 2.2 Update `rvsec-gator/pom.xml`: remove `<gator.soot.version>3.3.0</gator.soot.version>`, replace `ca.mcgill.sable:soot:${gator.soot.version}` with `org.soot-oss:soot:${soot.version}`
- [x] 2.3 Update `rvsec-gator/sootandroid/pom.xml`: same groupId/version change if Soot is redeclared
- [x] 2.4 Update `rvsec-gator/commons/pom.xml`: same change if Soot is declared
- [x] 2.5 Update `rvsec-gator/client/pom.xml`: remove BOTH Soot exclusions from `rvsec-mop-extractor` dependency (lines 43-51 — both `ca.mcgill.sable:soot` and `org.soot-oss:soot`; neither groupId conflict exists anymore)
- [x] 2.6 Run `mvn clean compile -pl rvsec-gator -am -DskipTests -DskipMopAgent` — list all compilation errors
- [x] 2.7 Fix API breaks in `Configs.java` (`Options.v().set_force_android_jar()`, `set_src_prec()` — lines 235-237) — NO BREAKS: API preserved in Soot 4.7.1
- [x] 2.8 Fix API breaks in `EpiccBasedIntentAnalysis.java` (`gui/clients/ata/EpiccBasedIntentAnalysis.java` — `soot.dexpler.Util.splitParameters()`, `Util.getType()` — lines 125-128) — NO BREAKS: API preserved in Soot 4.7.1
- [x] 2.9 Fix any remaining compilation errors found in 2.6 — NONE: zero compilation errors
- [x] 2.10 Verify `mvn clean compile -pl rvsec-gator -am -DskipTests -DskipMopAgent` succeeds
- [x] 2.11 Run `mvn dependency:tree -pl rvsec-gator/client` — verify no Guava/SLF4J version conflicts — OK: org.soot-oss:soot:4.7.1 resolved, Guava 27.1-jre, no conflicts
- [x] 2.12 Verify `mvn clean compile -pl rvsec-apk -DskipTests -DskipMopAgent` succeeds (FlowDroid 2.10.0 + Soot 4.7.1 compile compatibility) — OK: BUILD SUCCESS
- [ ] 2.13 Runtime smoke test: execute `rvsec-apk` on 1 APK to detect `NoSuchMethodError` (compile ≠ runtime) — requires fat JAR, will validate during task 6
- [ ] 2.14 If 2.12 or 2.13 fails: upgrade FlowDroid to 2.14.1 (validated with CryptoAnalysis) or 2.15.1 (both confirmed on Maven Central)
- [x] 2.15 **Git commit**: FIX 3 checkpoint (Soot upgrade + dependency changes) — aa17461c

## 3. FIX 1 — Soot Defensive Options (INV-ANA-16)

- [x] 3.1 In `Main.java`, add to `sootArgs` array (both `withCHA` and non-CHA branches): `"-p", "jb.sils", "enabled:false"`, `"-p", "jb.dae", "enabled:false"`, `"-no-bodies-for-excluded"`, `"-exclude", "kotlin."`, `"-exclude", "kotlinx."`, `"-exclude", "androidx.compose."`
- [x] 3.2 In `Main.java`, add programmatically before `soot.Main.main()`: `Options.v().set_ignore_resolution_errors(true)` and `Options.v().set_throw_analysis(Options.throw_analysis_dalvik)`
- [x] 3.3 Verify compilation: `mvn clean compile -pl rvsec-gator/sootandroid` — BUILD SUCCESS
- [x] 3.4 **Git commit**: FIX 1 checkpoint (defensive Soot options) — 65444e26 (combined with FIX 2)

## 4. FIX 2 — Flowgraph Graceful Degradation (INV-ANA-17)

- [x] 4.1 In `Flowgraph.java`, wrap `Body b = currentMethod.retrieveActiveBody()` (line 274) in try-catch with `Logger.warn()` warning (method signature + exception message) and `continue`. Move `numMtd += 1` (line 273) to AFTER the `retrieveActiveBody()` call so skipped methods are not counted
- [x] 4.2 In `Flowgraph.java`, replace `throw new RuntimeException(e)` (line 343) with `Logger.warn()` warning (statement + exception message) and `continue`
- [x] 4.3 Verify compilation: `mvn clean compile -pl rvsec-gator/sootandroid` — BUILD SUCCESS
- [x] 4.4 **Git commit**: FIX 2 checkpoint (Flowgraph graceful degradation) — 65444e26 (combined with FIX 1)

## 4b. FIX 2 Additional — Null Receiver + IntentAnalysis Loop (discovered during testing)

- [x] 4b.1 In `Flowgraph.java`, add null-check for `jimpleUtil.receiver(ie)` before `rcv_var.getType()` (NPE on excluded-package virtual calls)
- [x] 4b.2 In `FlowgraphRebuilder.java`, add same null-check at line 133 (rebuildFlow method) and line 967 (buildCallGraph method)
- [x] 4b.3 In `IntentAnalysis.java`, add `HashSet<Pair> visited` to the fixpoint `while (!workingList.isEmpty())` loop to prevent infinite re-processing when `intentContent.get(allocNode)` returns null
- [x] 4b.4 Verify compilation — BUILD SUCCESS

## 4c. FIX 2 Additional — Write-First JSON Strategy (discovered during testing)

- [x] 4c.1 In `RvsecAnalysisClient.java`, write JSON with reachability (empty windows/transitions) BEFORE starting WTG construction. If WTG completes, rewrite with full data. Guarantees reachability survives external timeout (Python kills process).
- [x] 4c.2 Make `writeJson()` tolerate `wtg == null` (writes empty arrays for windows/transitions)
- [x] 4c.3 Verify compilation — BUILD SUCCESS
- [x] 4c.4 Test: `cryptoapp.apk` still produces full JSON (reachability + windows + transitions) — CONFIRMED: identical to baseline

## 4d. FIX 3 Additional — Soot Option Rename (discovered during testing)

- [x] 4d.1 Replace `-process-multiple-dex` with `-search-dex-in-archives` in both sootArgs branches of `Main.java` (option renamed in Soot 4.x)
- [x] 4d.2 Verify compilation — BUILD SUCCESS

## 4e. Call Graph Algorithm Parameter (D5)

- [ ] 4e.1 In `Configs.java`, replace `public static boolean withCHA = false` with `public static String cgAlgorithm = "cha"` (values: `cha`, `rta`, `vta`, `spark`)
- [ ] 4e.2 In `Main.java`, replace `-withCHA` arg parsing with `-cgAlgorithm <value>`. Keep `-withCHA` as alias for `-cgAlgorithm cha` (backward compat during transition)
- [ ] 4e.3 In `Main.java`, replace the two hardcoded branches (withCHA/non-CHA) with a single sootArgs construction that selects CG phase options based on `Configs.cgAlgorithm`: `cha` → `-p cg.cha enabled:true`, `rta` → `-p cg.spark enabled:true -p cg.spark rta:true`, `vta` → `-p cg.spark enabled:true -p cg.spark vta:true`, `spark` → `-p cg.spark enabled:true`
- [ ] 4e.4 In GATOR Python script (`lib/gator/gator`), replace `-withCHA` with `-cgAlgorithm` argument (default `cha`)
- [ ] 4e.5 In `rv-static-analysis/config.py`, update `get_tool_command()` to pass `-cgAlgorithm` instead of `-withCHA`
- [ ] 4e.6 Verify compilation and test with `cryptoapp.apk` using `cha` (default)

## 5. Build Fat JAR

- [x] 5.1 Build `rvsec-analysis-client.jar`: `mvn clean package -pl rvsec-gator/client -am -DskipTests` — BUILD SUCCESS
- [x] 5.2 Copy new JAR to `rv-android/lib/gator/rvsec-analysis-client.jar`
- [x] 5.3 Verify JAR size is reasonable (old: ~50MB; new should be similar or larger with unified Soot) — 57MB OK

## 6. Smoke Test

- [x] 6.1 Backup current `rvsec-analysis-client.jar` to `backup/gh51-deprecated-modules/rvsec-analysis-client-soot3.3.0.jar`
- [ ] 6.2 **Isolation experiment** (validates if FIX 3 is necessary): In a separate branch (or before merging task 2), apply ONLY FIX 1 defensive options to `Main.java` while keeping Soot 3.3.0, build JAR, and run on 5 APKs from the JCA SA-failure list (`flip_2_dnd`, `totalrecall`, `calcyou`, `ttsengine`, `tictactoe`). If ≥3/5 produce JSON, FIX 3 may be optional (document results for thesis). NOTE: this experiment must run before or in parallel with FIX 3, not after it
- [ ] 6.3 Run GATOR with full fixes (FIX 1+2+3) on 10 APKs from JCA dataset (gh50) that are instrumented OK but SA fails:
  - `dev.robin.flip_2_dnd_903.apk`
  - `com.qq7te.totalrecall_8.apk`
  - `net.youapps.calcyou_10.apk`
  - `org.woheller69.ttsengine_31.apk`
  - `com.itsfrz.tictactoe_2.apk`
  - `com.github.girator.rebooter_14.apk`
  - `gizz.tapes.foss_63.apk`
  - `com.iyox.wormhole_5013.apk`
  - `org.librefit.app_10501.apk`
  - `io.github.dorumrr.happytaxes_10.apk`
  Source: `APKS_JCA/errors/instrument_and_sa_errors.json` (32 total inst OK + SA failed)
- [ ] 6.4 Record which produce JSON — success criterion: ≥7/10
- [ ] 6.5 Run GATOR on 10 APKs that currently work (including `cryptoapp.apk` baseline) — success criterion: ≤1 regression
- [ ] 6.6 Compare `cryptoapp.apk` output against baseline: `directlyReachesMop` must match exactly, `reachable`/`reachesMop` within ±10%
- [ ] 6.7 Run Fat JAR via `rv-experiment` on the same 10 previously-crashing APKs (E2E pipeline validation)

## 7. Verification

- [ ] 7.1 Run `mvn clean compile -DskipTests -DskipMopAgent` on all active RVSEC modules (`rvsec-gator`, `rvsec-apk`, `rvsec-frame-computer`)
- [ ] 7.2 Run full SA via `rv-experiment` on 1 APK to verify end-to-end pipeline (Python wrapper → GATOR → JSON → parser)
- [ ] 7.3 Document results: number of new APKs analyzed, any regressions, any API changes made
