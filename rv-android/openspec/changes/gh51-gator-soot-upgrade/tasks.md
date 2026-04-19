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

## 1. Prerequisites — Comment Out Deprecated Modules

- [ ] 1.1 Comment out `rvsec-methods-extractor` module in `rvsec/rvsec-android/pom.xml`
- [ ] 1.2 Comment out `rvsec-taint` module in `rvsec/rvsec-android/pom.xml`
- [ ] 1.3 Verify `mvn clean compile -pl rvsec-gator -am` still works with current Soot 3.3.0

## 2. FIX 3 — Soot Version Upgrade (INV-ANA-18)

- [ ] 2.1 Update `rvsec/pom.xml`: `<soot.version>4.4.1</soot.version>` → `<soot.version>4.7.1</soot.version>`
- [ ] 2.2 Update `rvsec-gator/pom.xml`: remove `<gator.soot.version>3.3.0</gator.soot.version>`, replace `ca.mcgill.sable:soot:${gator.soot.version}` with `org.soot-oss:soot:${soot.version}`
- [ ] 2.3 Update `rvsec-gator/sootandroid/pom.xml`: same groupId/version change if Soot is redeclared
- [ ] 2.4 Update `rvsec-gator/commons/pom.xml`: same change if Soot is declared
- [ ] 2.5 Update `rvsec-gator/client/pom.xml`: remove Soot exclusion from `maven-assembly-plugin` configuration
- [ ] 2.6 Run `mvn clean compile -pl rvsec-gator -am` — list all compilation errors
- [ ] 2.7 Fix API breaks in `Configs.java` (`Options.v().set_force_android_jar()`, `set_src_prec()` — lines 235-237)
- [ ] 2.8 Fix API breaks in `EpiccBasedIntentAnalysis.java` (`soot.dexpler.Util.splitParameters()`, `Util.getType()` — lines 125-128)
- [ ] 2.9 Fix any remaining compilation errors found in 2.6
- [ ] 2.10 Verify `mvn clean compile -pl rvsec-gator -am` succeeds
- [ ] 2.11 Verify `mvn clean compile -pl rvsec-apk` succeeds (FlowDroid 2.10.0 + Soot 4.7.1 compatibility)
- [ ] 2.12 If 2.11 fails: evaluate upgrading FlowDroid to 2.14.1 or 2.15.1

## 3. FIX 1 — Soot Defensive Options (INV-ANA-16)

- [ ] 3.1 In `Main.java`, add to `sootArgs` array (both `withCHA` and non-CHA branches): `"-p", "jb.sils", "enabled:false"`, `"-p", "jb.dae", "enabled:false"`, `"-no-bodies-for-excluded"`, `"-exclude", "kotlin."`, `"-exclude", "kotlinx."`
- [ ] 3.2 In `Main.java`, add programmatically before `soot.Main.main()`: `Options.v().set_ignore_resolution_errors(true)` and `Options.v().set_throw_analysis(Options.throw_analysis_dalvik)`
- [ ] 3.3 Verify compilation: `mvn clean compile -pl rvsec-gator/sootandroid`

## 4. FIX 2 — Flowgraph Graceful Degradation (INV-ANA-17)

- [ ] 4.1 In `Flowgraph.java`, wrap `Body b = currentMethod.retrieveActiveBody()` (line 274) in try-catch with `Logger.verb()` warning and `continue`
- [ ] 4.2 In `Flowgraph.java`, replace `throw new RuntimeException(e)` (line 343) with `Logger.verb()` warning and `continue`
- [ ] 4.3 Verify compilation: `mvn clean compile -pl rvsec-gator/sootandroid`

## 5. Build Fat JAR

- [ ] 5.1 Build `rvsec-analysis-client.jar`: `mvn clean package -pl rvsec-gator/client -am -DskipTests`
- [ ] 5.2 Copy new JAR to `rv-android/lib/gator/rvsec-analysis-client.jar`
- [ ] 5.3 Verify JAR size is reasonable (old: ~50MB; new should be similar or larger with unified Soot)

## 6. Smoke Test

- [ ] 6.1 Backup current `rvsec-analysis-client.jar` to `backup/`
- [ ] 6.2 Select 10 APKs that currently crash: `app.zornslemma.mypricelog_4.apk`, `ac.mdiq.podcini.X_256.apk`, `app.fluffy_730.apk`, `app.siftrecipes_6.apk`, and 6 others from Kotlin/Compose APKs (>50 .kt files) in `data/apks/`
- [ ] 6.3 Run GATOR directly on each of the 10 APKs — record which produce JSON
- [ ] 6.4 Verify success criterion: ≥7/10 produce JSON
- [ ] 6.5 Select 10 APKs that currently work (including `cryptoapp.apk` baseline)
- [ ] 6.6 Run GATOR on the 10 working APKs — verify no regressions
- [ ] 6.7 Compare `cryptoapp.apk` output against baseline: `directlyReachesMop` must match exactly, `reachable`/`reachesMop` within ±10%

## 7. Verification

- [ ] 7.1 Run `mvn clean compile` on all active RVSEC modules (`rvsec-gator`, `rvsec-apk`, `rvsec-frame-computer`)
- [ ] 7.2 Run full SA via `rv-experiment` on 1 APK to verify end-to-end pipeline (Python wrapper → GATOR → JSON → parser)
- [ ] 7.3 Document results: number of new APKs analyzed, any regressions, any API changes made
