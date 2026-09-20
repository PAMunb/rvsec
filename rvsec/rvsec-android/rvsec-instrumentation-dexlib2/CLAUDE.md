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

## Documentation conventions
Java in this module is documented with **Javadoc**, and the `rvsec-core` helper
classes the woven monitors call follow the same eleven rules.

1. **Depth by tier.** A public API class and an orchestrator (`DexWeaver`,
   `BatchRunner`, `MonitorBuilder`) carry a full class Javadoc; an internal
   method over ten lines carries a summary plus `@param`/`@return`; a small
   helper carries one line; a self-evident accessor, setter or `toString`
   carries **none** — the descriptor POJOs are deliberately bare, because the
   name and the signature already say everything there is to say.
2. **Noun phrase for a thing, imperative for an action.** A package or class
   Javadoc opens by saying what the thing *is* ("Register-level instruction
   rewriter used by the coverage spill path."). A method Javadoc opens with an
   imperative sentence ending in a period ("Compile the monitor sources, then
   run d8.").
3. **Topical `<h2>`/`<h3>` headings.** A long class Javadoc is sectioned by the
   subject each part covers — `<h3>Frame growth via clone</h3>`,
   `<h2>Register allocation strategy</h2>`, `<h2>Two mutation paths</h2>` — not
   by a fixed list of section names. Name the problem the section discusses.
4. **`@param`, `@return` and `@throws` carry no types** — the signature holds
   them. `@throws` states the condition that raises it, opening with "when" or
   "if":
   ```java
   /**
    * Grow the register frame of {@code impl} by {@code delta} slots.
    *
    * @param delta slots carved out at the low end of the frame
    * @return the rebuilt implementation; the caller swaps it in
    * @throws IllegalStateException if a shifted register overflows its
    *     format's field width
    */
   ```
5. **A field holding meaningful state carries a one-line Javadoc** saying what
   it holds and when it is valid (`/** Original {@link MethodReference} →
   wrapper {@link MethodReference}. */`). A field that is only an injected
   collaborator needs nothing.
6. **A `@return` of a map or a JSON document lists its keys.** The reader must
   not have to run the weaver to learn the shape of what comes back:
   ```java
   /**
    * @return per-APK counters, keyed by {@code "advices"} (advices in the
    *     descriptor), {@code "dexFiles"} (DEX entries extracted),
    *     {@code "wrappersGenerated"} and {@code "wovenDexes"}
    */
   ```
7. **`// Phase N:` for orchestration, `// Step N:` for an algorithm.** Phases
   number the stages of a pipeline method (`// Phase 3: extract DEX files from
   APK (preserving entry names).`); steps number the moves of a dense routine
   such as register shifting or pointcut parsing. A rationale block sits
   **directly above** the code it explains, never after it, and says *why* —
   the mechanism that makes the code non-obvious, not a paraphrase of it.
8. **Contracts use `MUST`/`MUST NOT` and `Precondition:`/`Postcondition:`.**
   An obligation the caller cannot infer from the signature is stated as an
   obligation ("the caller MUST replace its reference to the source
   implementation with the returned one"); a state the method assumes or
   guarantees is labelled as such.
9. **Cite code with `{@code}` and `{@link}`.** Identifiers, literals, DEX
   descriptors and instruction mnemonics go in `{@code}`; a type or member the
   reader should jump to goes in `{@link}`. Every `{@link}` target must exist —
   a dangling one is a broken reference the Javadoc build reports, and it is
   the cheapest kind of documentation rot to introduce.
10. **Nothing that lives outside the file.** No invariant, decision, task,
    change or issue identifier; no date; no `file:line`; no pointer to a design
    document or a report standing in for the explanation itself; no narrative
    of what the code used to do; no promotional adjectives. A comment is read
    with the file open and nothing else at hand, and it describes the code as
    it is now.
11. **`TODO(topic)` and `FIXME(topic)` name a module or a topic** —
    `TODO(coverage-weaver)`, `FIXME(register-spill)` — never an issue number,
    which ages out of the tracker and leaves the marker unreadable.

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
