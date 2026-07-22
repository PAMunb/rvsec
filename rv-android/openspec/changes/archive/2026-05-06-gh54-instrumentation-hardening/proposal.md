# Proposal: Instrumentation hardening — Kotlin/Compose exclusion, DEX register-alias workaround, pre-flight contamination check

GitHub Issue: #54

---

## STATUS: CLOSED — NOT IMPLEMENTED (2026-05-06)

**Decisão**: arquivar sem implementar. Nenhuma das três mitigações propostas chega à implementação. Este artefato é preservado como registro histórico da investigação.

**Motivos consolidados** (cross-revisão por Claude Opus 4.7, Codex e Gemini CLI; veredicto de duas das três análises foi "NÃO PRONTA"; Gemini foi "PRONTA" mas sem auditoria in loco):

### A.DEX é redundante (state drift confirmado in loco)

A proposta de emitir `check-cast` antes de cada `invoke` injetado é **state drift**. A correção de register-aliasing já foi implementada via `WrapperEmitter` em gh52 (commit `2e64e848`, INV-INS-29):

> **`DexWeaver.java:71-78`** (verificado em `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java`):
> *"Original MethodReference → wrapper MethodReference. When an invoke instruction matches a key, the weaver REPLACES the invoke's reference with the wrapper (instead of inserting an inline hook), eliminating the register-aliasing class of bug (INV-INS-29): the wrapper is a static method that calls the original AND fires the monitor events, all using its own local register frame, so the caller's registers stay byte-identical."*

O wrapper é mecanismo **mais forte** que check-cast — elimina a classe inteira do bug, em vez de apenas convencer o verifier ART. Smoke ratificado:

> **`docs/20260426_dexlib2_validation_results.md:310-366`**: *"19/20 APKs traversed the full dexlib2 instrumentation pipeline. Of the 18 that also reached runtime on the API-30 emulator, **100% (18/18)** booted, ran APE-RV exploration, and produced a logcat with ZERO `VerifyError`. INV-INS-29 + INV-INS-31 (commit `2e64e848`) hold empirically across this expanded 18-APK cohort."*

Adicionar check-cast por cima duplicaria correção, somaria overhead sem benefício, e arrisca regressão simétrica em OLD-CLEAN (sobe DEX sem subir AJC, ampliaria gap em vez de fechá-lo).

### A.AJC tem mecânica fraca contra R8

Análise mecânica das exclusões propostas contra os padrões reais diagnosticados no baseline:

- `Coverage.aj:29-30` JÁ contém `within(androidx..*)` e `within(kotlin..*)` — duas das quatro cláusulas propostas são **redundantes** (a delta efetiva é só `kotlinx..*` + `<clinit>`).
- Classes que falharam no baseline são R8-obfuscadas para nomes flat curtos (`r9.s.<clinit>`, `t8.c.z`, `l3.h.<init>`) — vivem no default package, não em `kotlin.*`/`androidx.compose.*`. Logo as exclusões por pacote **não casam** R8-obfuscated names.
- Apenas `execution(* *<clinit>(..))` casa `r9.s.<clinit>`. Os outros dois padrões (método regular `t8.c.z`, constructor `l3.h.<init>`) ficariam não-cobertos.

Estimativa quantitativa: A.AJC como formulada recuperaria 1-2 de 6 APKs NEW BROKEN no melhor caso, deixando o gap em ~58pp (gate de 5pp não converge). Reformular para padrão de assinatura R8 (`^[a-z][0-9]+\.`) traria risco de over-exclusion em código de app legítimo, e exigiria construir oracle Kotlin/Compose para Layer 5 (cryptoapp atual é puro Java, não testa essa dimensão).

### B1 não tem valor incremental

O detector de APKs já-instrumentadas (precondition no `Instrumenter` ABC) foi rejeitado: o smoke v1 incident é evento raro em ambiente Docker controlado e o custo do incidente foi pontual. O design original tinha falha lógica adicional — AND de `Lmop/` E `ajc$` produz falso-negativo no fluxo default dexlib2 (que emite `Lmop/` mas não `ajc$`); a correção exigiria reformular como filtro de assinatura específica (`Lmop/MultiSpec_*`), trabalho que não se justifica para benefício marginal.

### Validação empírica refuta urgência

Memória `project_ajc_validacao_full_2026-05-06.md`:

> *"72 APKs × 2 tools × 3 reps × 5min: regressão é categoria-específica (R8/Compose ~8% do dataset), AJC competitivo em legacy (OLD 36% > ASE2024 27%); dex 1.34× verifyerrors mais que ajc. **Não bloqueia release.**"*

A regressão AJC em R8/Compose já está caracterizada e aceita como categoria-específica. AJC permanece opt-in conservador; dexlib2 default cobre o gap empiricamente.

### Caminho alternativo

Reabertura como `gh55` (futuro) só se uma destas condições mudar:
1. Modernização API 30 + Fastbot 2.0 (memória `project_modernization_research_2026-05-02.md`) abrir orçamento para fechar AJC R8/Compose com mecanismo proper (oracle Kotlin/Compose + signature pattern auditado + pre-flight em ≥80% match rate)
2. Surgir VerifyError novo em DEX não coberto pelo wrapper fix INV-INS-29 (improvável dado smoke 18/18 zero)
3. Higiene operacional contra contaminação virar problema recorrente (não atual)

### Cross-references

- Análises LLM: `docs/analise_claude.md`, `docs/analise_codex.md`, `docs/analise_gemini.md`
- Verificação in loco: `DexWeaver.java:71-78` (wrappers), `docs/20260426_dexlib2_validation_results.md:310-366` (smoke 18/18)
- Memórias: `project_ajc_validacao_full_2026-05-06.md`, `project_ajc_retained_as_optin.md`, `project_modernization_research_2026-05-02.md`

---

## Why (proposta original — preservada para histórico)

Empirical validation across 72 APKs (60 OLD-CLEAN ASE2024 + 6 NEW BROKEN + 6 NEW WORKS, 851 tasks, 11h wall) revealed that both instrumentation variants produce `VerifyError` in subsets of APKs, but via **different mechanisms**:

- **AJC** fails in apps with R8-obfuscated Kotlin/Compose code (8 / 72 APKs, 100% failure rate in NEW BROKEN category): the AspectJ weaver emits advice in `<clinit>`/`<init>` of obfuscated classes, and the Frame Computer fails to derive correct stackmap types in the presence of nest-mate access patterns. Affected classes are rejected by ART verifier at load time, so the app crashes before any method runs (`cov_rv_method = 0%`).
- **DEX** (dexlib2) fails when monitor advice is invoked with a typed crypto argument (`SecureRandom`, `KeyPair`, `SecretKeySpec`, `IvParameterSpec`) but the source register at the insertion site contains a different reference type (`StringBuilder`, `String`, custom obfuscated class). Affects 12 / 72 APKs spread across OLD-CLEAN and NEW WORKS categories — independent of R8 obfuscation.

The result is a **10pp global coverage gap** (dex 42.65% vs ajc 32.67% mean `cov_rv_method`) that masks two distinct, addressable issues. Investigation has ruled out a Frame Computer regression bisect (the component already runs pre- and post-ajc; the limitation is architectural, not regression-driven) and a dexlib2 frame recompute (DEX bytecode has no JVM-style stackmap frames; ART derives types via local def-use). Three concrete, low-risk mitigations are proposed.

## What Changes

- **A.AJC** — Coverage.aj pointcut exclusions: extend `excludedPackages()` in `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj` to skip `kotlin..*`, `kotlinx..*`, `androidx.compose..*`, and class initializers (`execution(* *<clinit>(..))`). Removes the weaving sites that trigger Frame Computer failures in R8-obfuscated synthetic classes and Compose-generated lambdas.
- **A.DEX** — Register-type coercion at advice insertion site: emit `check-cast vN, <expected_crypto_type>` immediately before each `invoke` injected by dexlib2 when the source register's static type cannot be proven to match the monitor signature. Eliminates the register-alias `VerifyError` without requiring upstream changes to the rv-monitor template generator. Implemented in the dexlib2 fat CLI (`rvsec-instrumentation-dexlib2/dex-mutator/DexWeaver.java` or equivalent).
- **B1** — Pre-flight contamination check: in `Instrumenter.instrument_apks()` (the ABC contract in `rv-instrumentation-core`), validate each input APK and reject (with a clear error pointing to the artifact-detection rule) any APK whose `classes*.dex` already contains `Lmop/` or `ajc$` references. Prevents accidental double-instrumentation of previously-processed APKs (the failure mode previously documented in `feedback_verify_apk_clean_before_instrument.md`).

None of the three changes are breaking. Existing single-variant pipelines, downstream coverage parsers, and monitor specs remain unchanged. APKs that previously instrumented successfully will continue to do so; APKs that previously failed at runtime will either be salvaged (A.AJC, A.DEX) or rejected at the input gate (B1) with a deterministic error message.

## Capabilities

### New Capabilities

None. This change strengthens existing instrumentation behavior; no new capability is introduced.

### Modified Capabilities

- `instrumentation`: the Instrumentation Pipeline spec is updated to reflect (a) the additional pointcut exclusions in `Coverage.aj`, (b) the new register-coercion step in the dexlib2 weaver, and (c) the pre-flight contamination check as a new precondition on `Instrumenter.instrument_apks()`. No requirement is removed; three are added.

## Impact

All changes live in the single `PAMunb/rvsec` repository, which contains both the Java-side Maven projects (`rvsec/`, `javamop/`, `mop-maven-plugin/`) and the Python uv workspace (`rv-android/`). A single PR touches three subtrees:

- **Java side — `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj`**: 4 new exclusion clauses (`kotlin..*`, `kotlinx..*`, `androidx.compose..*`, `execution(* *<clinit>(..))`). This is a build-time-only resource — the next monitor-generation cycle picks it up automatically.
- **Java side — `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/`**: new register-coercion logic in the DEX weaver (insert `check-cast` before each injected `invoke` when the source register's static type is not provably compatible with the monitor signature). The dexlib2 fat CLI (`instr-cli.jar`) is rebuilt by Maven and auto-copied to `rv-android/modules/rv-instrumentation-dexlib2/lib/` per the existing D9 rule.
- **Python side — `rv-android/modules/rv-instrumentation-core/src/rv_instrumentation_core/`**: extend the `Instrumenter` ABC with a default `validate_input_apk()` method that both variant subclasses inherit (B1). No call-site changes in `rv-experiment` (the precondition is enforced inside `instrument_apks()`).
- **Docker image**: `phtcosta/rvandroid:0.8.0` MUST be rebuilt (no-cache) after merge so the new `Coverage.aj` resource and the new `instr-cli.jar` are baked into the image used by experiment runs.
- **Specs touched**: `openspec/specs/instrumentation/spec.md` receives three additive requirement deltas; no other domain spec is affected.
- **PRD**: relates to FR01 (monitor generation), FR02 (instrumentation variants), FR03 (coverage tracking) — no new FR is introduced.
- **Cross-module dependencies**: the change is fully contained within the instrumentation domain. Downstream Python modules (`rv-platform`, `rv-experiment`, `rv-coverage`) consume the instrumented APK as before — no API change.
- **Validation gate**: re-run `validacao_full` (72 APKs, same configuration as 2026-05-05/06 baseline) and verify the dex-ajc gap drops below 5 pp in each of the three categories (OLD-CLEAN, NEW BROKEN, NEW WORKS). Baseline numbers are recorded in `out/validacao_full_consolidated/REPORT.md`.
