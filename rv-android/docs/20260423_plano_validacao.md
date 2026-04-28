# 20260423 — Plano de validação rigorosa: pipeline `ajc` vs pipeline `dexlib2`

## Contexto

O `rv-instrumentation` atual (pipeline `dex2jar → ajc → ASM → d8`) falha em ~65% dos APKs do dataset JCA-557 (taxa de instrumentação 34.6% — 193/557) e tem regressões silenciosas em Kotlin/R8 (VerifyError ou zero coverage). O protótipo `prototipo-dexlib2` substitui esse par por weaving DEX-native via `com.android.tools.smali:smali-dexlib2`, provando em testes unitários funcionar em `cryptoapp` (7 eventos RVSEC no formato exato, zero VerifyError — ver `docs/20260423_plano_prototipo.md` §Status).

**Antes de promover dexlib2 a pipeline oficial**, precisamos de um framework de validação **alinhado com a arquitetura do rv-android** (specs, métricas, workflow) que demonstre:

1. **Equivalência comportamental** em APKs onde o pipeline atual funciona (zero regressão).
2. **Recuperação** em APKs onde o pipeline atual falha por VerifyError/Kotlin-R8 (ganho da tese).
3. **Conformidade com invariantes** formalizados em `openspec/specs/instrumentation/spec.md` e `openspec/specs/analysis/spec.md`.
4. **Byte-compatibilidade** com parsers downstream (`LogcatParser`, `CoverageTracker`, `analyze_*.py`).

Este plano **não cria infraestrutura paralela** — reusa `rv-experiment`, `rv-platform`, `CoverageTracker`, `LogcatRepository`, e os scripts existentes em `scripts/` (`analyze_comparacao.py`, `consolidate_exp*.py`, `run_phase_b.sh`, `baseline_docker.py`). A única extensão é uma **variante `dexlib2`** no módulo `rv-instrumentation`.

Segue as regras P1-P4 do `CLAUDE.md` (simplicidade, human-readable docs, no backward compat, current-state comments) e o fluxo SDD (Spec-Driven Development).

## Estado da arte de referência

- [Chen et al. 2016 — Coverage-directed differential testing (PLDI)](https://dl.acm.org/doi/10.1145/2908080.2908095) — differential testing de JVM implementations.
- [Padhye et al. 2019 — JQF/Zest](https://github.com/rohanpadhye/JQF) — coverage-guided semantic fuzzing para Java.
- [Reger & Havelund 2016 — What is a Trace? (RV)](https://www.semanticscholar.org/paper/What-Is-a-Trace-A-Runtime-Verification-Perspective-Reger-Havelund/64d16b3e97811802574489d56daa30b874cd5945) — definição canônica de trace equivalence em RV.
- [Chen & Roșu 2007 — MOP: An efficient and generic RV framework (OOPSLA)](https://dl.acm.org/doi/10.1145/1297027.1297069) — modelo subjacente ao JavaMOP.
- [Daian et al. 2015 — RV-Android (RV)](https://link.springer.com/chapter/10.1007/978-3-319-23820-3_24) — artigo original, benchmark JCA-400 herda daqui.
- [Soueidi 2024 — Engineering Instrumentation for RV (PhD, INRIA)](https://theses.hal.science/tel-04771309/file/SOUEIDI_2024_archivage.pdf) — modelo de equivalência de shadows em bytecode instrumentation.
- [Dahse & Holz 2016 — Extended Code Coverage for AspectJ-Based RV Tools (Springer)](https://link.springer.com/chapter/10.1007/978-3-319-46982-9_14) — cobertura de pointcuts como métrica empírica.

## Princípios de design (alinhados com `CLAUDE.md`)

1. **Reusar o que existe**. Não duplicar `CoverageTracker`, `LogcatParser`, scripts de análise. Extensão mínima.
2. **Adicionar variante, não framework paralelo**. `rv-instrumentation` ganha `instrumentation_variant: str` (enum `"ajc" | "dexlib2"`). Todo o resto (task model, result format, CSVs) permanece idêntico.
3. **Métricas padronizadas**. Usar `cov_act`, `cov_method`, `cov_rv_method`, `errors` de `summary.csv` e `unique_msg` de `errors.csv` (formato `class:::method:::spec:::error_type:::message`). Zero formato novo.
4. **Invariantes primeiro**. Para cada claim de equivalência, citar o invariante `INV-INS-*` / `INV-ANA-*` / `INV-PLT-*` que precisa continuar válido.
5. **Docker-paralelo**. Rodar dataset-scale com `baseline_docker.py` (N containers, isolamento garantido por spec `INV-TOOL-15`).
6. **Nunca operar emulador manualmente** — só via rv-platform (regra permanente em `CLAUDE.md`).

## Extensão no `rv-instrumentation` (pré-requisito)

**Caminho**: `rv-android/modules/rv-instrumentation/src/rv_instrumentation/config.py` + `rvandroid.py`.

Adicionar campo a `RVInstrumentationConfig`:

```python
class RVInstrumentationConfig(BaseValidatedModel):
    # ... campos existentes ...
    instrumentation_variant: Literal["ajc", "dexlib2"] = "ajc"
```

`RVInstrumentation.instrument_apks()` despacha por variante:
- `ajc`: pipeline atual (preservado, default).
- `dexlib2`: invoca o `prototipo-dexlib2` CLI (fat-jar em `modules/rv-instrumentation/lib/prototipo-dexlib2.jar` após promoção) sobre o mesmo APK + descriptor, recebe APK assinado de volta.

Propagar de `ExperimentConfig.instrumentation_variant` (novo campo) via `get_rv_instrumentation_config()` (JIT config, FR17).

Gatilho CLI:

```bash
rv-experiment run \
  --instrumentation-variant ajc \  # ou dexlib2
  --tools ape,fastbot \
  --apks-dir ./data/calibration_dataset_v2 \
  --specification-set jca \
  --repetitions 3 --timeout 300 \
  --name pipeline_ajc_baseline
```

**Invariantes a preservar**:
- INV-INS-01 (artifacts produzidos), INV-INS-05 (`Coverage.aj` presente), INV-INS-06 (hash diferente), INV-INS-10 (assinatura), INV-INS-12 (`RVSEC_HOME` obrigatório).

**Gate de extensão**: test unitário em `rv-instrumentation/tests/` com variante `dexlib2` chamando o JAR do protótipo sobre `cryptoapp.apk`, verificando os 5 invariantes acima.

## Framework de validação em 6 camadas

Cada camada tem: (a) objetivo, (b) invariantes/FRs que valida, (c) procedimento reusando infra existente, (d) métrica objetiva, (e) gate de aceitação.

### Camada 0 — Conformidade com invariantes (static)

**Objetivo**: verificar que os artefatos do pipeline `dexlib2` satisfazem os invariantes `INV-INS-*` formalizados em `openspec/specs/instrumentation/spec.md`.

**Invariantes testados**:
- `INV-INS-01`: saída contém ≥1 `.aj` e ≥1 `.java`.
- `INV-INS-05`: `Coverage.aj` presente em `monitors/`.
- `INV-INS-06`: `hash(apk_instrumented) != hash(apk_original)` (MD5 de bytes).
- `INV-INS-10`: APK instrumentado passa `apksigner verify`.
- `INV-INS-11`: binários externos (`dex2jar`, `d8`, `zipalign`, `apksigner`) são executáveis no ambiente.
- `INV-INS-04`: sem `.rvm` residuais após `rv-monitor`.

**Procedimento**: estender `modules/rv-instrumentation/tests/integration/` com `test_dexlib2_invariants.py` (pytest). Usa `cryptoapp.apk` (já disponível em `apks_examples/`).

**Métrica**: 6/6 invariantes passam.

**Gate 0**: todos os testes verdes. Bloqueante para as camadas seguintes.

---

### Camada 1 — Equivalência estática de hooks (baksmali diff)

**Objetivo**: confirmar que o conjunto de join points instrumentados pelo pipeline `dexlib2` é **compatível** (superset ou mapeável) com o do pipeline `ajc`.

**Nota sobre mapping rule**: `ajc` emite `invoke-static aspectOf() + invoke-virtual ajc$afterReturning$N$HASH(...)` enquanto `dexlib2` emite `invoke-static MonitorWrappers.X(...) ou MultiSpec_1RuntimeMonitor.XEvent(...)` direto. A equivalência é funcional, não byte-exata. A regra:

```
ajc call-site X na class C, método M, offset O emitiu advice Y
⇔ dexlib2 call-site equivalente em (C, M) invoca ≥1 monitor method
  que cobre o mesmo evento MOP (resolvido por nome da spec).
```

**Procedimento**: script `validator/static_diff.py`:

1. Para cada APK do subset de validação:
   - `baksmali disassemble APK_ajc → smali_ajc/`
   - `baksmali disassemble APK_dexlib2 → smali_dexlib2/`
2. Extrair de cada smali:
   - `H_ajc` = set de `(class, method, advice_id)` via regex sobre `ajc$...$N$HASH(`
   - `H_dexlib2` = set de `(class, method, spec_name)` via regex sobre `Lmop/MultiSpec_*RuntimeMonitor;->*Event` e `Lmop/MonitorWrappers;->*`
3. **Mapping**: resolver `advice_id` do ajc para `spec_name` via descriptor JSON (mesmo usado pelo dexlib2).
4. Calcular:
   - `recall = |H_ajc ∩ H_dexlib2| / |H_ajc|`
   - `precision = |H_ajc ∩ H_dexlib2| / |H_dexlib2|`
   - listar discrepâncias com classe/método/spec.

**Métrica**: `recall ≥ 0.95` em ≥ 90% dos APKs do subset.

**Gate 1**: recall agregado ≥ 0.95 em 30 APKs de validação (subset do JCA-400 onde o ajc funcionava).

---

### Camada 2 — Install & boot (runtime, single APK)

**Objetivo**: confirmar que APKs produzidos pelos 2 pipelines instalam e bootam sem regressão.

**Invariantes/FRs**:
- `INV-PLT-04` (timeout é sucesso), `INV-PLT-13` (Phase 3 dentro do emulator context).
- `FR07` (emulator management), `FR09` (component-based execution).

**Procedimento**: executar `rv-experiment run` com timeout mínimo (10s) e capturar `TaskResult.state` + `Task.logcat_file`:

```bash
# Pipeline A
rv-experiment run \
  --instrumentation-variant ajc \
  --tools monkey --timeout 10 --repetitions 1 \
  --apks-dir ./subset_30_apks \
  --name pipeline_ajc_install_check

# Pipeline B
rv-experiment run \
  --instrumentation-variant dexlib2 \
  --tools monkey --timeout 10 --repetitions 1 \
  --apks-dir ./subset_30_apks \
  --name pipeline_dexlib2_install_check
```

**Análise**: script `validator/compare_install_boot.py`:

```python
import json
a = json.load(open("results/pipeline_ajc_install_check/results.json"))
b = json.load(open("results/pipeline_dexlib2_install_check/results.json"))

regressions = []  # ajc ok mas dexlib2 FAILED
recoveries  = []  # ajc FAILED mas dexlib2 ok
for apk in set(a) | set(b):
    sa = a.get(apk, {}).get("repetitions", {}).get("1", {}).get("timeouts", {}).get("10", {}).get("tools", {}).get("monkey", {}).get("summary", {}).get("state")
    sb = b.get(apk, {}).get(...).get("state")
    if sa == "COMPLETED" and sb != "COMPLETED": regressions.append(apk)
    if sa != "COMPLETED" and sb == "COMPLETED": recoveries.append(apk)
```

Complementarmente, parsear logcat capturado (`task.logcat_file`) por `FATAL EXCEPTION` / `VerifyError`.

**Métricas**:
- `install_success_rate(pipeline)` (% APKs onde `pm install` aceita).
- `boot_success_rate(pipeline)` (% APKs onde `Displayed ...MainActivity` chega antes de VerifyError).
- `regressions` (esperado 0) vs `recoveries` (esperado > 0 — ganho da tese).

**Gate 2**: `regressions = 0` no subset de 30 APKs onde o pipeline `ajc` funcionava em `results/baseline_v2/`.

---

### Camada 3 — Equivalência funcional (trace equivalence)

**Objetivo**: sob os **mesmos inputs**, ambos APKs emitem o **mesmo conjunto de eventos MOP + cobertura**.

**Invariantes/FRs**:
- `INV-ANA-04` (logging em real-time), `INV-ANA-07/08` (formatos parseáveis), `INV-ANA-15` (fórmula de cobertura).
- `FR11` (logcat capture), `FR12` (coverage), `FR13` (violations).

#### 3.1 Determinismo de input

A flakiness dos monkeys é mitigada em 3 níveis (ordem crescente de rigor):

| Nível | Técnica | Determinismo | Custo | Uso |
|---|---|---|---|---|
| 3.1.a | `rv-experiment` com `monkey --seed <S>` + `--repetitions 3` | parcial (timing) | baixo | dataset-scale |
| 3.1.b | UIAutomator2 driver script em `scripts/drive_<app>.py` (taps explícitos, coords fixas) | alto | médio (1 script por app) | cryptoapp, 3 apps flagship |
| 3.1.c | `rvagent:pure_algorithm` (DFS determinístico, MOP-priorizado) | alto | zero (já existe) | apps com violações MOP conhecidas |

**Nota**: `rvagent:pure_algorithm` — quando corretamente calibrado (Fase C de `rv-agent-validation`) — é determinístico porque não usa o LLM e segue DFS WTG-guided. Reusar.

#### 3.2 Procedimento

1. Para cada APK no subset:
   - Executar pipeline ajc via `rv-experiment run --instrumentation-variant ajc ...`
   - Executar pipeline dexlib2 via `rv-experiment run --instrumentation-variant dexlib2 ...`
   - **Mesma ToolConfig, mesmo seed, mesmo timeout, mesmas repetições.**
2. Ambos produzem `summary.csv`, `coverage.csv`, `errors.csv`, `results.json`.
3. Consolidar via script novo `scripts/consolidate_pipeline_comparison.py` (modelado em `consolidate_exp3.py`):
   ```python
   # Produz um CSV unificado com coluna "pipeline" ∈ {ajc, dexlib2}
   # e linhas indexadas por (apk, rep, timeout, tool, seed)
   ```
4. Aplicar `scripts/analyze_comparacao.py` com dois "tools" sintéticos (`pipeline_ajc`, `pipeline_dexlib2`) para obter áreas 1, 3, 4, 11, 12, 16 (completion, coverage, errors, timing, determinism, validation).

#### 3.3 Métricas de equivalência

Para cada par `(apk, rep, timeout, tool)`:

**A. Cobertura (de `summary.csv`)**:
- `Δcov_method = cov_method_dexlib2 − cov_method_ajc`
- Classificar em **win/tie/loss** com tolerância `±2pp` (convenção existente em `analyze_comparacao.py`).
- **Target**: tie ≥ 80%, losses ≤ 5%, wins ≥ 15% (ganhos vêm de APKs onde ajc falha).

**B. Detecção de violações (de `errors.csv`)**:
- Extrair `E_pipeline = set(unique_msg)` para cada pipeline (formato `class:::method:::spec:::error_type:::message`).
- `precision = |E_ajc ∩ E_dexlib2| / |E_dexlib2|`
- `recall = |E_ajc ∩ E_dexlib2| / |E_ajc|`
- `F1 = 2·P·R/(P+R)`
- **Target**: F1 ≥ 0.95 por APK; agregado ≥ 0.98.

**C. Agreement Kappa de Cohen** (por APK, por spec):
- Para cada `(apk, spec)`, construir matriz 2x2 (detectada vs não detectada em cada pipeline).
- `κ ≥ 0.9` indica concordância substancial.

**D. Determinismo cruzado** (área 12 do `analyze_comparacao.py`):
- CoV (coefficient of variation) entre repetições deve ser comparável (diferença ≤ 5pp entre pipelines).

**E. Significância estatística (equivalência, não apenas diferença)**:

O teste correto aqui é **TOST pareado** (Two One-Sided Tests), porque o claim é "os pipelines são equivalentes", não "não é possível distinguir as distribuições". Mann-Whitney U testa H0="mesma distribuição" e falhar em rejeitar H0 é evidência fraca — MWU também assume amostras independentes, enquanto temos pares por APK. Usamos **Wilcoxon signed-rank TOST**:

- H0 (rejeita equivalência): |median(dexlib2_apk − ajc_apk)| > Δ
- H1 (proves equivalence): −Δ ≤ median(dexlib2_apk − ajc_apk) ≤ +Δ

**Bounds pré-registrados** (fixados antes de ver os dados):
- `cov_method`: Δ = 2pp (alinhado com a convenção win/tie/loss já usada em `analyze_comparacao.py`)
- F1 por spec: Δ = 0.02
- Kappa de Cohen por spec: Δ = 0.05

**Critérios**:
- **Equivalência**: ambos os testes unilaterais do TOST rejeitam a α=0.05.
- **Não-inferioridade** (claim mais fraco, suficiente para promoção): apenas o teste unilateral inferior rejeita a α=0.05, i.e., `p_lower < 0.05` mesmo que `p_upper ≥ 0.05`.
- **Regressão**: o teste unilateral inferior não rejeita E median(dexlib2 − ajc) < −Δ → bloqueia promoção.

Reportar sempre: diferença mediana pareada (point estimate), IC 90% bootstrapped (10k resamples), ambos p-values TOST, e effect size r (Wilcoxon). MWU pode figurar como teste suplementar não-paramétrico distribucional, mas **não** como gate primário.

#### 3.4 Oracle canônico: cryptoapp

Sabemos a priori quais violações ocorrem em `cryptoapp`. Ground truth em `results/gh50_def_val/cryptoapp.apk/cryptoapp.apk__1__300__aperv.logcat`:

| # | Spec | ErrorType | Class.method | Expected message |
|---|---|---|---|---|
| 1 | MessageDigestSpec | UnsafeAlgorithm | MessageDigestUtil.hash | `... but found MD5.` |
| 2 | MessageDigestSpec | UnsafeAlgorithm | MessageDigestUtil.hash | `... but found SHA-1.` |
| 3 | CipherSpec | InvalidSequenceOfMethodCalls | CipherUtil.des | unknown |
| 4 | CipherSpec | UnsafeAlgorithm | CipherUtil.des | `... but found DES.` |
| 5 | KeyGeneratorSpec | UnsafeAlgorithm | CipherUtil.des | `... but found DES.` |
| 6 | KeyPairGeneratorSpec | InvalidKeySize | CryptographyActivity.generateKeyPair | DSA |
| 7 | KeyPairSpec | InvalidSequenceOfMethodCalls | CryptographyActivity.generateKeyPair | unknown |
| 8 | SecretKeySpecSpec | UnsatisfiedConstraint | CipherUtil.aes | `keyMaterial.length not randomized` |
| ... | (lista completa extraída do logcat oracle) | | | |

Oracle YAML em `validator/oracles/cryptoapp-oracle.yaml` (campos ausentes = wildcard). Script `validator/check_oracle.py` confirma presença de cada linha no `errors.csv` de ambos pipelines.

**Gate 3 (funcional)**:
- Oracle cryptoapp: 100% coberto por **ambos** pipelines (com UIAutomator script 3.1.b).
- Subset 30 APKs: F1 agregado ≥ 0.98, Kappa médio ≥ 0.9, zero regressão estatisticamente significativa.

---

### Camada 4 — Validação em larga escala (dataset JCA-400)

**Objetivo**: equivalência agregada + quantificação do ganho em APKs Kotlin/R8.

**Procedimento**:
1. Usar `scripts/run_phase_b.sh` como template — ele já roda 105 APKs × 3 tools × 3 reps em Docker-paralelo via `baseline_docker.py`. Clonar pra `scripts/run_phase_validacao.sh` com 2 variantes:

```bash
# Pipeline A — ajc (baseline)
uv run python scripts/baseline_docker.py \
  --tools "ape,fastbot,rvagent:pure_algorithm" \
  --instrumentation-variant ajc \
  --data-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
  --filter-file modules/rv-agent-validation/data/all_valid_apks.txt \
  --output-dir ./results/validacao_ajc \
  --n-containers 6 --timeout 300 --repetitions 3

# Pipeline B — dexlib2
uv run python scripts/baseline_docker.py \
  --tools "ape,fastbot,rvagent:pure_algorithm" \
  --instrumentation-variant dexlib2 \
  --data-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
  --filter-file modules/rv-agent-validation/data/all_valid_apks.txt \
  --output-dir ./results/validacao_dexlib2 \
  --n-containers 6 --timeout 300 --repetitions 3
```

Wallclock ~18h cada (945 tasks). Total ~36h ou paralelo em máquina com 12 containers (~18h).

2. Consolidar: `scripts/consolidate_pipeline_comparison.py` produz CSV unificado.

3. Análise: `scripts/analyze_comparacao.py ./results/validacao_unified/ --tools pipeline_ajc,pipeline_dexlib2` produz relatório markdown com áreas 1-16.

4. Relatório específico da tese: `scripts/report_recovery_rate.py`:
   - APKs onde `pipeline_ajc` retorna `coverage.csv` vazio ou `FATAL/VerifyError` no logcat → lista R.
   - Dentre R, quantos `pipeline_dexlib2` produz coverage > 0 → recovery count.
   - Target: ≥ 90% de recovery rate (ou seja, dexlib2 resolve ≥ 90% dos APKs quebrados pelo ajc).

**Métricas Camada 4** (agregadas em 105 APKs × 3 tools × 3 reps):

| Métrica | Definição | Target |
|---|---|---|
| `instrumentation_success_rate` | % APKs onde pipeline produz APK válido | dexlib2 ≥ ajc (idealmente +15-20pp) |
| `boot_success_rate` | % APKs que bootam sem VerifyError | dexlib2 ≥ ajc |
| `coverage_median_delta` | mediana pareada de `cov_method` dexlib2 − ajc | ≥ 0 (não regride) |
| `violation_detection_F1` | F1 agregado sobre `errors.csv` | ≥ 0.95 |
| `recovery_rate` | % APKs recuperados em dexlib2 | ≥ 90% |
| `determinism_gap` | |CoV_dexlib2 − CoV_ajc| por métrica | ≤ 5pp |

**Gate 4**: todos os targets acima; não-inferioridade via Wilcoxon signed-rank TOST pareado unilateral inferior (Δ=2pp para `cov_method`, Δ=0.02 para F1, Δ=0.05 para κ, α=0.05) rejeita em ≥80% das specs. Equivalência bilateral (ambos os TOSTs rejeitam) é reportada como evidência mais forte mas não é bloqueante para promoção desde que a não-inferioridade se mantenha. Ver INV-INS-21 no spec delta `gh52-instr-dexlib2/specs/instrumentation/spec.md`.

---

### Camada 5 — Cobertura (`Coverage.aj`, RVSEC-COV)

**Objetivo**: validar que `Coverage.aj` no dexlib2 produz os mesmos `RVSEC-COV` events — depende da implementação de register spill (Fase 5 do plano do protótipo).

**Invariantes/FRs**:
- `INV-ANA-07` (dois formatos de coverage log parseáveis), `INV-ANA-15` (fórmula).
- `FR12` (method coverage tracking).

**Procedimento**:
1. Instrumentar cada APK com `Coverage.aj` em ambos pipelines.
2. Capturar `RVSEC-COV` events no logcat via `CoverageTracker` (reusa infra existente).
3. Para cada APK, extrair:
   - `M_ajc` = set de signatures em `RVSEC-COV` do pipeline ajc.
   - `M_dexlib2` = set de signatures do pipeline dexlib2.
4. Comparar:
   - `recall = |M_ajc ∩ M_dexlib2| / |M_ajc|` ≥ 0.99.
   - `coverage_pct_delta` = |`cov_method_dexlib2` − `cov_method_ajc`| ≤ 1pp (INV-ANA-15).
5. Validar thread-safety (INV-ANA-05): rodar com `rvagent:pure_algorithm` + `monkey --concurrent-threads 4` (se suportado) e garantir nenhum evento perdido (comparar total antes vs depois).

**Gate 5**: recall ≥ 0.99, coverage delta ≤ 1pp, zero threading issues.

---

### Camada 6 — Conformidade de spec (OpenSpec SDD)

**Objetivo**: antes da promoção a pipeline oficial, atualizar `openspec/specs/instrumentation/spec.md` com os novos invariantes introduzidos pela variante `dexlib2`, seguindo o workflow OpenSpec.

**Procedimento**:
1. Criar mudança OpenSpec: `openspec/changes/ghXXX-dexlib2-instrumentation/` com `proposal.md`, `design.md`, `tasks.md`, `specs/instrumentation/spec-delta.md`.
2. Delta spec adiciona:
   - `FR38`: "O sistema MUST suportar a variante `dexlib2` de instrumentação que elimina `dex2jar` e `ajc` do caminho crítico."
   - `INV-INS-26` até `INV-INS-30`: (a) wrapper methods para call sites static+after-returning, (b) name-based arg resolution, (c) register spill para Coverage, (d) compatibilidade de versão das specs com `MultiSpec_1RuntimeMonitor.java`, (e) JSON descriptor emitido pelo JavaMOP patched.
3. `/opsx:sync` promove delta para spec principal após aprovação.

**Gate 6**: OpenSpec change archived (`openspec archive ghXXX-dexlib2-instrumentation`), specs principais atualizadas, todos os testes de invariante passando.

---

## Implementação concreta (extensão mínima no codebase)

### Arquivos a criar

| Arquivo | Linhas aprox. | Propósito |
|---|---|---|
| `modules/rv-instrumentation/src/rv_instrumentation/dexlib2_variant.py` | ~100 | Adapter invocando o JAR do protótipo |
| `modules/rv-instrumentation/tests/integration/test_dexlib2_invariants.py` | ~150 | Camada 0 |
| `scripts/validator/static_diff.py` | ~200 | Camada 1 (baksmali diff) |
| `scripts/validator/compare_install_boot.py` | ~80 | Camada 2 |
| `scripts/validator/consolidate_pipeline_comparison.py` | ~150 | Camada 3/4 (reusa padrão de `consolidate_exp3.py`) |
| `scripts/validator/check_oracle.py` | ~80 | Camada 3 (oracle match) |
| `scripts/validator/report_recovery_rate.py` | ~100 | Camada 4 (tese central) |
| `scripts/validator/oracles/cryptoapp-oracle.yaml` | ~60 | Ground truth |
| `scripts/run_phase_validacao.sh` | ~50 | Shell wrapper (clone de `run_phase_b.sh`) |
| `openspec/changes/ghXXX-dexlib2-instrumentation/*.md` | ~400 | SDD deliverables |

**Total**: ~1400 linhas, ~10 dias de dev + wallclock 18-36h para dataset.

### Arquivos a modificar

| Arquivo | Mudança |
|---|---|
| `modules/rv-instrumentation/src/rv_instrumentation/config.py` | `+ instrumentation_variant: Literal[...]` |
| `modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py` | `+ dispatch por variante em instrument_apks()` |
| `modules/rv-experiment/src/rv_experiment/config.py` | `+ instrumentation_variant` propagado via `get_rv_instrumentation_config()` |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | `+ --instrumentation-variant` CLI flag |
| `scripts/baseline_docker.py` | `+ --instrumentation-variant` pass-through |

**Não modificar**: `rv-platform`, `rv-coverage`, `rv-static-analysis` (zero mudança — reusam formato existente).

## Datasets e ground truth

| Dataset | Tamanho | Propósito | Path |
|---|---|---|---|
| `cryptoapp` | 1 APK | Oracle funcional (camada 3) | `apks_examples/cryptoapp.apk` |
| `calibration_dataset_v2` | 15 APKs (10 cal + 5 holdout) | Calibração + validação small-scale (camadas 1-3) | `modules/rv-agent-validation/data/calibration_dataset_v2/` |
| `all_valid_apks.txt filter` | ~105 APKs | Large-scale baseline (camada 4) | `modules/rv-agent-validation/data/all_valid_apks.txt` |
| JCA-400 completo | ~400 APKs | Replicação ICST + quantificação do ganho | distribuído em `results/baseline_v2/instrumented_apks/` |
| JCA-557 (all original) | 557 APKs | Max recall da tese (dexlib2 resolve mais que ajc) | original set completo |

**Baselines existentes (não precisa re-rodar)**:
- `results/baseline_v2/` (3 tools × 105 APKs × 3 reps × 600s) — ground truth do pipeline ajc.
- `results/gh49_e2e/` (instrumentation gh49), `results/gh50_val/` (instrumentation gh50). Usar o mais recente que bate com a versão atual do ajc.
- ICST paper results: aggregados em `docs/` (verificar — pode ser necessário extrair do paper ou gerar).

## Critérios de aceitação globais (promover `dexlib2` a pipeline oficial)

Todos os 6 gates devem passar **numa mesma janela de execução** (mesmo commit, mesma versão de specs):

| Gate | Camada | Métrica | Target | Custo |
|---|---|---|---|---|
| 0 | Invariantes | 6 INV-INS-* testados | 6/6 green | baixo |
| 1 | Static diff | hook recall em 30 APKs | ≥ 0.95 | baixo |
| 2 | Install/boot | regressões no subset | = 0 | baixo |
| 3 | Oracle cryptoapp | eventos do oracle | 100% coberto por ambos | médio |
| 3 | Trace F1 (30 APKs) | F1 agregado | ≥ 0.98 | médio |
| 4 | Dataset JCA-400 | recovery rate | ≥ 90% | alto (36h wallclock) |
| 4 | Dataset JCA-400 | coverage median delta | ≥ 0 | alto (incluído em 4) |
| 5 | Coverage (após Fase 5) | recall RVSEC-COV | ≥ 0.99 | dep. spill |
| 6 | OpenSpec SDD | change archived | sim | baixo |

**Bloqueio duro**: falha em Gate 0, 2, ou 4 (coverage delta < 0 ou recovery < 90%) = não promover.

## Ordem recomendada de execução

1. **Extensão `rv-instrumentation` + Gate 0** (2 dias)
2. **Gate 1 (static diff) + Gate 2 (install/boot)** em subset 30 APKs (2 dias)
3. **Gate 3 (cryptoapp oracle + trace F1)** (2 dias)
4. **Fase 5 do protótipo (register spill + Coverage.aj)** — pré-requisito do Gate 5 (4-6 dias)
5. **Gate 4 (dataset JCA-400)** — Docker paralelo (1 dia de dev + 36h wallclock)
6. **Gate 5 (Coverage)** (1 dia)
7. **Gate 6 (OpenSpec SDD)** (2 dias)

**Total**: ~15-18 dias de dev + 36h de wallclock.

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Divergência entre o `.aj` canônico (`rvsec-mop/src/main/resources/jca/`) e o gerado pelo JavaMOP patched | Camada 0 valida via `INV-INS-01`; descriptor JSON bate exatamente (115 advices, 133 events — já verificado) |
| ajc usa `aspectOf()` dispatch, dexlib2 usa `MonitorWrappers` — diff de smali não é byte-exato | Camada 1 usa **mapping rule** por spec name, não byte-diff |
| `rvagent:pure_algorithm` pode não cobrir 100% das violações de cryptoapp | Complementar com UIAutomator script 3.1.b (cobre determinismo total) |
| Docker parallel pode ter contenção de I/O em 12 containers | Usar `N_CONTAINERS=6` como default (já validado em `run_phase_b.sh`) |
| Cryptoapp sem acesso ao comportamento UI esperado | Oracle YAML com campos opcionais = wildcard (ex: `expected_msg` pode ser ausente se só importar spec+errorType) |
| Coverage spill quebra DEX | POC isolada antes; baksmali diff + dexdump validation obrigatórios (já planejado em Fase 5 do protótipo) |

## Anexos / documentos relacionados

- `docs/20260421_problema_dex2jar.md` — diagnóstico do problema raiz que motiva dexlib2.
- `docs/20260422_lspatch.md` — reavaliação LSPatch → dexlib2 (apêndice A).
- `docs/20260423_javamop.md` — funcionamento do JavaMOP e decisão do hook.
- `docs/20260423_plano_prototipo.md` — plano de construção do protótipo (estado atual).
- `docs/PRD.md` — 37 FRs, 8 NFRs, 111 invariantes do rv-android.
- `openspec/specs/instrumentation/spec.md` — especificação do pipeline atual (25+ invariantes).
- `openspec/specs/analysis/spec.md` — especificação do `CoverageTracker` + `LogcatParser`.
- `openspec/specs/platform/spec.md` — especificação do `TaskExecutor` + `ResultProcessorComponent`.

## Glossário específico de validação

| Termo | Definição |
|---|---|
| **Recovery rate** | Fração de APKs onde ajc falha (VerifyError/zero coverage) mas dexlib2 produz coverage > 0 |
| **Mapping rule** | Função que traduz `ajc$afterReturning$N$HASH` (pipeline ajc) para `<spec>_<event>Event` (pipeline dexlib2) via descriptor JSON |
| **Trace equivalence** | Ambos os pipelines emitem, sob mesmo input, o mesmo conjunto de `unique_msg` em `errors.csv` modulo reordering |
| **Kappa agreement** | Coeficiente de Cohen κ medindo concordância entre pipelines na detecção de cada spec por APK |
| **Trim mean** | Média com remoção de 10% top/bottom — usada em `analyze_calibration.py` para reduzir outliers |
| **Win/tie/loss** | Classificação de APK pela diff `dexlib2 − ajc` com tolerância ±2pp (convenção do projeto) |
