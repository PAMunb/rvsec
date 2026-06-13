# Design: gh54-instrumentation-hardening

---

## STATUS: CLOSED — NOT IMPLEMENTED (2026-05-06)

Esta change foi arquivada sem implementação. Ver `proposal.md` (header de fechamento) e `## Closure findings` no final deste documento para a análise consolidada que motivou a decisão.

Os blocos seguintes (`## Context`, `## Architecture`, `## Goals / Non-Goals`, etc.) preservam o desenho original como registro histórico.

---

## Context

The `validacao_full` experiment (2026-05-05/06; 72 APKs × 2 variants × 2 tools × 3 reps × 5 min; 851 tasks; 11 h wall) established the empirical baseline that motivates this change. Mean `cov_rv_method` is **dex 42.65 % vs ajc 32.67 %** (Δ 10 pp). The gap is dominated by two distinct failure modes — AJC `VerifyError` in R8/Compose-obfuscated apps (8 / 72 APKs, 0 % coverage in NEW BROKEN category) and DEX `VerifyError` from register-alias mismatch at advice insertion sites (12 / 72 APKs, mixed OLD-CLEAN and NEW WORKS). Neither is a regression of an isolated commit: the AJC Frame Computer (`rvsec-frame-computer`) already runs both pre- and post-ajc and is structurally limited on Kotlin/Compose nest-mate access; the DEX bug stems from dexlib2 not narrowing register types when emitting injected `invoke` instructions, and DEX bytecode lacks JVM-style stackmap frames so a "recompute frames" fix has no off-the-shelf equivalent.

This design specifies three additive, low-risk mitigations that close the gap without rewriting either weaver from scratch. The proposal (`./proposal.md`) catalogues *what* changes; this document covers *how* — file paths, function signatures, and the contract enforced at each insertion point. Relevant requirements: FR01 (monitor generation), FR02 (instrumentation variants), FR03 (coverage tracking); no new FR introduced. Spec impact is confined to the `instrumentation` domain (`openspec/specs/instrumentation/spec.md`), three additive requirement deltas.

The change spans the single `PAMunb/rvsec` repository: two Java modules (`rvsec/rvsec-mop/`, `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`) and one Python module (`rv-android/modules/rv-instrumentation-core/`). A single PR ships all three, the Maven build re-bakes `instr-cli.jar` and copies it to the workspace via the existing D9 rule, and the Docker image is rebuilt no-cache before re-running the validation gate.

## Architecture

```
                      ┌─────────────────────────────────────────────┐
                      │  PAMunb/rvsec (single repo)                 │
                      ├─────────────────────────────────────────────┤
                      │                                             │
   APK input ───────► │  [B1] Instrumenter.validate_input_apk()    │
   (rv-experiment)    │       └─ rejects if classes*.dex contains   │
                      │          Lmop/ or ajc$ refs                 │
                      │                                             │
                      │  ┌─────────────────┐    ┌─────────────────┐ │
                      │  │  AJC variant    │    │  DEX variant    │ │
                      │  ├─────────────────┤    ├─────────────────┤ │
                      │  │ rv-monitor-gen  │    │ dexlib2 weaver  │ │
                      │  │ ─ Coverage.aj   │    │ ─ DexWeaver.java│ │
                      │  │   [A.AJC]       │    │   [A.DEX]       │ │
                      │  │   excludedPkgs  │    │   insertCheck-  │ │
                      │  │   += kotlin/    │    │   Cast() before │ │
                      │  │   compose/      │    │   each injected │ │
                      │  │   <clinit>      │    │   monitor invoke│ │
                      │  └─────────────────┘    └─────────────────┘ │
                      │            │                     │          │
                      │            ▼                     ▼          │
                      │       (instrumented APK ready for execution)│
                      └─────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `Coverage.aj` (resource) | AspectJ pointcut definitions for coverage probes | `.aj` source compiled by `ajc` at monitor-gen time | woven `.class` files with coverage advice |
| `Instrumenter.validate_input_apk()` (Python ABC) | Reject pre-instrumented APKs at the input gate | `Path` to APK | `None` (raises `ContaminationError`) |
| `DexWeaver.insertCheckCast()` (Java helper) | Emit `check-cast vN, Tcrypto;` before each injected `invoke` whose source register's type is not provably the monitor signature's expected type | `MutableMethodImplementation`, `int sourceReg`, `String expectedType` | mutated `MutableMethodImplementation` with prepended `check-cast` instruction |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Req 1 + INV-INS-42 (Coverage.aj excludes Kotlin/Compose/`<clinit>`) | `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj` — `excludedPackages()` extended with 4 new clauses | `rvsec-mop/src/test/...` — assert the new patterns are in the compiled aspect; smoke-run on `enigmadroid_16.apk` confirms no `VerifyError` in `r9.s.<clinit>` |
| Req 2 + INV-INS-43 (DEX weaver emits `check-cast` before typed crypto invokes) | `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java` — new `insertCheckCast(...)` helper + call from `weaveInvoke(...)` | `dex-mutator/src/test/.../DexWeaverCheckCastTest.java` — fixture method with `String` in v0, advice expects `SecureRandom`, assert generated bytecode has `check-cast v0, Ljava/security/SecureRandom;` immediately before the `invoke` |
| Req 3 + INV-INS-44 (Instrumenter rejects pre-instrumented input) | `rv-android/modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py` — new abstract default `validate_input_apk()` invoked from `instrument_apks()`; `ContaminationError` defined in new sibling `errors.py` module | `rv-instrumentation-core/tests/test_validate_input_apk.py` — feed a known contaminated APK fixture (re-uses `data/apks/com.aptasystems.dicewarepasswordgenerator_8.apk`), assert `ContaminationError` raised with 3-arg constructor |
| INV-INS-45 (RVSEC-COV recall ≥ 0.99 on app-package methods after exclusions) | `Coverage.aj` exclusions are bounded to library/synthetic packages — no app-package weaving sites are removed | `validator-cli layer5 --oracle oracles/cryptoapp-oracle.yaml --apk <instrumented cryptoapp>` against an A.AJC build; recall computed by the harness on app-package methods only |
| Acceptance gate (empirical, layer-4-equivalent) | re-run `validacao_full` (72 APKs, same config) → gap dex-ajc < 5 pp per category | `out/validacao_full_consolidated/REPORT.md` updated with post-fix numbers; pre/post comparison table cross-linked to `docs/20260426_dexlib2_validation_results.md` §5 |

## Goals / Non-Goals

**Goals:**
- Eliminate the AJC `VerifyError` failures triggered by `Coverage.aj` weaving Kotlin/Compose synthetic code (target: 8 / 72 → ≤ 2 / 72 broken APKs)
- Eliminate the DEX register-alias `VerifyError` failures (target: 12 / 72 → ≤ 2 / 72 broken APKs)
- Prevent silent re-instrumentation of already-processed APKs (target: 100 % rejection at input)
- Maintain or improve mean `cov_rv_method` for OLD-CLEAN APKs (no regression in apps where both variants work today)
- Reduce dex-ajc gap below 5 pp in each of the three categories (OLD-CLEAN, NEW BROKEN, NEW WORKS)

**Non-Goals:**
- Architectural rewrite of the AJC Frame Computer (limitation is in ASM's stackmap inference on R8 nest-mate code; out of scope)
- DEX liveness analysis with new register allocation (would replace dexlib2's local insertion model; out of scope)
- Removing AJC variant entirely (gh52 §18.8 already established AJC as opt-in; this change keeps it usable, not default)
- Modifying the rv-monitor template generator to emit `Object`-typed signatures (upstream tool; cross-project surgery avoided)
- Per-APK fallback dispatch between dexlib2 and AJC (hybrid approach explored and rejected as too complex for current scope)

## Decisions

### Decision 1 — A.AJC: extend `excludedPackages()` rather than refactor Coverage.aj or add per-class skip

**Choice**: add four clauses to the existing `excludedPackages()` pointcut:
```aspectj
|| within(kotlin..*)
|| within(kotlinx..*)
|| within(androidx.compose..*)
|| execution(* *<clinit>(..))
```

**Alternatives considered**:
- *Delete `Coverage.aj` entirely*: loses all coverage tracking; not viable.
- *Per-class deny list maintained in YAML* (similar to `weaving_excludes.yaml` in gh50): adds runtime config surface for what is structurally a static rule; rejected for unnecessary complexity.
- *Runtime try/catch wrapper around every advice body*: would hide real bugs and degrade debuggability; rejected per principle "defensive code masks failures".

**Rationale**: the 4 patterns are universally applicable (no app should be monitoring its own Kotlin stdlib calls or Compose internals; class initializers are notoriously fragile under bytecode rewrite). Additive change preserves existing behaviour for non-Compose apps. Reversible by removing the clauses if a regression appears.

### Decision 2 — A.DEX: emit `check-cast` at the weaver, not change monitor signatures

**Choice**: in `DexWeaver`, immediately before each injected `invoke` to a monitor method whose signature declares a typed crypto parameter (`SecureRandom`, `KeyPair`, `SecretKey`, `IvParameterSpec`, `MessageDigest`, `Cipher`, etc.), emit:
```
check-cast vSourceReg, L<expectedCryptoType>;
invoke-static {vSourceReg, ...}, monitor.on_event:(L<expectedCryptoType>;...)V
```
The check-cast is unconditional (we always emit it; Android's verifier elides the dynamic check at runtime when it can prove the type narrows trivially). At runtime, if the source register actually contains a wrong type, `check-cast` throws `ClassCastException` — caught by the surrounding monitor try/catch (already present in the rv-monitor templates). The call site never reaches the `invoke` with a verifier-mismatched type.

**Alternatives considered**:
- *Type-erased monitor signatures (`Object` everywhere)*: requires patching the rv-monitor / JavaMOP template generator (upstream, dormant since 2021). Rejected as out-of-scope cross-project work.
- *Liveness analysis at insertion site to skip injection when type is uncertain*: would silently lose coverage; harder to reason about; rejected.
- *Try/catch wrapper around the entire injected `invoke`*: doesn't help because the `VerifyError` happens at class load, before any code runs; rejected.

**Rationale**: `check-cast` is a single DEX instruction; bytecode overhead is one instruction per advice site (a few KB total for a typical APK). Verifier sees the post-cast register as the correct type, so class loads successfully. Runtime `ClassCastException` is the right semantic ("we tried to monitor X but the call wasn't actually X"), and is harmless under the existing monitor try/catch.

### Decision 3 — B1: enforce contamination check in the ABC, not in `rv-experiment`

**Choice**: add a default method `validate_input_apk(apk_path: Path) -> None` to the `Instrumenter` ABC in `rv-instrumentation-core`. Both variant subclasses (`AjcInstrumentation`, `DexlibInstrumentation`) inherit it; both call it from `instrument_apks()` before any decompile/weaving step. Implementation reads `classes*.dex` via `androguard` and rejects if `Lmop/` or `ajc$` references are present.

**Alternatives considered**:
- *Enforce in `rv-experiment.PreProcessor`*: too late — variant-agnostic precondition belongs at the variant boundary. Also duplicates check across both variants if added per-variant.
- *Optional flag (opt-in)*: silently allowing contaminated input was the failure mode that produced the smoke v1 artefact (3 h investigation lost); fail-fast is the right default.
- *Per-call CLI flag to the dexlib2 `instr-cli.jar`*: limits to one variant; ABC default avoids duplication.

**Rationale**: the ABC is the right contract boundary. Default method (not abstract) means subclasses inherit "for free" with zero LOC change; subclasses can override only if they have variant-specific stricter rules.

## API Design

### `Instrumenter.validate_input_apk(apk_path: Path) -> None` *(new, in ABC `rv-instrumentation-core`)*

**Pre**: `apk_path.is_file()`. **Post**: returns `None` if APK is clean (no `Lmop/` or `ajc$` references in any `classes*.dex`); raises otherwise.

**Errors**: `ContaminationError(apk_path: Path, found_lmop_refs: int, found_ajc_refs: int)` — new exception in `rv_instrumentation_core.errors` (the `errors.py` module is also new — `rv-instrumentation-core` currently has no dedicated exceptions module; this change introduces it, mirroring the pattern already used by `rv-instrumentation-dexlib2`). Message format: `"APK {apk_path.name} appears already instrumented (found {found_lmop_refs} Lmop/ and {found_ajc_refs} ajc$ references). Re-instrumentation is not supported; use a clean original APK from the source dataset."`

**Called from**: `Instrumenter.instrument_apks(apks_dir, results_dir, apk_paths)` — for each APK in the iteration loop, `validate_input_apk(apk_path)` is invoked first; on `ContaminationError`, the APK is added to `instrument_errors.json` with phase=`"validation"` and the loop continues with the next APK (one bad APK doesn't abort the batch).

### `DexWeaver.insertCheckCast(impl: MutableMethodImplementation, sourceReg: int, expectedJniType: String) -> void` *(new, Java)*

**Pre**: `impl` is the in-progress weave; `sourceReg` is the register from which the next emitted `invoke` will read its first non-receiver argument; `expectedJniType` is the JNI form (e.g. `Ljava/security/SecureRandom;`) of the monitor signature's declared type. **Post**: prepends `check-cast vSourceReg, expectedJniType` to the next instruction emitted on `impl`.

**Errors**: none from this helper itself. At runtime, an injected `check-cast` may throw `ClassCastException`; the existing rv-monitor advice template wraps the dispatch in try/catch and records the case as a coverage event without firing the FSM transition.

**Called from**: `DexWeaver.weaveInvoke(...)` (the existing per-call-site weave method) — added unconditionally before each `invoke` whose target signature declares a typed reference parameter from a fixed allow-list of crypto types (initial list: `SecureRandom`, `KeyPair`, `KeyPairGenerator`, `KeyGenerator`, `Cipher`, `MessageDigest`, `Mac`, `KeyStore`, `SSLContext`, `TrustManagerFactory`, `KeyManagerFactory`, `Signature`, `SecretKey`, `SecretKeySpec`, `IvParameterSpec`, `PBEKeySpec`, `PBEParameterSpec`, `GCMParameterSpec`, `DHGenParameterSpec`, `IHMACParameterSpec`).

### `Coverage.aj` extension *(modified resource)*

The diff is purely additive in `excludedPackages()`. No public API change.

## Data Flow

```
                                 ┌─────────────────────┐
   rv-experiment ───────────────►│ PreProcessor        │
   .instrument_apks()             │ .instrument_apks()  │
                                  └──────────┬──────────┘
                                             │ for each APK
                                             ▼
                                  ┌──────────────────────────┐
                                  │ [B1] validate_input_apk  │ ◄── NEW
                                  │   raises if contaminated │
                                  └──────────┬───────────────┘
                                             │ clean
                                             ▼
                            ┌────────────────┴────────────────┐
                            │                                 │
                  ┌─────────▼──────────┐         ┌────────────▼──────────┐
                  │ AJC variant        │         │ DEX variant           │
                  │                    │         │                       │
                  │ rv-monitor-gen     │         │ instr-cli.jar         │
                  │  reads Coverage.aj │         │  DexWeaver.weave...() │
                  │  [A.AJC] new       │         │  [A.DEX] insertCheck- │
                  │  excludes apply    │         │  Cast() before each   │
                  │                    │         │  injected invoke      │
                  │ ajc weave + frame  │         │                       │
                  │ recompute (existing)│        │ dexlib2 patch +       │
                  │                    │         │ repackage             │
                  │ d8 → APK           │         │ apksigner → APK       │
                  └────────────────────┘         └───────────────────────┘
```

The AJC pipeline picks up the new `Coverage.aj` exclusions at monitor-generation time (they are compiled into the aspect classes). The DEX pipeline picks up the new `insertCheckCast` calls when the rebuilt `instr-cli.jar` is consumed by the Python wrapper (Maven D9 auto-copy). Both variants gain the B1 precondition automatically (default method on ABC).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ContaminationError` | B1 — `validate_input_apk` detects `Lmop/`/`ajc$` in input | Record in `instrument_errors.json` with `phase=validation`, skip this APK, continue batch | User instruments a clean copy from the source dataset (`/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS/` or `JOAO/APKs/`) |
| `ClassCastException` (runtime, in app) | A.DEX — injected `check-cast` proves the source register isn't actually the expected type | Caught by existing rv-monitor advice template's try/catch | Coverage event still emitted; FSM transition skipped; logged at advice level |
| `VerifyError` (runtime, in app) | Residual cases not covered by A.AJC or A.DEX (~2 APKs estimated) | Same as today — APK crashes, rep records 0 % coverage | Documented limitation; future work tracked in next change |
| Java compile failure (Coverage.aj) | A.AJC — typo in new exclusion clauses | Maven build fails fast; CI gate blocks PR | Fix syntax, re-build |

## Risks / Trade-offs

- **A.AJC may exclude legitimate Compose-internal calls to JCA APIs** → Mitigation: in practice, Compose UI code rarely calls JCA directly; if a regression appears, narrow exclusions to specific subpackages (e.g., `androidx.compose.ui..*` only). Reversible.
- **A.DEX `check-cast` adds bytecode overhead** → Mitigation: ~1 instruction per advice site; total APK size growth measured in KB, not MB. ART optimises trivially-narrowing casts at JIT time.
- **A.DEX `ClassCastException` at runtime may crash the app if uncaught** → Mitigation: rv-monitor advice template already wraps dispatch in try/catch (verified in current code); if a future spec template removes that, this design must be revisited.
- **B1 may reject APKs that legitimately ship `mop/` or `ajc$` packages** (e.g., a third-party app that happens to use a class named like our monitors) → Mitigation: heuristic is conservative (require both `Lmop/` AND `ajc$` references? or check signature pattern? — to be tightened during implementation if a false positive appears in `validacao_full` rerun).
- **Validation gate may not converge to < 5 pp** → Mitigation: if post-fix run shows residual gap, the failure modes must be re-analysed and the next iteration scoped before declaring the change complete. Acceptance criterion is empirical, not pass/fail on tests alone.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java, dex-mutator) | `DexWeaver.insertCheckCast` emits correct DEX opcode for each crypto type; idempotence under repeat invocation | JUnit + dexlib2 fixture method | ~5 tests |
| Unit (Python, rv-instrumentation-core) | `validate_input_apk` rejects contaminated, accepts clean, raises typed exception with diagnostic message | pytest with two APK fixtures (`data/apks/com.aptasystems...apk` contaminated, `cryptoapp.apk` clean) | ~3 tests |
| Integration (Java, dexlib2 weaver) | End-to-end weave on a fixture APK with mixed JCA usage; assert generated DEX has `check-cast` before each monitor invoke; ART verifier (via `dexdump --check-mode=safe`) accepts result | JUnit + cryptoapp.apk fixture | ~2 tests |
| Integration (smoke, both variants) | Re-instrument and run 1 APK from each forensic group: enigma (R8/Compose), muspyforandroid (DEX register-alias), cryptoapp (control). Verify coverage > 0 for all | `rv-experiment run` with `--apks-filter` | 3 APKs × 2 variants × 1 rep |
| Validator harness Layer 0 | INV-INS-42/43/44/45 enforced by `rvsec-instrumentation-dexlib2/validator/` test suite | `mvn -pl validator test -Dtest=InvariantTest` | 4 invariant tests |
| Validator harness Layer 5 | RVSEC-COV recall on app-package methods ≥ 0.99 against cryptoapp oracle (proves A.AJC exclusions don't leak into app code) | `validator-cli layer5 --oracle oracles/cryptoapp-oracle.yaml --apk <instrumented cryptoapp>` | 1 oracle run |
| Validation gate | Re-run `validacao_full` (72 APKs, identical config to 2026-05-05/06 baseline). Compare per-category mean cov_rv_method. Gap dex-ajc < 5 pp in each of OLD-CLEAN, NEW BROKEN, NEW WORKS | `docker compose -f docker/docker-compose.validacao-full.yml up -d` after image rebuild | 864 tasks (~11 h) |

## Open Questions

- **Q1 — B1 heuristic strength**: should `validate_input_apk` require BOTH `Lmop/` AND `ajc$` references (current design), or just one as sufficient signal? Current design errs on the conservative side (require both) to avoid false positives on third-party packages that happen to be named `mop`. To be tightened during impl if `validacao_full` rerun shows missed contamination.
- **Q2 — A.DEX type allow-list**: the initial list of 20 crypto types covers all current MOP specs, but future `.mop` additions could declare new typed parameters. Should `insertCheckCast` derive the list dynamically from the loaded monitor signatures, or maintain it as a static constant in `DexWeaver`? Current design: static constant for simplicity; revisit if MOP spec churn becomes an issue.
- **Q3 — Should the change include deletion of `weaving_excludes.yaml`** (the gh50 quarantine list, demonstrated empirically to filter < 0.2 % of events)? Out of scope for this change but candidate for a follow-up cleanup once gh54 lands.

---

## Closure findings (2026-05-06)

### Verificação A.DEX — state drift confirmado

Procedimento: `grep` + leitura direta no `DexWeaver.java` canônico (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java`).

**Achado**: `DexWeaver:71-78` documenta o mecanismo `wrapperReplacements`:

> *"Original MethodReference → wrapper MethodReference. When an invoke instruction matches a key, the weaver REPLACES the invoke's reference with the wrapper (instead of inserting an inline hook), eliminating the register-aliasing class of bug (INV-INS-29): the wrapper is a static method that calls the original AND fires the monitor events, all using its own local register frame, so the caller's registers stay byte-identical."*

`DexWeaver:79`: `private final Map<String, MethodReference> wrapperReplacements;`
`DexWeaver:87`: `private final java.util.List<WrapperEmitter.WrapperEntry> registeredWrappers;`
`DexWeaver:104-114`: construtor injeta a list de wrappers; `registerWrapper()` faz o registro per-entry.

Mecanismo é **superior** ao check-cast proposto:
- Check-cast convence o ART verifier vendo um tipo no registrador, mas o registrador caller continua exposto a aliasing
- Wrapper roda em um method static separado com seu próprio frame, isolando completamente o caller

Smoke ratificado em `docs/20260426_dexlib2_validation_results.md:310-366`:
- 19/20 APKs instrumentadas (95%); falha foi INV-INS-32 (registro >v15 com `Format35c` — emitter, não register-aliasing)
- 18/18 executadas: **0 VerifyError** (tabela `:341-342`)
- "INV-INS-29 + INV-INS-31 (commit `2e64e848`) hold empirically across this expanded 18-APK cohort" (`:365-366`)

Veredicto: **A.DEX não é necessária**. Adicionar check-cast por cima de wrappers duplica correção, soma overhead, e arrisca regressão de gap em OLD-CLEAN.

### Análise A.AJC — mecânica fraca contra R8

`Coverage.aj` real (`rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj:22-46`) já contém `within(androidx..*)` (linha 29) e `within(kotlin..*)` (linha 30). Das 4 cláusulas propostas em A.AJC:

| Cláusula | Status | Casa que padrão diagnosticado? |
|---|---|---|
| `within(kotlin..*)` | **redundante** (linha 30) | `r9.s` (R8 default package) — não casa |
| `within(androidx.compose..*)` | **redundante** (subset de `androidx..*`) | `t8.c` (R8 default package) — não casa |
| `within(kotlinx..*)` | nova | nenhum dos 3 padrões — não casa |
| `execution(* *<clinit>(..))` | nova | `r9.s.<clinit>` — **casa** ✓ |

Padrões diagnosticados no baseline:
- `r9.s.<clinit>` — casa via `<clinit>` ✓
- `t8.c.z(View, KeyEvent)` — método regular, não casa por nenhuma das 4 cláusulas
- `l3.h.<init>(View)` — constructor (`<init>` ≠ `<clinit>`), não casa

Estimativa: A.AJC recuperaria 1-2 de 6 APKs NEW BROKEN, deixando gap residual ~58pp. Gate `< 5pp` não converge.

Pivot para signature pattern (`^[a-z][0-9]+\.`) traria risco de over-exclusion sem oracle Kotlin/Compose — cryptoapp atual é puro Java e não testa essa dimensão. Construir oracle Kotlin/Compose é não-trivial (4-6h adicionais sem garantia de que mecanismo funciona).

### Análise B1 — falha lógica + valor incremental baixo

Inconsistência cross-artifact: proposal narra OR, design/spec normativos exigem AND. Design listou Q1 como aberta (`design.md:206`) enquanto spec já hardcoda como requirement (spec.md:101). Sem fonte única de verdade.

Falha lógica: AND requer `Lmop/` E `ajc$`. APKs instrumentadas pela variante dexlib2 (default pós-2026-05-06 conforme memória `today-2026-05-06.md`: *"dexlib2 default ✓ (gh52 §18.8); AJC opt-in enabled w/ warning"*) têm `Lmop/` mas não `ajc$`. AND **não casa contaminação no fluxo padrão** — derrota o propósito declarado.

Correção necessária seria filtro de assinatura específica (`Lmop/MultiSpec_[A-Za-z]+(MonitorAspect|RvMonitor);`). Trabalho não-trivial (regex compilada de single source-of-truth, garantia de não-deriva com rv-monitor codegen).

Custo do incidente smoke v1: 3h investigação, evento único em 6 meses. Ambiente Docker controlado torna recorrência improvável. Higiene operacional não justifica o trabalho de reformular.

### Cross-revisão multi-LLM

Três análises produzidas em paralelo:

| Revisor | Veredicto | Blockers principais |
|---|---|---|
| Claude Opus 4.7 (`docs/analise_claude.md`) | NÃO PRONTA | A.AJC redundante+R8-fraca; B1 false-negative dexlib2; typo `IHMACParameterSpec`; gate delta-based; `weaveInvoke` fictício |
| Codex (`docs/analise_codex.md`) | NÃO PRONTA | A.DEX state drift (wrappers); L0 `InvariantTest` inexistente; L5 CLI errado; B1 contradição requirement vs Q1 |
| Gemini CLI (`docs/analise_gemini.md`) | PRONTA | nenhum |

Dois de três revisores convergiram em "NÃO PRONTA" com auditoria in loco. Gemini fez análise leve sem verificar código real. Claude e Codex bateram em problemas materialmente verificáveis (e verificados na fase de fechamento).

### Decisão

Arquivar gh54 sem implementar. Documentar regressão AJC R8/Compose como **categoria-específica aceita** (~8% do dataset). AJC permanece opt-in conservador, dexlib2 default cobre o gap. Reabertura como gh55 só se condições materiais mudarem (modernização API 30, novo mecanismo de VerifyError não coberto pelo wrapper, ou higiene operacional virar problema recorrente).
