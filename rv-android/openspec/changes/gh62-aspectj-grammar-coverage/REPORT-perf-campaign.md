# Relatório Final — §4.PERF (regressão de performance) + Campanha de Instrumentação JCA-190

**Change:** gh62-aspectj-grammar-coverage · **GitHub Issue:** #62
**Data:** 2026-05-31 · **Branch:** `modules` (HEAD `431767d5`)

Este relatório documenta o ciclo de correção da regressão de performance descoberta na validação (§6.S), sua validação local e em escala (campanha de 190 APKs JCA com a variante dexlib2), e uma investigação separada que isolou um defeito pré-existente da instrumentação dexlib2 em apps Jetpack Compose.

---

## 1. Contexto — a regressão §4.PERF

A instrumentação dos 190 APKs foi interrompida quando o container `gh62_06` ficou **43+ minutos** num único APK (`io.github.eucsoh.android_9.apk`, 27 MB / 5 DEX) sem terminar.

Causa-raiz (investigação multi-agente + análise estruturada — relatório em `/tmp/gh62_perf_investigation.md`): **duas fases CPU-bound sequenciais**.

- **P2 — A REGRESSÃO (introduzida no gh62, commit `3af5b3aa` §4.D):** `DexWeaver.weave` reavaliava o `commonAst` (`!within(RVMObject+) && !adviceexecution() && BaseAspect.notwithin()`) por **(instrução × 115 advices)** via `new CombinedPC(AND, commonAst, pe)`; cada chamada reconstruía uma árvore de 23 nós em `BaseAspectExpander.expand` **sem cache**. O `commonAst` depende apenas do `classDef` (é invariante por classe), então a reavaliação por instrução era puro desperdício.
- **P1 — pré-existente (gh52):** `AndroidClassIndex.load` reabria o `ZipFile` por ancestral durante a caminhada de subtipos. Roda 1×/APK antes do weave; não é a regressão, mas soma.

## 2. A correção (semântica-idêntica, perf-only)

5 commits atômicos locais (sem `Co-Authored-By`), já no `origin/modules`:

| Commit | Unidade | Mudança |
|--------|---------|---------|
| `a1c3331f` | P2.1 | Hoist do `commonAst` para **por-classe** em `DexWeaver.weave` (novos `classMatchesCommon`/`isClassInvariant`, reusam a probe de `<clinit>` `staticInitMatchesClass`); remove o `new CombinedPC(AND, commonAst, pe)` do loop principal e do pré-passe staticinit; fallback per-instruction se não-invariante; contador `commonAstEvals`. |
| `762de287` | P2.2 | Memoiza `BaseAspectExpander.expand` (`ConcurrentHashMap` keyed pelas exclusions). |
| `6bdc5b59` | P2.3 | Short-circuit em `PointcutMatcher.mergeBindings` quando um lado é vazio. |
| `9713cd25` | P1 | `AndroidClassIndex implements AutoCloseable` + cache do `ZipFile` aberto. |
| `4adf04d6` | docs | `design.md` D16 + `tasks.md` §4.PERF (documentado como defeito VALIDATION-DISCOVERED, espelhando o precedente §4.RW). |

**Build:** reator completo `mvn clean install` → BUILD SUCCESS, **640 execuções de teste, 0 fail / 0 err / 0 skip** (grammar-tests 102, MatrixIntegrityTest 18, AbsorptionClaimsContractTest 4, validator 50, pointcut-engine 67, dex-mutator 34, advice-emitter 42). Nenhum teste precisou mudar (perf-only). A matriz de gramática permaneceu intocada.

## 3. §4.PERF.VAL — validação local (eucsoh, pior caso)

`instrument` puro-JVM (sem emulador), jar corrigido md5 `3d2dff7a`, rodado **sem timeout** até completar.

| Métrica | Jar com regressão | Jar corrigido |
|---|---|---|
| Wall-clock | 43+ min, **nunca terminava** | **14:32** |
| Exit status | — | **0** |
| Woven DEX | 0 (travava no matcher) | 5/5, linear ~2 min/dex |
| APK instrumentado+assinado | ❌ | ✅ 28,9 MB + `.idsig` |
| VerifyError | — | **0** |

`weaveCounts`: advices=115, dexFiles=5, wovenDexes=5, classesSeen=43850, methodsSeen=233661, matchesApplied=454, wrappersSubstituted=450, plansSkipped=0, coverageInstrumented=80160. CPU 116% (single-thread CPU-bound, como esperado). A produção linear dos DEX (em vez do blow-up combinatório) confirma a correção.

## 4. Imagem Docker

`docker/rvandroid/build.sh` (`--no-cache`, clona `modules`@`431767d5`, `mvn clean install`):

- Imagem `phtcosta/rvandroid:0.9.0`+`latest` reconstruída → nova ID `f557da671979` (≠ stale `8f358f23`); tag inalterada.
- Verificado dentro da imagem: HEAD = `431767d5`; commits do fix (`a1c3331f`, `9713cd25`) presentes; `instr-cli.jar` presente (6,9 MB). O md5 do jar na imagem (`39dab6c9`) difere do local (`3d2dff7a`) — esperado (shade fat-jar não-determinístico entre toolchains; mesma fonte).

## 5. Campanha de instrumentação — 190 APKs JCA (variante dexlib2, do zero)

10 containers (`docker-compose.instrument-jca190-gh62.yml`), do zero (dirs de resultado limpos via container root; originais `instrument_jca190_NN` preservados).

| Métrica | Resultado |
|---|---|
| APKs instrumentados | **190 / 190** (19 × 10 containers) |
| VerifyError / rejecting (logs) | **0** |
| Erros de instrumentação | **0** (todos `instrument_errors.json` = `{}`) |
| Container preso > 40 min | **nenhum** (maior idle individual ~9 min) |
| Tempo total | ~1 h 42 (13:43 → 15:25) |

A regressão está **resolvida em escala**: pior caso individual ~9 min/APK contra o hang de 43+ min. A rodada pré-fix havia parado em 33/190; esta fechou 190/190 sem travar.

## 6. Validação install / launch / logcat (emulador API 30)

`scripts/validate_instrument_jca190.py` (sequencial, por decisão do usuário), apontado **exclusivamente** ao conjunto gh62 (`RESULTS_GLOB` corrigido para `instrument_jca190_gh62_*`; dedup removida). Emulador subido manualmente pelo usuário; o script usa o device via `adb` (sem gerência de ciclo de vida).

| Métrica | Valor |
|---|---|
| Total | 190 / 190 |
| **PASS** | **169** |
| FAIL_FATAL | 21 |
| install_ok | 189 / 190 |
| launch_ok | 189 / 190 |
| **has_verifyerror** | **0** |
| has_rvsec_cov (cobertura ativa) | 189 / 190 |
| Tempo | 1486 s (~25 min) |

### 6.1 Zero falhas induzidas pelo fix §4.PERF

Comparação do conjunto de falhas contra o baseline preservado (`install_report.PREV_original_set.csv`):

```
NEW-only (induzidas pelo gh62) : 0
comuns (mesmas falhas)         : 21
```

O conjunto de 21 falhas é **idêntico** ao baseline → o fix §4.PERF (perf-only) **não introduziu nenhuma falha de runtime**. Nenhum crash stack contém frame `RVSEC`/`br.unb`/`aspectj`.

### 6.2 Decomposição das 21 falhas

| Causa | Qtd |
|---|---|
| `IncompatibleClassChangeError` (Compose `DrawScope`) | 18 |
| `UnsatisfiedLinkError` (lib nativa ausente — `com.dobby.vpn`) | 1 |
| `IllegalStateException` (`com.dessalines.habitmaker`) | 1 |
| Falha de instalação (`com.greenart7c3.nostrsigner`) | 1 |

## 7. Investigação Compose-ICCE — defeito da instrumentação dexlib2

As 18 `IncompatibleClassChangeError` foram investigadas comparando o launch **do APK original (sem instrumentação)** vs o instrumentado (`/tmp/gh62_icce_investigate.sh`; evidência em `out/gh62_icce_investigation/`).

**Resultado: 18/18 = `DEXLIB2_INDUCED`.** Em todos os 18, o APK original instala **e** lança normalmente (sem ICCE, sem fatal); apenas a versão instrumentada crasha com `IncompatibleClassChangeError` em `androidx.compose.ui.graphics.drawscope.DrawScope` (interface esperada como classe).

**Conclusão:** a categoria Compose-ICCE é um **defeito real da instrumentação dexlib2** — o re-dexing/merge quebra a resolução interface-vs-classe no bytecode Compose/R8 otimizado. **Não é bug dos apps.** Atinge ~9,5% do dataset (18/190). É **ortogonal e separado** do fix §4.PERF (que permanece limpo). Confirma empiricamente a "categoria-específica R8/Compose" antes apenas suspeitada.

## 8. Artefatos produzidos

- `data/results/validation_gh62_keep.txt` — 169 APKs aprovados (PASS).
- `data/results/validation_gh62_drop.txt` — 21 APKs reprovados, com a causa de cada.
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260531/` — **169 APKs instrumentados e verificados** (3,1 G; confirmados instrumentados — maiores que os originais).
- `out/validate_instrument_jca190/install_report.csv` — relatório por APK (190 linhas) + `logs/` (logcats das falhas).
- `out/gh62_icce_investigation/result.csv` + `orig_logs/` — investigação Compose-ICCE.

## 9. Conclusão e pendências

O fix §4.PERF está **validado de ponta a ponta**: resolve a regressão localmente (eucsoh 14:32) e em escala (190/190, pior caso ~9 min), gera DEX válido (0 VerifyError) e **não introduz nenhuma falha de runtime**. O dataset final JCA-dexlib2 tem **169 APKs** instalável-e-verificados.

Pendências (independentes, fora do escopo deste relatório):

1. **gh62 §6.S gate(i)** — morto incompleto no APK 11/12; retomar via rv-platform (tag de violação MOP = `RVSEC`, cobertura = `RVSEC-COV`).
2. **gh62 §7 archive** — sync das delta specs + mover a change para `archive/`; limpar strays untracked.
3. **Defeito dexlib2-on-Compose (ICCE)** — candidato a nova issue GitHub, com a evidência dos 18 casos em `out/gh62_icce_investigation/`.
