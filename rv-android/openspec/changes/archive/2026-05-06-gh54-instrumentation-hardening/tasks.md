# Tasks: gh54-instrumentation-hardening

---

## STATUS: ABANDONED — NO TASKS EXECUTED (2026-05-06)

**Nenhum dos 7 task groups abaixo foi executado.** Todos permanecem com `[ ]` (não-completos) por design — esta é a representação canônica do estado "change arquivada sem implementação".

### Rationale por grupo (rastreabilidade reversa)

| Grupo | Mitigação | Por que não foi executado |
|---|---|---|
| 1. A.AJC — Coverage.aj exclusions | A.AJC | Mecânica fraca: 2 das 4 cláusulas são redundantes (`kotlin..*` e `androidx..*` já em `Coverage.aj:29-30`); R8-obfuscated names não casam exclusões por pacote; só 1 de 3 padrões diagnosticados (`r9.s.<clinit>`) seria coberto. Pivot para signature pattern requer oracle Kotlin/Compose não-trivial. Regressão R8/Compose já caracterizada como categoria-específica aceita. |
| 2. A.DEX — DexWeaver insertCheckCast | A.DEX | State drift confirmado: `DexWeaver:71-78` já implementa `wrapperReplacements` (mecanismo superior — wrapper static method com frame isolado, em vez de check-cast). Smoke `gh52_smoke20_newdata` (`docs/20260426_dexlib2_validation_results.md:310-366`) ratifica 18/18 zero VerifyError. Adicionar check-cast por cima duplica correção. Typo na allow-list (`IHMACParameterSpec` não existe) é sintoma de auditoria insuficiente. |
| 3. B1 — validate_input_apk | B1 | Rejeitada pelo escopo: incidente raro, ambiente Docker controlado. Falha lógica adicional: AND não casa contaminação dexlib2 (default pós-2026-05-06) — derrota o propósito. Correção exigiria filtro `Lmop/MultiSpec_*` específico, trabalho não justificado pelo benefício marginal. |
| 4. Build artefatos (Maven + Docker rebuild) | (suporte) | Sem mudanças em A.AJC/A.DEX/B1, não há o que rebuildar. Imagem `phtcosta/rvandroid:0.8.0` permanece como está. |
| 5. Smoke validation | (suporte) | Sem implementação para validar. APKs forenses (enigmadroid, muspyforandroid, dicewarepasswordgenerator) permanecem disponíveis para futuras investigações. |
| 6. Validation gate (re-run validacao_full) | (suporte) | Re-run de 11h não justificável sem fixes. Baseline em `out/validacao_full_consolidated/REPORT.md` permanece como estado-da-arte; gap dex-ajc é aceito como categoria-específica. |
| 7. Final QA (lint, verify, docs sync, code review) | (suporte) | Sem diff a revisar. |

### Cross-references

- Análises LLM: `docs/analise_claude.md`, `docs/analise_codex.md`, `docs/analise_gemini.md`
- Verificação in loco do A.DEX state drift: `DexWeaver.java:71-78`, `docs/20260426_dexlib2_validation_results.md:310-366`
- Memórias: `project_ajc_validacao_full_2026-05-06.md` (regressão categoria-específica aceita), `project_modernization_research_2026-05-02.md` (caminho alternativo)

Os grupos seguintes preservam o plano original como registro histórico — não há ação esperada.

---

## 1. A.AJC — Coverage.aj pointcut exclusions

- [ ] 1.1 Edit `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj` — add 4 clauses to `excludedPackages()`: `within(kotlin..*)`, `within(kotlinx..*)`, `within(androidx.compose..*)`, `execution(* *<clinit>(..))`
- [ ] 1.2 Add unit test under `rvsec/rvsec-mop/src/test/` asserting the compiled aspect's pointcut definition contains the 4 new exclusion patterns (parse the generated `.aj` or check the AspectJ XML metadata)
- [ ] 1.3 Run `mvn -pl rvsec/rvsec-mop -am clean install -DskipTests=false` from repo root to verify the resource compiles cleanly

## 2. A.DEX — DexWeaver insertCheckCast helper

- [ ] 2.1 Add `insertCheckCast(MutableMethodImplementation impl, int sourceReg, String expectedJniType)` method to `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java` — emits a `BuilderInstruction21c(Opcode.CHECK_CAST, ...)` reading from and writing to `sourceReg`. Signature matches `design.md` API Design (parameter name `expectedJniType` is the JNI form like `Ljava/security/SecureRandom;`)
- [ ] 2.2 Define static allow-list `CRYPTO_TYPES` in `DexWeaver`: 20 JNI type descriptors covering SecureRandom, KeyPair, KeyPairGenerator, KeyGenerator, Cipher, MessageDigest, Mac, KeyStore, SSLContext, TrustManagerFactory, KeyManagerFactory, Signature, SecretKey, SecretKeySpec, IvParameterSpec, PBEKeySpec, PBEParameterSpec, GCMParameterSpec, DHGenParameterSpec, IHMACParameterSpec
- [ ] 2.3 Modify the existing `weaveInvoke(...)` (or equivalent advice-emission path) to call `insertCheckCast` before each injected `invoke` whose target signature's first non-receiver parameter type is in `CRYPTO_TYPES`
- [ ] 2.4 Add `DexWeaverCheckCastTest.java` with at least 5 fixtures: (a) String register → SecureRandom expected (cast emitted), (b) byte[] register → SecretKeySpec expected (cast emitted), (c) SecureRandom register → SecureRandom expected (cast still emitted), (d) non-crypto invoke (no cast emitted), (e) repeated invoke same method (idempotent — one cast per call site)
- [ ] 2.5 Run `mvn -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator -am clean install` to verify build + tests
- [ ] 2.6 Verify Maven D9 auto-copy populated `rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` with the rebuilt fat CLI

## 3. B1 — Instrumenter.validate_input_apk

- [ ] 3.1 Create new file `rv-android/modules/rv-instrumentation-core/src/rv_instrumentation_core/errors.py` (does NOT exist today — `rv-instrumentation-core` currently has no dedicated exceptions module). Define `ContaminationError(apk_path: Path, found_lmop_refs: int, found_ajc_refs: int)` with the message format specified in the spec. Re-export it from `__init__.py` for the package's public API. Pattern mirrors `rv-instrumentation-dexlib2/.../errors.py`
- [ ] 3.2 Add default `validate_input_apk(apk_path: Path) -> None` method to the `Instrumenter` ABC in `rv-android/modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py`. Use `androguard.core.bytecodes.apk.APK` to enumerate `classes*.dex` entries and grep for `Lmop/` and `ajc$` patterns; raise `ContaminationError` only when BOTH are present (conservative heuristic per design Q1)
- [ ] 3.3 Wire `validate_input_apk(apk_path)` into both subclasses' `instrument_apks()` per-APK loop in `rv-android/modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py` and `rv-android/modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py`. On `ContaminationError`, record under `phase=validation` in `instrument_errors.json` and continue the batch (do NOT abort)
- [ ] 3.4 Add `rv-android/modules/rv-instrumentation-core/tests/test_validate_input_apk.py` with 4 tests: (a) clean APK passes, (b) contaminated APK raises `ContaminationError` with diagnostic, (c) APK with only `Lmop/` references but no `ajc$` passes, (d) APK with only `ajc$` references but no `Lmop/` passes
- [ ] 3.5 Run `/rv-doc-code modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py` to refresh docstrings
- [ ] 3.6 Run `/rv-test-run rv-instrumentation-core`

## 4. Build artefacts

- [ ] 4.1 Run `mvn -B clean install -DskipTests` from repo root to rebuild Java side (rvsec-mop + dexlib2 fat CLI) and propagate artefacts via Maven D9
- [ ] 4.2 Run `bash docker/rvandroid/build.sh` (no-cache rebuild of `phtcosta/rvandroid:0.8.0`) so the new Coverage.aj asset and the new instr-cli.jar are baked in
- [ ] 4.3 Verify `docker images phtcosta/rvandroid:0.8.0` shows a creation timestamp matching the rebuild

## 5. Smoke validation

- [ ] 5.1 AJC smoke: re-instrument `io.github.deprec8.enigmadroid_16.apk` with the AJC variant; assert the resulting APK installs on emulator and that `[APE] // Short Msg: java.lang.VerifyError` does NOT appear in the trace for class `r9.s` (the previously-failing class)
- [ ] 5.2 DEX smoke: re-instrument `com.danielme.muspyforandroid_3.apk` with the DEX variant; verify `dexdump -d` of the output shows `check-cast` immediately before each injected `invoke` to a `mop/MultiSpec_*MonitorAspect` method with a typed crypto parameter
- [ ] 5.3 B1 smoke: pass `data/apks/com.aptasystems.dicewarepasswordgenerator_8.apk` (the contaminated APK from the smoke v1 incident) to either variant's `instrument_apks()`; verify `ContaminationError` is recorded in `instrument_errors.json` with `phase=validation`
- [ ] 5.4 Control smoke: re-instrument `cryptoapp.apk` (a known-clean baseline) with both variants and confirm coverage matches the validacao_v2 baseline (100 % cov_rv_method, 4 errors captured in 3 reps) within ±2 pp

## 6. Validation gate

This change reuses the validator harness shipped with gh52 (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/`) for Layer 0 and Layer 5 gates, plus a Layer-4-equivalent re-run of `validacao_full` for the empirical coverage gate. Layers 1 and 3 are NOT included (Layer 1 would falsely flag the intentional A.AJC exclusions; Layer 3 overlaps with the validacao_full re-run at smaller scale).

### 6a. Layer 0 — Invariants (static gates)

- [ ] 6.1 Run `mvn -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator test -Dtest=InvariantTest` to validate the existing invariant suite plus the 3 new ones (INV-INS-42, INV-INS-43, INV-INS-44, INV-INS-45). All MUST pass green.
- [ ] 6.2 If the validator harness does not yet have test cases for INV-INS-42..45, add them under `validator/src/test/java/.../InvariantTest.java` before the run.

### 6b. Layer 5 — Coverage recall (cryptoapp oracle)

- [ ] 6.3 Run `validator-cli layer5 --oracle oracles/cryptoapp-oracle.yaml --apk <instrumented cryptoapp>` against an A.AJC-instrumented cryptoapp build. Assert `RVSEC-COV` recall ≥ 0.99 on app-package methods (per INV-INS-45). The cryptoapp is pure Java (no Kotlin/Compose) so the new exclusions MUST be no-ops on its app code.
- [ ] 6.4 Document layer5 output (recall numbers, pass/fail) in `out/validacao_full_consolidated/REPORT.md` post-fix section.

### 6c. Layer 4-equivalent — empirical re-run of validacao_full

- [ ] 6.5 Re-launch `docker compose -f docker/docker-compose.validacao-full.yml up -d` with the rebuilt 0.8.0 image
- [ ] 6.6 Wait for all 10 containers to exit (~11 h wall, monitored periodically)
- [ ] 6.7 Re-run the consolidation script that produced `out/validacao_full_consolidated/{REPORT.md,consolidated_summary.csv,per_variant_category_tool.csv}`
- [ ] 6.8 Append a "Post-fix" section to `REPORT.md` with side-by-side per-category comparison: pre-fix (baseline 2026-05-05/06) vs post-fix means, deltas, and pass/fail against the < 5 pp gap acceptance criterion in each of OLD-CLEAN, NEW BROKEN, NEW WORKS
- [ ] 6.9 Cross-link the post-fix section to `docs/20260426_dexlib2_validation_results.md` §5 (where the parallel-session gh52 Phase 5 ratification will land) so both documents reference the same empirical numbers

## 7. Final QA

- [ ] 7.1 Run `/rv-qa-lint-fix rv-instrumentation-core` and `/rv-qa-lint-fix rv-instrumentation-ajc` and `/rv-qa-lint-fix rv-instrumentation-dexlib2`
- [ ] 7.2 Run `/rv-verify rv-instrumentation-core` and `/rv-verify rv-instrumentation-ajc` and `/rv-verify rv-instrumentation-dexlib2`
- [ ] 7.3 Update `modules/rv-instrumentation-core/CLAUDE.md` and `modules/rv-instrumentation-{ajc,dexlib2}/CLAUDE.md` to document the new B1 contract on the Instrumenter ABC
- [ ] 7.4 Run `/rv-docs-sync rv-instrumentation-core` to align module docs with the new behaviour
- [ ] 7.5 Invoke `/rv-code-reviewer` via Skill tool to review the full diff (Java + Python + tests + docs)
