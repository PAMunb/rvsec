# CLAUDE.md - rvsec-instrumentation-dexlib2

DEX-native AspectJ weaver (gh#52). Given the JSON descriptor emitted by patched
JavaMOP (`--emit-descriptor`) plus the `MultiSpec_*RuntimeMonitor.java` monitor
sources, it rewrites Dalvik bytecode **in place** (smali/dexlib2), then rebuilds
and re-signs the APK. The `.aj` aspect text is **never** parsed — the JSON
descriptor is the sole contract (INV-INS-56). Shades to `instr-cli.jar` (picocli).

This is a **Maven sub-reactor** (`packaging=pom`, groupId `br.unb.cic`, base
Java package `br.unb.cic.rv.*` — note: NOT `br.unb.cic.rvsec.*`). Do NOT
duplicate `architecture.md` (931 lines, canonical) or the spec here — point to them.

## Role in pipeline
The **dexlib2 variant** of Android instrumentation, alternative to the **ajc
variant** (`dex2jar→ajc→d8`, lossy on Kotlin/R8). Pipeline: descriptor → type
resolution → DEX extraction → wrapper generation → advice weave → register
alloc/injection → coverage weave → monitor build → merge/sign. Terminal phase
is one of `dex_only` (default, `--output` omitted) / `build_only` / `signed`.

## Relationships
- ⟵ consumes `MultiSpec_<N>MonitorAspect.json` descriptor + monitor `.java`
  sources from **javamop** (`../../rvsec-mop*`, patched `--emit-descriptor`).
- ⟶ consumed by Python **`rv-android/modules/rv-instrumentation-dexlib2`**
  (`java -jar lib/instr-cli.jar`; implements the `Instrumenter` ABC). ajc stays
  the **default** in Python; dexlib2 is **opt-in** (`RV_INSTRUMENTATION_VARIANT=dexlib2`
  or `--instrumentation-variant dexlib2`).

## Sub-modules (10, layered DAG — verified in pom.xml)
```
descriptor-reader ← pointcut-engine ← advice-emitter ← dex-mutator ← coverage-weaver
monitor-builder (standalone)   multidex-merger (standalone)
cli (aggregates all 8 above)   validator, grammar-tests (alongside, test/tooling)
```

| Module | Key file (`br.unb.cic.rv.*`) | Role |
|---|---|---|
| descriptor-reader | `descriptor/AspectDescriptor.java`, `DescriptorReader.java` | parse JSON descriptor (contract) |
| pointcut-engine | `pointcut/PointcutMatcher.java`, `BaseAspectExpander.java` | resolve pointcuts, expand base aspects |
| advice-emitter | `emitter/{WrapperEmitter,IfGuardEmitter,MonitorInvokeBuilder}.java` | wrappers, `if()` guards, monitor calls |
| dex-mutator | `mutator/{DexWeaver,RegisterShifter,InstructionInjector}.java` | in-place DEX weave, register spill |
| coverage-weaver | `coverage/CoverageWeaver.java` | inject `Coverage.log` probes |
| monitor-builder | `builder/MonitorBuilder.java` | `javac`+`d8` of monitor sources |
| multidex-merger | `merger/MultidexMerger.java` | merge DEXes, sign, zipalign |
| cli | `cli/{InstrumentationCli,BatchRunner}.java` | picocli entry (`br.unb.cic.rv.cli`) |
| validator | `commons-math3` sanity/stat checks (never on prod path) |
| grammar-tests | `grammar/MatrixIntegrityTest.java`, `grammar/util/DemandCounter.java` (test pkg) | CI-enforce grammar matrix; no main artifact |

## Dependencies
Internal: the DAG above. External: `smali-dexlib2`/`smali-baksmali 3.0.9`,
jackson 2.18.2, picocli 4.7.6, asm 9.7.1 (pointcut-engine), slf4j 2.0.16,
junit-jupiter 5.11.3. Subprocesses: `javac`/`d8`/`zipalign`/`apksigner`.
Test/tooling only (never prod path): commons-math3 (validator), commonmark (grammar-tests).

## Build & invocation
- `mvn -pl :cli -am package` → shade `cli/target/instr-cli.jar`, **auto-copied
  (design D9)** to `rv-android/modules/rv-instrumentation-dexlib2/lib/`.
- Main class `br.unb.cic.rv.cli.InstrumentationCli`; batch:
  `java -jar instr-cli.jar batch <apks-dir> --descriptor MultiSpec_1MonitorAspect.json --monitor-src-dir <mop> [--output <dir>]`.

## References (do not duplicate)
- `architecture.md` — deep canonical ref (931 lines).
- Grammar coverage matrix (living contract, CI-enforced): **lives OUTSIDE this
  module** at `rv-android/docs/aspectj_grammar_coverage.md`. Verdicts: `COVERED` /
  `SILENT-GAP` (0 post-gh62) / `EXPLICIT-NO-OP` / `NOT-NEEDED`. Supersedes
  `AJ_CONSTRUCTIONS_INVENTORY.md` + `AJ_TO_DEXLIB2_MAPPING.md` (INV-INS-102).
- `rv-android/openspec/specs/instrumentation/spec.md` (INV-INS-\*);
  `rv-android/openspec/changes/archive/2026-06-23-gh62-aspectj-grammar-coverage/deferred.md`.

## Gotchas
- Only the JSON descriptor is the contract; never parse `.aj` (INV-INS-56).
- Wrapper substitution is byte-stable (INV-INS-66).
- Frame growth needs `replaceImpl` or serialization drops the increment (INV-INS-80/87).
- Multidex preserved (INV-INS-52); register spill avoids VerifyError.
- `if()` lowering is **fork-free** (2 supported forms; else `UnsupportedAspectConstructError`).
- `grammar-tests` produces no main artifact; the matrix doc lives in the **rv-android** tree.
