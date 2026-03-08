# Analise de Diagnostico do RVSmart — Experimento gh31_mini

**Data**: 2026-03-07
**Experimento**: gh31_mini (5 APKs x rvsmart:mvp x 1 rep x 300s)
**Contexto**: Validacao do gh31-rvsmart-coverage-scoring (score breakdown, UI coverage tracker, plateau detector)
**Baseline**: cli_experiment_20260305_180341_fe33918e (gh30, mesmos APKs, 2 reps)

### Caminhos dos Resultados

- **Experimento gh31_mini**: `results/gh31_mini/`
- **Baseline gh30**: `results/cli_experiment_20260305_180341_fe33918e/`
- **Traces**:
  - `results/gh31_mini/com.blippex.app_5.apk/com.blippex.app_5.apk__1__300__rvsmart:mvp.trace`
  - `results/gh31_mini/com.crazyhitty.chdev.ks.munch_14.apk/com.crazyhitty.chdev.ks.munch_14.apk__1__300__rvsmart:mvp.trace`
  - `results/gh31_mini/com.example.root.analyticaltranslator_6.apk/com.example.root.analyticaltranslator_6.apk__1__300__rvsmart:mvp.trace`
  - `results/gh31_mini/com.gianlu.dnshero_40.apk/com.gianlu.dnshero_40.apk__1__300__rvsmart:mvp.trace` (VAZIO)
  - `results/gh31_mini/com.github.axet.hourlyreminder_476.apk/com.github.axet.hourlyreminder_476.apk__1__300__rvsmart:mvp.trace`
- **Logcats**: Mesmo padrao, extensao `.logcat`
- **Static analysis JSON**: `results/gh31_mini/<apk>/<apk>.json`
- **CSV consolidados**: `results/gh31_mini/summary.csv`, `coverage.csv`, `errors.csv`, `performance.csv`
- **Resultados JSON**: `results/gh31_mini/results.json`, `tasks.json`
- **Codigo-fonte rvsmart (Java)**: `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`
- **Plugin Python (rvsmart-tool)**: `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py`

---

## 1. Resumo Executivo

| APK | Iters | Throughput | Activities | Methods | MOP | Errors | Diagnostico |
|-----|-------|-----------|-----------|---------|-----|--------|-------------|
| blippex | 141 | 0.48 it/s | 100% (2/2) | 15.5% | 21.4% | 0 | RESTART storm (93.6%) |
| munch | 1072 | 3.65 it/s | 80% (4/5) | 28.5% | 48.0% | 4 | Ping-pong loop (60%+ das iters) |
| translator | 112 | 0.38 it/s | 50% (1/2) | 17.1% | 25.0% | 10 | 100% no-effect, stuck |
| dnshero | 0 | 0 | 20% (1/5) | 2.9% | 3.0% | 0 | **Silent hang** (0 trace lines) |
| hourly | 268 | 0.92 it/s | 50% (2/?) | 29.9% | 35.4% | 4 | OOA storm (57.8%) |

**Veredicto**: Apenas o munch teve exploracao funcional, e mesmo assim com um bug grave de ping-pong. Os outros 4 APKs demonstram falhas sistemicas no rvsmart.

---

## 2. Bugs e Anomalias Detalhadas

### BUG 1 — dnshero: Silent Hang (CRITICO)

**Sintoma**: Trace file vazio (0 bytes). O rvsmart executou por 300s sem produzir nenhuma saida stdout.

**Evidencia**:
- Task completou com status COMPLETED e execution_time=353s
- Logcat mostra 24 linhas de RVSEC-COV do `onCreate` (cobertura passiva = 2.9%)
- No baseline (gh30), o mesmo APK produziu apenas 1 linha de trace em ambas as reps
- A tela do app (LoadingActivity) tem 3 elementos interativos: EditText "Domain", Button "PREFERENCES", ImageButton (lupa de busca)

**Diagnostico**: O app requer um dominio valido para prosseguir. O rvsmart nao consegue digitar um dominio valido porque o `InputValueGenerator` gera "test" para campos genericos — "test" nao e um dominio DNS valido. Apos a primeira acao (SET_TEXT no iter 0 no baseline), provavelmente ocorre uma excecao no `runIteration()` que e capturada pelo try/catch no `run()` (AgentLoop.java:203-206) e silenciada com apenas um `Log.w`. Como o rvsmart roda via `app_process` sem acesso ao logcat do dispositivo, o warning se perde. Cada iteracao falha silenciosamente por 300s.

**Causa raiz provavel**: Excecao repetida em `UiCapture.capture()` ou `ScreenState` parsing que impede a escrita do trace. O `TraceWriter.writeLine()` nunca e chamado porque a excecao ocorre antes.

**Solucao proposta**:
1. Adicionar trace line de erro quando `runIteration()` lanca excecao (catch no `run()`)
2. Adicionar watchdog: se 30s se passarem sem trace output, logar diagnostico
3. Melhorar `InputValueGenerator` com dominio valido para campos com hint "domain"/"url"

---

### BUG 2 — blippex: RESTART Storm (SEVERO)

**Sintoma**: 132/141 iteracoes (93.6%) sao RESTART. 104 RESTARTs consecutivos sem efeito.

**Cronologia detalhada**:
```
iter 0-3:   MainActivity — 3x SET_TEXT + 1x CLICK (sem efeito, retries=3)
iter 4:     LONG_CLICK abre Chrome (OOA) — saiu do app!
iter 5:     Chrome FirstRun — SET_TEXT no EditText
iter 6-8:   [MISSING — gap de 3 iters] — provavelmente system dialogs descartados
iter 9:     OOA recovery (tolerance_exceeded) — Chrome detectado
iter 10-35: SplashActivity — 26x RESTART consecutivos (sem efeito)
iter 36:    RESTART finalmente transiciona para MainActivity (1 iter util!)
iter 37:    BACK na MainActivity — volta a SplashActivity? Nao, muda hash
iter 38:    CLICK abre Launcher (saiu do app de novo!)
iter 39:    SET_TEXT em Calendar (app errado!)
iter 40:    OOA recovery (launcher_fastpath)
iter 41-143: SplashActivity — 104x RESTART consecutivos ate timeout
```

**Diagnostico**:
1. **SplashActivity sem elementos interativos**: O UI dump da SplashActivity nao tem nenhum widget clickable. O rvsmart so pode fazer RESTART.
2. **RESTART nao espera a auto-transicao**: Muitos apps fazem `SplashActivity -> MainActivity` apos 2-3s via handler/timer. O rvsmart faz RESTART imediato (~2s exec) que relanca o app e volta ao SplashActivity, criando um loop infinito.
3. **StuckDetector nao esta ativo**: Apesar de 104 iteracoes iguais, o detector de stuck nao dispara ou sua acao de recovery tambem e RESTART.
4. **Navegacao para fora do app**: A acao LONG_CLICK no iter 4 abriu Chrome, e o CLICK no iter 38 abriu o Launcher. O rvsmart nao filtra acoes que podem sair do app.

**Dados de score**:
- Score total medio = **-500** nas 129 iters de SplashActivity (score fixo de -500 para RESTART)
- 94.2% dos scores sao negativos
- Saturation = 1.0 (100%) a partir do iter 10 — ironicamente "saturado" porque so tem 1 tela

**Solucao proposta**:
1. Detectar telas sem elementos interativos e fazer `Thread.sleep(2000)` antes do proximo capture (esperar auto-transicao)
2. Limitar RESTARTs consecutivos no mesmo hash (ex: max 5 RESTARTs no mesmo hash → force BACK/wait)
3. Filtrar LONG_CLICK em elementos que podem abrir apps externos (URLs, EditText com hint "search")

---

### BUG 3 — analyticaltranslator: 100% No-Effect (SEVERO)

**Sintoma**: Todas as 112 iteracoes tiveram `action_had_effect=false`. Apenas 1 screen hash durante toda a execucao.

**Cronologia**:
```
iter 0-2:   [MISSING — gap, provavelmente startup]
iter 3-114: MainActivity hash=a658526f — 112 iters, 0% efeito
            96x RESTART, 9x SET_TEXT, 7x CLICK
```

**Analise de coordenadas** (16 acoes com coordenadas):
- `(491,843)`: 5x no TextView — campo de saida (nao interativo)
- `(491,333)`: 4x no EditText — campo de entrada
- `(491,578)`: 4x no TextView — outro campo de saida
- `(183,1039)`: 2x no Button — botao de traducao
- `(183,993)`: 1x no Button

**Diagnostico**:
1. **SET_TEXT e CLICK nao mudam o hash**: O app provavelmente responde as acoes (o texto muda no EditText, o botao de traducao processa), mas o **hash do ScreenState permanece identico** porque o algoritmo de hashing nao captura o conteudo dos campos de texto.
2. **Efeito real vs efeito detectado**: A deteccao de efeito compara hashes antes/depois. Se o unico efeito e texto aparecendo num TextView de output, o hash baseado em estrutura (classe + resource-id + bounds) nao muda.
3. **96/112 = RESTART**: Como nenhuma acao tem efeito, o StuckDetector (ou a logica de fallback) forca RESTARTs que relancam o app no mesmo estado.
4. **Exec time alto** (avg 1733ms, max 2648ms): Cada RESTART demora ~2s, dominando o tempo total.

**Score breakdown**: coverage=100 (unico estado, 100% coberto) mas total=-308 em media (penalizacao por RESTARTs).

**Solucao proposta**:
1. Incluir texto/content-desc no hash para detectar mudancas de conteudo como efeito
2. Ou: considerar que SET_TEXT em EditText sempre tem efeito (o conteudo muda)
3. Adicionar heuristica: se CLICK em Button e seguido de mudanca de texto em algum campo, considerar efeito

---

### BUG 4 — munch: Ping-Pong Loop (MODERADO)

**Sintoma**: A partir do iter ~150, o rvsmart entra em loop perpetuo entre 2 hashes: `e541a335` ↔ `d8ff8577`, alternando CLICK (tier 4) e BACK (tier 3).

**Evidencia**: Dos 1072 iteracoes totais:
- Hash `e541a335`: 316 visitas (29.5%)
- Hash `d8ff8577`: 312 visitas (29.1%)
- **58.6% das iteracoes gastas em apenas 2 telas**

O padrao e perfeitamente regular:
```
iter N:   e541a335 → d8ff8577 via BACK  (tier 3 = Backtrack)
iter N+1: d8ff8577 → e541a335 via CLICK (tier 4 = Unified)
iter N+2: e541a335 → d8ff8577 via BACK  (tier 3 = Backtrack)
...repete por centenas de iteracoes
```

**Diagnostico**:
1. **Backtrack sempre volta para o mesmo estado**: O tier 3 (proactive backtrack) faz BACK que leva a `d8ff8577`. O tier 4 faz CLICK que leva a `e541a335`. Nenhum deles tenta um caminho diferente.
2. **PlateauDetector nao dispara**: Embora nao haja novos estados, `action_had_effect=true` em todas as iteracoes (o hash muda), entao o detector nao conta como "sem progresso".
3. **RewardScorer domina**: reward avg=14119 no munch. Este valor alto mascara a falta de exploracao real — o scorer recompensa acoes com efeito, mesmo que sejam BACK/CLICK ping-pong.
4. **Desperdicio massivo**: ~600 iteracoes gastas em ping-pong = ~165s desperdicados (56% do tempo).

**Impacto**: Apesar do bug, o munch ainda teve a melhor cobertura (80% activities, 48% MOP) — a exploracao inicial (iter 0-150) foi eficaz antes de degenerar.

**Solucao proposta**:
1. Detectar ciclos de 2 estados (A→B→A→B) e forcar exploracao de caminho diferente apos N repeticoes (ex: 10)
2. Penalizar transicoes para estados ja visitados muitas vezes no scorer
3. Contar ciclo A↔B como "sem progresso" no PlateauDetector

---

### BUG 5 — hourlyreminder: OOA Storm por SoundPicker (SEVERO)

**Sintoma**: 155 de 268 iteracoes (57.8%) sao OOA com `fg_pkg=com.google.android.soundpicker`.

**Cronologia**:
```
iter 0-112:  MainActivity — exploracao excelente (91 transicoes, 38 unique hashes)
iter 113:    CLICK na GalleryActivity abre o SoundPicker do sistema
iter 117:    OOA detection (tolerance_exceeded) — RESTART
iter 117-579: 155x RESTART OOA consecutivos (soundpicker nunca fecha)
             Cada RESTART tenta relancr o app mas o soundpicker permanece no foreground
```

**Diagnostico**:
1. **SoundPicker e modal**: O `com.google.android.soundpicker` e um componente do sistema que fica como Activity separada no foreground. `forceStop` do app alvo nao fecha o soundpicker.
2. **Recovery loop**: A cada iteracao: detect OOA → RESTART → soundpicker ainda no foreground → detect OOA → repeat
3. **`handleOoaRestart()` so faz `forceStop + startApp`**: Nao faz `forceStop` do pacote no foreground, apenas do app alvo
4. **156 gaps de iteracao**: Os gaps (117→120, 120→123, etc.) indicam que entre cada OOA detection ha 2-3 iteracoes de "tolerancia" que sao contadas mas nao produzem trace (o `outOfAppCounter` incrementa ate atingir o threshold)

**fg_pkg**: 100% `com.google.android.soundpicker` — um unico evento cascateou 155 iteracoes perdidas.

**A exploracao antes do OOA era excelente**:
- 38 unique hashes, 91 transicoes, 81% effect rate
- 9 widget types diferentes com boa distribuicao
- Score tiers: 100% tier 2 (Scored) — melhor tier para exploracao
- Saturation = 0.0 (ainda explorando quando parou)

**Solucao proposta**:
1. No `handleOoaRestart()`, fazer `forceStop` do foreground package ANTES de restartar o app alvo
2. Adicionar `consecutiveOoaAfterRestart` counter: apos 3 OOAs consecutivos apos RESTART, fazer `am force-stop <fg_pkg>` + dismiss
3. Alternativa: usar `adb shell input keyevent BACK` antes do RESTART para fechar dialogs modais

---

### BUG 6 — Saturation Rate = 0.0 com 38 Unique States (MODERADO)

**Sintoma**: hourlyreminder tem `saturation_rate=0.0` durante toda a execucao, apesar de ter 38 unique states.

**Diagnostico**: O `saturation_rate` no `UICoverageTracker` (gh31) mede cobertura de UI (elementos interagidos / elementos disponiveis por tela), nao descoberta de estados. E um campo **diferente** de `unique_states` (que conta hashes distintos no grafo).

Se o tracker nunca recebe `registerScreenElements()` ou `recordInteraction()`, o gap fica em 0. No hourlyreminder, 155 das 268 iteracoes sao OOA (sem captura de UI), entao o tracker pode nao estar recebendo dados suficientes. Tambem: se as 113 iteracoes "normais" usam tier 2 (Scored) que chama `selectBestScored()` sem passar pelo tracker path, o tracker pode nao ser atualizado.

**Verificacao necessaria**: Confirmar no AgentLoop se `uiCoverageTracker.registerScreenElements()` e chamado em toda iteracao com captura de UI, nao apenas em certas branches.

---

## 3. Score Breakdown — Analise Estatistica

### 3.1 Per-Scorer Statistics

| Scorer | blippex | munch | translator | hourly |
|--------|---------|-------|------------|--------|
| **mop** | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) |
| **wtg** | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) |
| **coverage** | avg=99.5 | avg=69.7 | avg=100 | avg=94.2 |
| **decay** | avg=13.9 (90.6% zero) | avg=18.7 | avg=25.9 (82.1% zero) | avg=197.6 |
| **confirmed** | avg=10.3 | avg=6.3 | avg=6.6 | avg=45.8 (34.5% zero) |
| **reward** | avg=12778 (stddev=7213) | avg=14119 | avg=2671 | avg=956 |
| **component** | avg=9.4 (94.2% zero) | avg=99.9 | avg=23.2 (83.9% zero) | avg=101.5 |
| **system** | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) | 0 (100% zero) |
| **total** | avg=-373 | avg=14303 | avg=-308 | avg=1388 |

### 3.2 Scorers Sistematicamente Inativos

- **mop = 0 em 100% das iteracoes** em todos os APKs: O MopScorer nao contribui. Causa provavel: nao ha dados de MOP score no `StaticMap` ou os metodos MOP nao sao diretamente alcancaveis pelas telas exploradas.
- **wtg = 0 em 100%**: O WtgScorer nao contribui. Causa provavel: sem dados de transicao WTG no `StaticMap` ou as transicoes estaticas nao correspondem as telas observadas.
- **system = 0 em 100%**: O SystemScorer nao contribui.

**Impacto**: 3 de 10 scorers nunca contribuem. O score total e dominado pelo **reward** (RewardScorer) que acumula valor ao longo do tempo — o que explica scores totais de 14K+ no munch.

### 3.3 Scores Negativos

| APK | Negativos | % | Causa |
|-----|-----------|---|-------|
| blippex | 131/139 | 94.2% | RESTART na SplashActivity = score fixo -500 |
| translator | 94/112 | 83.9% | RESTART na MainActivity = score fixo -500 |
| munch | 0/1070 | 0% | Exploracao saudavel |
| hourly | 1/113 | 0.9% | 1 RESTART isolado |

Score = -500 e o valor fixo para acoes de RESTART via Unified queue (tier 4). Nos apps com RESTART storm, isso domina.

---

## 4. Distribuicao de Acoes por Tipo e Componente

### 4.1 Tipos de Acao

| Tipo | blippex | munch | translator | hourly | Total |
|------|---------|-------|------------|--------|-------|
| CLICK | 1.4% | **54.4%** | 6.2% | 36.2% | 43.1% |
| BACK | 0.7% | **41.6%** | 0% | 0% | 28.0% |
| RESTART | **93.6%** | 0.4% | **85.7%** | **58.2%** | 24.3% |
| SET_TEXT | 3.5% | 1.2% | 8.0% | 3.7% | 2.3% |
| LONG_CLICK | 0.7% | 1.6% | 0% | 1.1% | 1.5% |
| SCROLL | 0% | 0.8% | 0% | 0.7% | 0.8% |

**Observacao critica**: RESTART deveria ser <5% em exploracao saudavel. 3 de 4 APKs tem >50% RESTART.

### 4.2 Widgets Interagidos

**munch** (1072 iters, mais diverso):
- `ImageView`: 476 (44.4%) — domina por ser a lista de noticias
- `LinearLayout`: 38, `TextView`: 26, `ImageButton`: 24, `Spinner`: 24
- `EditText`: 16, `Button`: 3
- **9 widget types** distintos

**hourly** (113 iters dentro do app):
- `ActionBar$Tab`: 26 (23%) — tabs de navegacao
- `ImageButton`: 24 (21%) — botoes de acao
- `FrameLayout`: 19 (17%) — containers
- `EditText`: 15 (13%) — campos de entrada
- `CheckBox`: 10 (9%) — configuracoes
- **9 widget types** distintos — boa diversidade

**Effect rate por widget** (hourly):
- `ActionBar$Tab`: **100%** — tabs sempre mudam o estado
- `ImageButton`: **100%** — botoes sempre tem efeito
- `FrameLayout`: **89%** — containers geralmente respondem
- `Button`: **88%**
- `CheckBox`: **40%** — toggle nem sempre muda hash
- `EditText`: **13%** — SET_TEXT raramente muda hash (ver BUG 3)

---

## 5. Cobertura de UI por Tela

### 5.1 Per-Screen Hash Analysis

**blippex** (7 hashes):
| Hash | Activity | Iters | Effect % | Avg Score |
|------|----------|-------|----------|-----------|
| `99f6ffb3` | SplashActivity | 129 | 0% | -500 |
| `4500117f` | MainActivity | 5 | 20% | 1282 |
| Outros (5) | Chrome, Calendar, Launcher | 5 | 80% | 1056 |

129 de 141 iteracoes gastas em **1 unica tela sem elementos interativos**.

**munch** (28 hashes reportados, top 5):
| Hash | Iters | Effect % | Avg Score |
|------|-------|----------|-----------|
| `d8ff8577` | 312 | 97% | 14426 |
| `e541a335` | 316 | 97% | 14180 |
| `cc578fe4` | 133 | 97% | 14067 |
| `85d79c7e` | 101 | 97% | 14177 |
| `4b0fc954` | 71 | 97% | 14187 |

2 hashes concentram **58.6%** das iteracoes (ping-pong loop).

**hourly** (39 hashes, muito diverso):
- Top hash: `7acabae9` com 13 iters (11.5%)
- Distribuicao mais uniforme — sem concentracao excessiva
- 22 hashes visitados apenas 1 vez — exploracao ampla mas rasa

### 5.2 Coordenadas de Acao

**blippex**: Apenas 3 coordenadas unicas, com `(562,168)` repetida 6x (sempre no EditText).

**translator**: 5 coordenadas unicas. Concentradas no centro vertical da tela. Clicks repetidos nas mesmas posicoes sem resultado.

**hourly**: Nao analisado (dados de coord nao disponiveis para OOA iters).

---

## 6. Plateau e Stochastic

### 6.1 Exploration Plateaus (unique_states sem mudanca >=10 iters)

| APK | Plateau | Duracaoiters) | Unique States |
|-----|---------|---------------|---------------|
| blippex | iter 10-36 | 27 | 3 |
| blippex | iter 39-143 | 105 | 5 |
| munch | iter 150-1072 | **~900** | 28 |
| translator | iter 3-114 | **112** (toda a execucao) | 1 |
| hourly | iter 117-579 | **155** | 38 |

**Munch**: Embora "nao esteja em plateau" (action_had_effect=true pelo ping-pong), o `unique_states` nao cresce apos iter ~130. O PlateauDetector nao detecta isso porque "efeito" nao significa "progresso".

### 6.2 Stochastic Selection

| APK | Stochastic % | Effect (stoch) | Effect (determ) |
|-----|-------------|----------------|-----------------|
| blippex | 0.7% (1/139) | 0% | 4.3% |
| munch | 42.6% (456/1070) | ? | ? |
| translator | 2.7% (3/112) | 0% | 0% |
| hourly | 17.7% (20/113) | 80% | 79.6% |

**Munch tem 42.6% stochastic** — quase metade das acoes sao aleatorias. Isso deveria introduzir diversidade, mas o ping-pong loop persiste porque ambos estados tem scores altos e o stochastic nao e diferente o bastante.

**Hourly**: Stochastic e deterministic tem effect rate quase igual (80% vs 79.6%) — o stochastic nao adiciona nem tira valor.

---

## 7. Timing

| APK | Capture avg | Scoring avg | Exec avg | Total avg | Outliers (>3s) |
|-----|-----------|------------|---------|----------|---------------|
| blippex | 0ms | 55ms | 1642ms | 2044ms | 3 |
| munch | 0ms | 19ms | 24ms | 271ms | 0 |
| translator | 0ms | 70ms | 1733ms | 2607ms | 16 |
| hourly | 0ms | 70ms | 65ms | 363ms | 3 |

- **Capture** e instantaneo em todos (~0ms) — UI dump via app_process e muito rapido
- **Exec** domina nos apps com RESTART (1.6-1.7s por RESTART)
- **Munch** tem o melhor throughput: 271ms/iter = 3.65 it/s
- **Translator** tem 16 outliers >3s (max 5813ms) — provavel que o app demora a reiniciar

---

## 8. Comparacao com Baseline (gh30)

| APK | Metrica | Baseline (rep1) | gh31_mini | Delta |
|-----|---------|-----------------|-----------|-------|
| blippex | iterations | 141 | 141 | +0 |
| | unique hashes | 8 | 8 | +0 |
| | effective actions | 6 | 6 | +0 |
| | OOA events | 2 | 2 | +0 |
| munch | iterations | 1067 | 1072 | +5 |
| | unique hashes | 30 | 30 | +0 |
| | effective actions | 1036 | 1039 | +3 |
| | OOA events | 2 | 2 | +0 |
| translator | iterations | 106 | 112 | +6 |
| | unique hashes | 1 | 1 | +0 |
| | effective actions | 0 | 0 | +0 |
| dnshero | iterations | 1 | 0 | -1 |
| hourly | iterations | 272 | 268 | -4 |
| | unique hashes | 42 | 40 | -2 |
| | effective actions | 93 | 90 | -3 |
| | OOA events | 160 | 155 | -5 |

**Conclusao**: gh31 (score breakdown) **nao alterou o comportamento** do rvsmart. Os resultados sao estatisticamente identicos ao baseline. Todos os bugs identificados sao **pre-existentes** do gh30.

---

## 9. Diagnostico Consolidado e Priorizacao

### Bugs por Prioridade

| # | Bug | Severidade | APKs Afetados | Impacto | Esforco |
|---|-----|-----------|---------------|---------|---------|
| 1 | Silent hang (0 trace output) | CRITICO | dnshero | 100% tempo perdido | Baixo |
| 2 | OOA storm (fg_pkg nao fechado) | SEVERO | hourly | 57.8% tempo perdido | Medio |
| 3 | RESTART storm (tela sem elementos) | SEVERO | blippex, translator | 85-93% tempo perdido | Medio |
| 4 | Ping-pong loop (2-state cycle) | MODERADO | munch | 56% tempo desperdicado | Medio |
| 5 | Effect detection (hash nao capta texto) | MODERADO | translator | 100% no-effect falso | Alto |
| 6 | Scorers inativos (mop=0, wtg=0) | BAIXO | todos | Score incompleto | Alto |
| 7 | Saturation inconsistente | BAIXO | hourly | Metrica incorreta | Baixo |

### Solucoes Propostas (Resumo)

1. **Silent hang**: Trace line de erro no catch do `run()` + watchdog timer
2. **OOA storm**: `am force-stop <fg_pkg>` + `input keyevent BACK` antes de RESTART
3. **RESTART storm**: `Thread.sleep(2000)` em telas sem elementos + limite de RESTARTs por hash
4. **Ping-pong**: Detector de ciclo de 2 estados → forcar acao diferente apos N repeticoes
5. **Effect detection**: Incluir texto/content-desc no hash ou heuristica SET_TEXT=efeito
6. **Scorers inativos**: Investigar se StaticMap recebe dados, verificar formato WTG/MOP
7. **Saturation**: Verificar chamada de `registerScreenElements()` em toda iteracao UI

---

## 10. Retries e Iteration Gaps

### Retries

| APK | Iters com retry | Total retries | Max | Tipos |
|-----|----------------|---------------|-----|-------|
| blippex | 5 | 14 | 3 | SET_TEXT:3, CLICK:1, LONG_CLICK:1 |
| munch | 148 | ? | 3 | CLICK dominante |
| translator | 16 | 45 | 3 | SET_TEXT:9, CLICK:5, RESTART:2 |
| hourly | 51 | 110 | 3 | CLICK:38, SET_TEXT:10, LONG_CLICK:3 |

O max de retries e sempre 3 (configuravel). **Translator** tem retry em SET_TEXT — indica que a digitacao falha repetidamente.

### Iteration Gaps

| APK | Gaps | Exemplos |
|-----|------|----------|
| blippex | 1 | iter 5→9 (3 missing — provavelmente system dialogs) |
| munch | 1 | iter 52→54 (1 missing) |
| translator | 0 | Continuo (iter 3-114) |
| hourly | **156** | Maioria sao gaps de 2 (tolerancia OOA: 2 iters sem trace antes de recovery) |

Os 156 gaps do hourly confirmam que o `outOfAppTolerance` consome iteracoes sem trace output.

---

## 11. Conclusoes

### O que funciona bem no gh31:
- **Score breakdown** aparece corretamente em 4 de 5 APKs
- **Timing granular** (capture/scoring/exec/total) capturado em todas as traces
- **Stochastic flag** rastreado corretamente
- **Score tiers** reportados consistentemente
- **Nenhuma regressao** vs baseline — comportamento identico

### O que precisa ser corrigido (bugs pre-existentes do rvsmart):
1. Recovery de OOA precisa fechar o app no foreground (nao apenas restartar o target)
2. Telas sem elementos interativos precisam de estrategia de espera (nao RESTART imediato)
3. Deteccao de efeito precisa considerar mudancas de texto, nao apenas mudanca de hash
4. Ciclos de 2 estados precisam ser detectados e quebrados
5. Excecoes no loop precisam gerar trace output (nao silenciar)

---
---

# PARTE II — Analise Profunda (Code Review)

**Data**: 2026-03-07 (complemento a Parte I)
**Metodo**: Leitura linha a linha de todo o codigo-fonte Java do rvsmart, cruzamento com JSONs reais de static analysis e traces do experimento, raciocinio estruturado (sequential thinking).

---

## 12. Modelo Mental do Algoritmo — Como o RVSmart Realmente Funciona

O core do RVSmart e DFS sobre um grafo de estados de UI:

```
loop ate timeout (INV-RSM-01):
  1. Captura tela → ScreenState → hash estrutural (className|resourceId|interactMask)
  2. Tier 1: Se PathBuffer ativo, segue caminho planejado (BACK)
  3. Tier 2: Se ha acoes NAO testadas nesta tela, executa a melhor scored (DFS: explorar)
  4. Tier 3: Se tela saturada (>= 80% acoes testadas 4+ vezes), BACK (DFS: backtrack)
  5. Tier 4: Fila unificada com todos os widgets + BACK(-100) + RESTART(-500), score-ranked
  6. Executa acao → throttle → recaptura → detecta efeito → retry se sem efeito (max 3x)
  7. Learner: reward + graph transitions → trace output
```

O sistema de 4 tiers E DFS:
- **Tier 2** = explorar novos (DFS forward)
- **Tier 3** = backtrack quando esgotado (DFS backtrack)
- **Tier 1** = backtrack planejado via BFS (stuck recovery)
- **Tier 4** = fallback scored (quando tiers 1-3 nao se aplicam)

O problema NAO esta na estrutura de tiers. Esta no **scoring dentro dos tiers** e nos **mecanismos de recuperacao**.

### 12.1 Cadeia de Scoring — Estado Real

O ActionSelector usa ate 8 scorers aditivos. Analise individual de cada um:

| # | Scorer | Status | Contribuicao Real | Evidencia |
|---|--------|--------|-------------------|-----------|
| 1 | **MopScorer** | **QUEBRADO** | 0 em 100% das iters, todos os APKs | Parser JSON incompativel (ver Bug A) |
| 2 | **WtgScorer** | **QUEBRADO** | 0 em 100% das iters, todos os APKs | Parser JSON incompativel (ver Bug A) |
| 3 | **RewardScorer** | **PREJUDICIAL** | 14000+ no munch, domina 96.8% do total | Acumulacao infinita (ver Bug B) |
| 4 | **CoverageDensityScorer** | **CODIGO MORTO** | Nunca contribui | `getCoverageGap()` nunca chamado |
| 5 | GradualDecayScorer | OK | 200→0 ao longo de 5 visitas | Penaliza revisitas, essencial para DFS |
| 6 | SystemElementFilter | OK | -5000 para system UI | Guard simples |
| 7 | ComponentPriorityScorer | OK | SET_TEXT=200, CLICK=100, SCROLL=25 | Prioriza acoes de alto valor |
| 8 | ConfirmedCoverageScorer | OK | 150/(1+revisitas) | Booste telas com MOP confirmado |

**50% dos scorers estao quebrados, mortos ou prejudiciais.** O agente opera efetivamente com 4 scorers.

### 12.2 Exemplo Real: Rastreamento de uma Iteracao (munch iter 3)

```json
{"iteration":3, "hash":"cc578fe4", "activity":"uiactivitiesHomeActivity",
 "action_type":"CLICK", "widget_class":"ImageButton", "score_tier":2,
 "scores":{"mop":0,"wtg":0,"decay":200,"system":0,"component":100,
           "confirmed":150,"reward":4203,"coverage":100,"total":4753}}
```

Decomposicao do score total = 4753:
- **reward: 4203 = 88.4% do total** ← domina tudo
- confirmed: 150 = 3.2%
- decay: 200 = 4.2%
- component: 100 = 2.1%
- coverage: 100 = 2.1%
- mop: 0 (QUEBRADO)
- wtg: 0 (QUEBRADO)
- system: 0

Apos ~150 iteracoes no munch, o reward chega a ~14000. Nesse ponto, a decisao do agente e determinada quase exclusivamente pelo reward acumulado. Os outros scorers sao irrelevantes.

---

## 13. Bugs — Causas-Raiz Verificadas no Codigo

### Bug A — StaticMap Parser: Formato JSON Incompativel (CRITICO)

**Arquivos**: `StaticMap.java:58-98`, JSON real em `results/gh31_mini/com.crazyhitty.chdev.ks.munch_14.apk/*.json`

**Codigo do parser** (`StaticMap.java:58-70`):
```java
private void parseReachability(JsonObject json) {
    JsonObject reach = json.getAsJsonObject("reachability");  // ← ESPERA JsonObject
    if (reach == null) return;  // ← SEMPRE null porque reachability e um ARRAY
    JsonObject directObj = reach.getAsJsonObject("directly_reaches_mop");
    // ... nunca executado
}
```

**JSON real produzido por RvsecAnalysisClient** (gh27):
```json
{
  "reachability": [                          // ← JSON ARRAY, nao Object!
    {
      "className": "com.nineoldandroids.util.ReflectiveProperty",
      "methods": [
        {
          "signature": "<com.nineoldandroids.util.ReflectiveProperty: void <init>(...)>",
          "reachable": false,
          "reachesMop": false,
          "directlyReachesMop": false         // ← campo no metodo, nao no topo
        }
      ]
    }
  ]
}
```

`getAsJsonObject("reachability")` retorna **null** quando o valor e um JSON array (comportamento do Gson). Portanto `directlyReachesMop` e `reachesMop` nunca sao populados. O `isLoaded` fica `true` (nenhuma excecao), mas os maps estao null.

**Mesmo problema para transitions** (`StaticMap.java:81-98`):

```java
private void parseTransitions(JsonObject json) {
    JsonObject transObj = json.getAsJsonObject("transitions");  // ESPERA Object
    // ...
}
```

JSON real:
```json
{
  "transitions": [                           // ← JSON ARRAY novamente!
    {
      "sourceId": 1082,
      "targetId": 1082,
      "events": [{"type": "implicit_power_event", "widgetClass": "...SplashActivity"}]
    }
  ]
}
```

O parser espera `Map<String, List<String>>`, o JSON tem `List<{sourceId, targetId, events}>`.

**Segundo problema — Formato dos nomes de atividade**:

Nomes no trace: `"uiactivitiesSplashActivity"` (pontos removidos do caminho relativo ao pacote `ui.activities.SplashActivity`).

Nomes no JSON: `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"` (fully qualified).

`qualifiedPrefix()` (`StaticMap.java:162-163`) geraria:
```
codePackage + "." + activityName + "."
= "com.crazyhitty.chdev.ks.munch" + "." + "uiactivitiesSplashActivity" + "."
= "com.crazyhitty.chdev.ks.munch.uiactivitiesSplashActivity."
```

Isso NAO faz match com a chave no JSON:
```
"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"
```

**Consequencia**: DUPLA falha — (1) parser nao le os dados, (2) mesmo se lesse, o matching de nomes falharia. MOP e WTG scoring nunca funcionaram desde gh29.

**Impacto**: Toda a logica de guiagem por analise estatica (o proposito central do design do rvsmart) e uma letra morta. O agente explora cegamente.

---

### Bug B — RewardPropagator: Acumulacao Infinita (CRITICO)

**Arquivos**: `RewardPropagator.java:65-84`, `RewardScorer.java:30-34`, `Config.java:60`

**Mecanismo de acumulacao** (`RewardPropagator.java:65-84`):
```java
public void propagate() {
    // Para cada posicao i na janela, calcula retorno descontado G
    for (int i = 0; i < len; i++) {
        double G = 0.0;
        double discount = 1.0;
        for (int j = i; j < len; j++) {
            G += discount * rewardArr[j];
            discount *= GAMMA;  // 0.8
        }
        accumulatedRewards.put(hash, current + G);  // ← SOMA ao existente, nunca subtrai
    }
}
```

`propagate()` e chamado em TODA iteracao (`AgentLoop.java:489`). A cada chamada, adiciona ao `accumulatedRewards` sem teto nem decaimento. Com janela N=5 e gamma=0.8:

- Iteracao 100: hash X acumulou ~1000 de reward
- Iteracao 500: hash X acumulou ~5000 de reward
- Iteracao 1000: hash X acumulou ~14000 de reward

**`propagateConfirmedCoverage()`** (`RewardPropagator.java:96-123`) agrava o problema:
```java
double boost = CONFIRMED_COVERAGE_BOOST * methods.size();  // 10.0 * N metodos
// Distribui para TODA a trajetoria com desconto
for (int i = hashes.length - 1; i >= 0; i--) {
    accumulatedRewards.put(h, current + boost * discount);
    discount *= GAMMA;
}
// E TAMBEM booste o hash confirmado diretamente
accumulatedRewards.put(hash, confirmed + boost);  // ← double-count!
```

Uma unica deteccao de cobertura com 5 metodos adiciona `50.0 * (1 + 0.8 + 0.64 + 0.512 + 0.41) + 50.0 = 216.6` de reward distribuido. Se isso acontece 10 vezes nas primeiras 50 iteracoes, o hash acumula ~2000 de reward antes de o agente ter explorado metade do app.

**`maxCumulativeFactor`** (`Config.java:60`): `DEFAULT_MAX_CUMULATIVE_FACTOR = 3.0` esta definido mas **nenhum codigo lhe faz referencia**. A variavel e lida por `getMaxCumulativeFactor()` mas nenhum caller existe.

**`RewardPropagator.reset()`** (`RewardPropagator.java:136-140`): Existe mas NAO e chamado em:
- `recoverApp()` (`AgentLoop.java:552-559`) — faz `stuckDetector.reset()` mas nao `rewardPropagator.reset()`
- `handleOoaRestart()` (`AgentLoop.java:577-592`) — mesmo problema
- `executeAction(RESTART)` (`AgentLoop.java:608-615`) — nao reseta nada

Os rewards acumulados persistem apos RESTART, reforçando permanentemente o vies por telas ja visitadas.

**Consequencia empirica no munch**:
- Iter 0-150: exploracao saudavel, descobre 28 estados, reward cresce gradualmente
- Iter 150+: 2 hashes (e541a335, d8ff8577) com reward ~14000 cada
- Tier 4: CLICK no d8ff8577 tem score ~14200 (reward=14000 + decay+component+confirmed=200)
- Tier 3: BACK no e541a335 vai para d8ff8577 (proactive backtrack por saturacao)
- Resultado: CLICK → e, BACK → d, CLICK → e, BACK → d — ping-pong por 900+ iteracoes
- 56% do tempo total desperdicado

**Por que o ping-pong NAO e detectado**:
- StuckDetector: hash MUDA a cada iteracao (e→d→e→d) → `consecutiveUnchanged=0` → nunca stuck
- PlateauDetector: `isNewState=false` (ambos ja conhecidos), MAS `action_had_effect=true` nao e verificado pelo PlateauDetector (ele ve `isNewState`, que e false). O plateau DEVERIA disparar, mas como a janela de 10 iters precisa de TODAS sem progresso, qualquer iteracao com novo estado reseta.
  - No munch: `isNewState=false` em todas as 900 iters de ping-pong → plateau DEVERIA ser detectado apos 10 iters
  - Verificacao: O trace mostra `score_tier=4` e `score_tier=3` alternando. Se o plateau ativasse, veríamos `stochastic=true` com probabilidade 0.5 (em vez de 0.15). Dos 456 acoes stochastic no munch, isso sugere que o plateau PODE estar ativo, mas o stochastic nao quebra o ping-pong porque ambos hashes tem reward ~14000 — mesmo com selecao aleatoria, os 2 hashes dominam.
  - **Conclusao**: Mesmo com plateau detector funcionando, o reward scorer impede a fuga do ciclo.

---

### Bug C — OOA Recovery Nao Fecha App do Foreground (SEVERO)

**Arquivo**: `AgentLoop.java:577-592`

```java
private void handleOoaRestart() {
    consecutiveOoaAfterRestart++;
    if (consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART) {
        // Fallback: forceStop + startApp — MAS so do TARGET, nao do foreground!
        appController.forceStop(packageName);   // ← forceStop do app ALVO
        sleep(200);
        appController.startApp(packageName);
        // ...
    } else {
        recoverApp();  // ← tambem so faz forceStop(packageName)
    }
}
```

`recoverApp()` (`AgentLoop.java:552-559`):
```java
private void recoverApp() {
    appController.forceStop(packageName);  // ← so o target!
    sleep(200);
    appController.startApp(packageName);
    sleep(800);
    stuckDetector.reset();
    cachedScreenState = null;
}
```

**Fluxo do bug no hourly**:
1. Iter 113: CLICK na GalleryActivity abre `com.google.android.soundpicker`
2. Iter 114-116: `outOfAppCounter` incrementa (tolerancia=3)
3. Iter 117: tolerancia excedida → `handleOoaRestart()` → `forceStop("com.github.axet.hourlyreminder")` → `startApp("com.github.axet.hourlyreminder")`
4. MAS o SoundPicker continua no foreground! O `startApp` lanca o target via intent, mas o SoundPicker tem prioridade de Activity stack
5. Iter 118: `root.getPackageName()` = `"com.google.android.soundpicker"` → OOA novamente
6. Loop infinito: 155 iteracoes gastas

**Sobre o fallback `consecutiveOoaAfterRestart >= 3`** (`AgentLoop.java:105`): Este mecanismo EXISTE e deveria escalar a recuperacao. Mas o fallback faz EXATAMENTE A MESMA COISA que o caminho normal — `forceStop(packageName) + startApp(packageName)`. A unica diferença e um log e reset do counter. O foreground app nunca e fechado.

**O foreground package esta DISPONIVEL**: Na deteccao OOA (`AgentLoop.java:242`):
```java
String foregroundPkg = rootPkg != null ? rootPkg.toString() : "null";
```
O `foregroundPkg` e conhecido. E passado para `RvTrack.ooa()` e para o trace. Mas NUNCA e usado para `forceStop`.

---

### Bug D — Sem Estrategia para Telas Vazias / Splash Screens (SEVERO)

**Arquivos**: `AgentLoop.java:282-320`, `ActionSelector.java:385-432`

**Fluxo do blippex**:
1. App lanca no SplashActivity
2. `uiCapture.capture(root)` retorna itens, MAS nenhum e interativo (nao clickable, nao scrollable, nao editable)
3. `generateCandidateActions()` percorre todos os itens:
   ```java
   for (ScreenItem item : screen.getItems()) {
       if (!item.isEnabled()) continue;
       Rect bounds = item.getBounds();
       if (bounds == null) continue;
       if (item.isClickable()) actions.add(CLICK...);      // nenhum clickable
       if (item.isLongClickable()) actions.add(LONG_CLICK...); // nenhum
       if (item.isEditable()) actions.add(SET_TEXT...);     // nenhum
       if (item.isScrollable()) actions.add(SCROLL...);     // nenhum
   }
   ```
   → Lista vazia de candidatos
4. Tier 2: `untested` vazio → skip
5. Tier 3: `node.getSaturationRate()` = 1.0 (totalActions=0 → retorna 1.0 por `ScreenNode.java:172`), MAS `successorTracker.getParents(hash)` vazio (primeira visita) → skip
6. Tier 4: `allActions` = [RESTART(score=-500)] → seleciona RESTART
7. RESTART → forceStop → startApp → app lanca no SplashActivity → volta ao passo 1
8. Loop: 132/141 iteracoes sao RESTART no SplashActivity

**O app FAZ auto-transicao** splash → main apos ~2-3s (comportamento padrao de splash screens com Handler). Mas cada RESTART leva ~1.2s (forceStop 200ms + startApp 800ms + throttle 100ms) e reseta o timer do splash. O agente nunca espera o suficiente para a transicao ocorrer.

**Coordenadas no trace confirmam**: As unicas iteracoes com hash diferente de SplashActivity sao iter 4 (saiu para Chrome) e iter 36 (finalmente chegou no MainActivity apos uma espera acidental). Apos iter 38, nunca mais sai do splash.

---

### Bug E — Deteccao de Efeito Ignora Mudancas de Texto (MODERADO)

**Arquivos**: `AgentLoop.java:425`, `ScreenState.java:59-95`

**Codigo de deteccao de efeito** (`AgentLoop.java:425`):
```java
boolean hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);
```

**Codigo de hash** (`ScreenState.java:85-94`):
```java
private static String widgetSignature(ScreenItem item) {
    String className = item.getClassName() != null ? item.getClassName() : "";
    String resourceId = item.getResourceId() != null ? item.getResourceId() : "";
    int mask = 0;
    if (item.isClickable())     mask |= MASK_CLICKABLE;
    if (item.isScrollable())    mask |= MASK_SCROLLABLE;
    if (item.isCheckable())     mask |= MASK_CHECKABLE;
    if (item.isLongClickable()) mask |= MASK_LONG_CLICKABLE;
    if (item.isEnabled())       mask |= MASK_ENABLED;
    return className + "|" + resourceId + "|" + mask;
}
```

O hash usa APENAS: `className`, `resourceId`, `interactMask` (bitmask de 5 flags). Exclui: `text`, `contentDescription`, `bounds`, `hint`, `inputType`, `parentIndex`, `packageName`.

**Consequencia no analyticaltranslator**:
- Tela: 1 EditText + 1 Button ("Translate") + 2 TextViews (output)
- SET_TEXT no EditText → texto muda para "test" → hash nao muda (texto excluido)
- CLICK no Button → app traduz → texto aparece no TextView output → hash nao muda
- `hadEffect=false` em 100% das iteracoes → agente conclui que NENHUMA acao funciona
- StuckDetector: `consecutiveUnchanged` incrementa a cada iter → RESTART apos 10

**Por que o texto esta excluido do hash (design original)**:
- Evitar explosao de estados: news feeds, timestamps, notificacoes mudam texto a cada segundo
- FastBot (ICSE 2023) usa a mesma abordagem: hash estrutural sem texto
- O comentario em `ScreenItem.java:11` diz explicitamente: "Excluded from hash: text, contentDescription"

**Trade-off**: Incluir texto no hash causaria milhares de estados fantasma em apps com conteudo dinamico. NAO mudar o hash. Em vez disso, tratar SET_TEXT como efeito implicito (o texto SEMPRE muda apos SET_TEXT).

---

### Bug F — Exception Swallowing no Loop Principal (MODERADO)

**Arquivo**: `AgentLoop.java:197-209`

```java
public void run() {
    startTimeMs = System.currentTimeMillis();
    iteration = 0;
    while (System.currentTimeMillis() < deadline) {
        try {
            runIteration();
        } catch (Exception e) {
            Log.w(TAG, "Iteration " + iteration + " error: " + e.getMessage());
            // ← NENHUMA trace line escrita!
            // ← Log.w vai para logcat, que pode nao ser capturado pelo plugin Python
        }
        iteration++;
    }
}
```

Se a excecao ocorre antes do `traceWriter.writeLine()` (linha 500), a iteracao nao produz NENHUM output. Como o rvsmart roda via `app_process` (UID 2000, sem acesso ao logcat do device), o `Log.w` se perde.

**Cenario do dnshero**: O app requer um dominio DNS valido no EditText da LoadingActivity. O InputValueGenerator gera "test" (generico). O app provavelmente lanca excecao no processamento. A cada iteracao: captura UI → aciona acao → app lanca excecao → catch no runIteration() ou no processamento subsequente → exception propagada → catch no run() → Log.w → nenhuma trace → proxima iteracao. 300 segundos, 0 bytes de trace.

---

## 14. Anomalias Adicionais (Nao Cobertas na Parte I)

### Anomalia 1: WtgScorer Inicializado com Parametro Morto

**Arquivo**: `ActionSelector.java:151`

```java
this.scorers.add(new WtgScorer(0));  // ← parametro "wtgScore=0"
```

**`WtgScorer.java:47`**:
```java
private final int wtgScore;
public WtgScorer(int wtgScore) { this.wtgScore = wtgScore; }
```

O campo `wtgScore` e armazenado mas **NUNCA lido** em nenhum metodo. O `score()` usa constantes internas `BOOST_1_HOP=200`, `BOOST_2_HOP=100`, `BOOST_3_HOP=50`. O parametro e vestigial de um design anterior.

---

### Anomalia 2: StuckDetector.updateWithActionType() — Codigo Morto

**Arquivo**: `StuckDetector.java:103-121`

```java
public boolean updateWithActionType(String currentHash, Action.Type actionType) {
    // ... SET_TEXT exemption: nao incrementa consecutiveUnchanged
    if (actionType == Action.Type.SET_TEXT) {
        return consecutiveUnchanged >= stuckMaxBlocks;  // Nao incrementa!
    }
    consecutiveUnchanged++;
    // ...
}
```

Este metodo **nunca e chamado**. O AgentLoop usa `stuckDetector.getConsecutiveUnchanged()` diretamente (`AgentLoop.java:351`), que e atualizado via `Learner.update()` → `stuckDetector.update(hash)` (sem isencao por tipo de acao).

**Consequencia**: SET_TEXT em forms incrementa o stuck counter igual a qualquer outra acao. Em telas de formulario onde SET_TEXT nao muda o hash, o agente atinge stuck threshold (10) e faz RESTART prematuro, desperdiçando o progresso de preenchimento do formulario.

---

### Anomalia 3: PlateauDetector — Interacao com Ping-Pong

**Arquivo**: `PlateauDetector.java:38-69`

```java
public void recordIteration(boolean isNewState, boolean hasNewMopCoverage) {
    boolean hasProgress = isNewState || hasNewMopCoverage;
    // ...
}

public boolean isPlateauDetected() {
    for (boolean hasProgress : window) {
        if (hasProgress) return false;  // UMA iteracao com progresso cancela plateau
    }
    return true;
}
```

No cenario de ping-pong do munch:
- `isNewState`: false (ambos hashes ja conhecidos) em todas as 900+ iters de ping-pong
- `hasNewMopCoverage`: false (sem novas coberturas) em todas

Portanto o PlateauDetector DEVERIA ativar apos 10 iteracoes de ping-pong. A pergunta e: por que o stochastic boost (0.15 → 0.50) nao quebra o ciclo?

Resposta: Porque o RewardScorer com 14000 pontos domina. Mesmo com stochastic selection (softmax), a probabilidade de escolher uma acao com score 14000 vs uma com score 200 e:
```
P(14000) = exp(14000/50) / (exp(14000/50) + exp(200/50))
         = exp(280) / (exp(280) + exp(4))
         ≈ 1.0  (praticamente 100%)
```

O softmax com temperature=50 e INCAPAZ de diversificar quando a diferença de scores e de 4 ordens de magnitude. O RewardScorer torna o stochastic selection inutil.

---

### Anomalia 4: ScreenNode.getSaturationRate() para Telas Vazias

**Arquivo**: `ScreenNode.java:171-186`

```java
public float getSaturationRate() {
    if (totalActions == 0) return 1.0f;  // ← 100% saturado se 0 acoes!
    // ...
}
```

Telas sem elementos interativos (splash screens) retornam `saturationRate=1.0`. Na logica do Tier 3 (`ActionSelector.java:224`):
```java
if (successorTracker != null && node != null && node.getSaturationRate() >= 0.8f) {
```

Splash screens com 0 acoes ativam backtrack proativo (correto em principio — nao ha nada para fazer). Mas se nao ha parents (primeira tela), o BACK e pulado e cai no Tier 4 que so tem RESTART. O resultado e correto (RESTART), mas o diagnostico no trace mostra "saturated=1.0" em uma tela que na verdade esta VAZIA — semanticamente confuso.

---

### Anomalia 5: RewardPropagator.reset() Nunca E Chamado

**Arquivo**: `RewardPropagator.java:136-140`

```java
public void reset() {
    trajectory.clear();
    rewards.clear();
    accumulatedRewards.clear();
}
```

Este metodo **nao e chamado** em nenhum lugar:
- `recoverApp()` (`AgentLoop.java:552-559`): reseta `stuckDetector`, `cachedScreenState`, mas NAO `rewardPropagator`
- `handleOoaRestart()` (`AgentLoop.java:577-592`): idem
- `executeAction(RESTART)` (`AgentLoop.java:608-615`): nao reseta nada alem de `cachedScreenState`

Os rewards acumulados persistem indefinidamente, mesmo apos RESTART. Isso reforça o vies por telas da sessao anterior do app (se o app crashou e foi restartado, os rewards das telas pre-crash continuam altos).

---

### Anomalia 6: RESTART no executeAction() nao reseta StuckDetector

**Arquivo**: `AgentLoop.java:608-615`

```java
case RESTART:
    appController.forceStop(packageName);
    sleep(200);
    appController.startApp(packageName);
    sleep(800);
    RvTrack.incrementRestarts();
    cachedScreenState = null;
    break;
    // ← stuckDetector.reset() NAO e chamado!
```

Compare com `recoverApp()` (`AgentLoop.java:552-559`) que FAZ `stuckDetector.reset()`. Quando o agente escolhe RESTART deliberadamente (Tier 4), o stuck detector NAO e resetado. Se o agente estava em stuck (consecutiveUnchanged=9) e fez RESTART, o counter persiste. Na proxima iteracao, se o hash for o mesmo (splash screen apos restart), `consecutiveUnchanged` chega a 10 e dispara stuck recovery novamente.

---

### Anomalia 7: Cached Screen State Nao Invalidado em System Dialog

**Arquivo**: `AgentLoop.java:229-235`

```java
if (dialogDetector.isSystemDialog(root)) {
    dialogDetector.dismiss(root);
    RvTrack.incrementSystemDialogs();
    metricsCollector.recordSystemDialog();
    return;  // ← cachedScreenState NAO e invalidado!
}
```

Se a iteracao anterior cacheou um `postActionState`, e a proxima iteracao encontra um system dialog (dismiss + return), o cache permanece valido. Na iteracao seguinte, o agente reutiliza a tela ANTES do dialog, ignorando o estado atual (que pode ter mudado apos o dialog ser fechado).

---

### Anomalia 8: Effect Detection via Adaptive Wait — Stale State

**Arquivo**: `AgentLoop.java:431-441`

```java
if (!hadEffect && needsAdaptiveWait && config.getAdaptiveWaitMs() > 0) {
    sleep(config.getAdaptiveWaitMs());
    AccessibilityNodeInfo rootAdaptive = devController.getUiAutomation().getRootInActiveWindow();
    if (rootAdaptive != null) {
        // ... recaptura e verifica efeito
    }
    // Se rootAdaptive == null: hadEffect permanece false (valor anterior)
    // Nao tenta recovery — transient null root ignorado silenciosamente
}
```

Se `rootAdaptive` e null (transient ANR durante adaptive wait), o codigo nao tenta recuperar. O `hadEffect` fica com o valor da captura PRE-adaptive-wait (false, porque adaptive wait so e tentado se `!hadEffect`). Isso e correto em resultado (hadEffect=false), mas o agente perde a oportunidade de detectar uma transicao que ocorreu durante o wait.

---

## 15. Analise do Hash de Elementos — Resposta a Pergunta Central

O usuario pergunta: "sera que nosso hash para identificar elementos nao esta bom?"

### O que o hash FAZ:
```
widgetSignature = className + "|" + resourceId + "|" + interactMask
screenHash = Objects.hash(activity, sorted_unique_signatures...)
```

Deduplicacao via LinkedHashSet: se 10 items de ListView tem `"ImageView||17"`, vira 1 assinatura. Isso e o padrao FastBot para evitar que listas inflem o numero de estados.

### O que o hash EXCLUI:
- `text` — conteudo textual do widget
- `contentDescription` — acessibilidade
- `bounds` — posicao/tamanho na tela
- `hint` — placeholder de campos de texto
- `inputType` — tipo de input (texto, numero, email)
- `parentIndex` — posicao na hierarquia
- `packageName` — pacote do widget

### Avaliacao por cenario:

| Cenario | Hash correto? | Problema? |
|---------|---------------|-----------|
| **analyticaltranslator** (SET_TEXT muda texto, hash nao muda) | Correto por design | Sim — efeito invisivel |
| **munch** (ping-pong entre 2 hashes) | Correto — 2 telas diferentes | Nao — problema e no scoring |
| **blippex** (splash com 0 elementos) | Correto — hash do activity name | Nao — problema e falta de espera |
| **hourly** (OOA storm) | Correto | Nao — problema e recovery |
| **dnshero** (silent hang) | N/A — nenhuma captura | Nao — problema e exception |
| **ListView dedup** (10 items → 1 sig) | Correto por design | Depende — pode mascarar estado de scroll |

### Conclusao sobre o hash:

O hash NAO e a causa-raiz da maioria dos bugs. Ele e um trade-off deliberado (evitar explosao de estados vs perder mudancas de texto). O **unico cenario** onde o hash causa problema real e a deteccao de efeito para SET_TEXT (analyticaltranslator). A correcao nao e mudar o hash — e tratar SET_TEXT como efeito implicito.

O hash de deduplicacao (FastBot pattern) pode causar problemas em apps com listas longas onde o SCROLL revela novos items com mesma assinatura (mesmo className, sem resourceId). Nesse caso, scroll nao muda o hash, e o agente nao sabe que revelou novos items. Mas isso nao foi observado neste experimento.

---

## 16. Diagnostico Consolidado — Revisado

### Bugs por Prioridade (revisada)

| # | Bug | Severidade | Causa-Raiz | APKs | Impacto | Esforco |
|---|-----|-----------|------------|------|---------|---------|
| A | StaticMap formato JSON | **CRITICO** | Parser espera Object, JSON tem Array + nomes de atividade incompativeis | TODOS | MOP e WTG nunca funcionaram | Medio |
| B | RewardScorer acumulacao | **CRITICO** | accumulatedRewards cresce infinitamente, maxCumulativeFactor nunca usado | munch (+todos indiretamente) | Score dominado, ping-pong, stochastic inutil | Baixo (remover) |
| C | OOA nao fecha foreground | SEVERO | forceStop so do target, nunca do foreground | hourly | 57.8% iters perdidas | Baixo |
| D | Telas vazias sem espera | SEVERO | 0 candidates → RESTART imediato sem esperar auto-transicao | blippex, translator | 85-93% iters perdidas | Baixo |
| E | SET_TEXT sem efeito | MODERADO | Hash estrutural exclui texto por design | translator | 100% falso negativo | Baixo |
| F | Exception silenciosa | MODERADO | catch no run() nao escreve trace | dnshero | 100% tempo perdido | Baixo |
| - | StuckDetector exemption | MODERADO | updateWithActionType() nunca chamado | forms em geral | RESTART prematuro em forms | Baixo |
| - | RESTART nao reseta stuck | BAIXO | executeAction(RESTART) nao chama stuckDetector.reset() | splash loops | Stuck re-trigger apos restart | Baixo |
| G | AccessibilityNodeInfo leak | **CRITICO** | root/rootAfter/rootAdaptive nunca reciclados via recycle() em AgentLoop | TODOS | ~4000 objetos nativos vazados por run de 300s; risco de OOM em runs longos | Baixo |
| H | UICoverageTracker ID mismatch | SEVERO | Registro usa `res:id/...`, interacao usa `coords:x,y` — nunca casam | TODOS | CoverageDensityScorer sempre retorna gap maximo; saturation_rate inconsistente | Medio |
| I | PathBuffer off-by-one | SEVERO | `invalidateIfDiverged()` compara hash atual com expected errado | TODOS | Caminhos BFS de 2+ hops sempre falham no primeiro hop; recovery multi-hop inoperante | Baixo |
| J | ScreenNode.totalActions first-visit | MODERADO | `totalActions` setado apenas na primeira visita | telas transientes | Se primeira visita ve 0 items (tela transiente), saturacao permanentemente 1.0 | Baixo |

### Solucoes Propostas (revisadas, alinhadas com P1)

**Principio**: Nao adicionar mecanismos. Consertar o que esta quebrado e remover o que e prejudicial.

| # | Bug | Solucao | Filosofia |
|---|-----|---------|-----------|
| A | StaticMap formato (triplice) | (1) Reescrever parseReachability/parseTransitions para ler JsonArray. (2) Corrigir normalizacao de activity names para matching fully-qualified. (3) Adaptar modelo de dados de transitions (sourceId/targetId/events). Ver Secao 19.6. | Fix (~60 linhas) |
| B | RewardScorer | **Remover RewardScorer + RewardPropagator** — com MOP+WTG funcionando (Bug A fix), o agente tera guiagem real e nao precisa de TD learning. O reward era uma compensacao por MOP/WTG nao funcionarem. | Simplificacao (P1) |
| C | OOA foreground | Recovery multi-stage: (1) `input keyevent BACK` para fechar dialog/modal, (2) se ainda OOA, `forceStop(foregroundPkg)`, (3) depois `forceStop(target) + startApp(target)`. | Fix (~10 linhas) |
| D | Telas vazias | Se 0 candidatos e sem parents, sleep(2-3s) e recapturar. So RESTART se ainda vazio apos espera. | Fix (5 linhas) |
| E | SET_TEXT efeito | Se action.type == SET_TEXT, hadEffect=true incondicionalmente. | Fix (2 linhas) |
| F | Exception trace | Escrever trace line com action_type="ERROR" no catch block de run(). | Fix (3 linhas) |
| - | StuckDetector | Usar updateWithActionType() em vez de getConsecutiveUnchanged() no AgentLoop. | Fix (1 linha) |
| - | RESTART stuck | Adicionar stuckDetector.reset() em executeAction(RESTART). | Fix (1 linha) |
| - | CoverageDensityScorer | Remover (codigo morto). | Limpeza (P1) |
| - | WtgScorer(0) param | Remover parametro vestigial. | Limpeza |
| G | AccessibilityNodeInfo leak | `root.recycle()` em try/finally nos 4 call sites de `getRootInActiveWindow()` em AgentLoop. | Fix (4 blocos) |
| H | UICoverageTracker ID mismatch | Unificar chave: usar mesmo esquema (resource-id ou coords) para `registerScreenElements()` e `recordInteraction()`. | Fix |
| I | PathBuffer off-by-one | Corrigir `invalidateIfDiverged()` para comparar com o hash expected correto na posicao atual do path. | Fix (2 linhas) |
| J | ScreenNode.totalActions | Atualizar `totalActions` em toda visita usando `Math.max(existing, newCount)`. | Fix (1 linha) |

### Cadeia de Scoring Simplificada (proposta)

**Antes** (8 scorers, 50% quebrados):
```
MopScorer(QUEBRADO) + WtgScorer(QUEBRADO) + GradualDecay + SystemElement
+ ComponentPriority + ConfirmedCoverage + RewardScorer(PREJUDICIAL) + CoverageDensity(MORTO)
```

**Depois** (6 scorers, todos funcionais):
```
MopScorer(CONSERTADO) + WtgScorer(CONSERTADO) + GradualDecay + SystemElement
+ ComponentPriority + ConfirmedCoverage
```

Reducao de 8 → 6 scorers. Remocao de toda a infraestrutura de reward propagation (RewardPropagator, RewardScorer, N-step TD, trajectory tracking). O agente volta a ser **DFS guiado por analise estatica** — que era o design original do gh29.

---

## 17. Arquivos Afetados

### Java (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`)

| Arquivo | Mudanca |
|---------|---------|
| `staticdata/StaticMap.java` | Reescrever parseReachability() e parseTransitions() + fix activity name matching |
| `core/AgentLoop.java` | OOA fix, splash wait, SET_TEXT effect, error trace, stuck detector call, RESTART reset, remover wiring do RewardPropagator |
| `Main.java` | Remover instanciacao de RewardPropagator, ajustar ActionSelector constructor |
| `strategy/ActionSelector.java` | Remover RewardScorer e CoverageDensityScorer do constructor |
| `strategy/RewardPropagator.java` | Remover (backup/) |
| `strategy/scorers/RewardScorer.java` | Remover (backup/) |
| `strategy/scorers/CoverageDensityScorer.java` | Remover (backup/) |
| `strategy/scorers/WtgScorer.java` | Limpar parametro vestigial |
| `core/Config.java` | Limpar constantes de reward nao usadas |
| `graph/ScreenNode.java` | Limpar cumulativeRewards (so usado por RewardPropagator) + fix totalActions first-visit (Bug J) |
| `strategy/PathBuffer.java` | Fix off-by-one em invalidateIfDiverged() (Bug I) |
| `core/UICoverageTracker.java` | Fix ID mismatch entre registro e interacao (Bug H) |

### Python (`modules/rvsmart-tool/`)

| Arquivo | Mudanca |
|---------|---------|
| `src/rvsmart_tool/tools/rvsmart/tool.py` | Detectar trace file vazio como erro |

### Testes

| Arquivo | Mudanca |
|---------|---------|
| Testes de RewardScorer/RewardPropagator | Remover |
| Testes de CoverageDensityScorer | Remover |
| Novos testes para StaticMap | Testar com formato JSON real |
| Novos testes para OOA com foreground pkg | Validar recovery |
| Novos testes para PathBuffer | Validar invalidateIfDiverged com paths de 2+ hops |
| Testes de UICoverageTracker | Validar que registro e interacao usam mesma chave |

---

## 18. Validacao

Re-executar gh31_mini (5 APKs x rvsmart:mvp x 1 rep x 300s) com as correcoes e comparar:

| Metrica | Esperado Antes | Esperado Depois |
|---------|---------------|-----------------|
| blippex activities | 100% (2/2) | Manter ou melhorar (splash wait) |
| munch activities | 80% (4/5) | >= 80% (sem ping-pong, mais exploracao) |
| translator activities | 50% (1/2) | > 50% (SET_TEXT funcional, stuck fixo) |
| dnshero | 0 iters | > 0 iters (trace de erro visivel) |
| hourly activities | 50% (2/?) | > 50% (OOA recovery funcional) |
| MOP scorer | 0 em 100% | > 0 em APKs com cobertura |
| WTG scorer | 0 em 100% | > 0 em APKs com transitions |
| RESTART % | 24.3% geral | < 10% |
| Reward max | 14000+ | N/A (removido) |
| PathBuffer recovery | Falha em 2+ hops | Sucesso em multi-hop BFS |
| Saturation tracking | Inconsistente (ID mismatch) | Valores coerentes por tela |

---

## 19. Validacao Cruzada — Analise por 5 LLMs

**Data**: 2026-03-07 (complemento as Partes I e II)
**Metodo**: O plano de diagnostico (Secoes 1-18) foi submetido a 5 LLMs independentes (Claude Opus 4.6, Codex, Gemini, Minimax, Qwen) para revisao e identificacao de lacunas. As analises foram sintetizadas via subagentes paralelos com raciocinio estruturado (MCP sequential thinking).
**Analises individuais**: `docs/rvsmart_refactoring/analise_*.md`

### 19.1 Consenso Universal (5/5 LLMs)

Todos os 6 bugs originais (A-F) e todas as anomalias (1-8) foram **confirmados** por todas as LLMs. Nenhum bug foi refutado. Concordancia total em:

| Item | Consenso |
|------|----------|
| Bug A (StaticMap parser) | CRITICO — causa-raiz #1 do sistema |
| Bug B (RewardScorer) | REMOVER, nao apenas limitar |
| Bug C (OOA recovery) | forceStop do foreground package |
| Bug D (Splash screens) | sleep antes de RESTART |
| Bug E (SET_TEXT efeito) | Efeito implicito, NAO mudar hash |
| Bug F (Exception) | Trace line no catch |
| Hash design | NAO e causa-raiz — correto por design |
| Scoring 8→6 | Aprovado — remover Reward + CoverageDensity |

### 19.2 Novos Bugs Validados (achados por 2+ LLMs independentemente)

| Bug | Achado por | Severidade | Descricao |
|-----|-----------|-----------|-----------|
| **G** — AccessibilityNodeInfo leak | Claude, Codex, Qwen (3/5) | CRITICO | `root`/`rootAfter`/`rootAdaptive` nunca reciclados; ~4000 objetos nativos vazados por run de 300s |
| **H** — UICoverageTracker ID mismatch | Claude, Codex (2/5) | SEVERO | Registro usa `res:id/...`, interacao usa `coords:x,y` — coverage tracker nunca casa elementos |
| **I** — PathBuffer off-by-one | Claude, Qwen (2/5) | SEVERO | `invalidateIfDiverged()` compara hash com posicao errada; BFS multi-hop sempre falha |
| Activity name normalization (parte do Bug A) | Claude, Codex, Minimax (3/5) | CRITICO | Triplice falha: JSON array vs Object + nomes de atividade incompativeis + field-level mapping |
| HeapMonitor formula errada | Claude, Codex (2/5) | MODERADO | `free/max` em vez de `(max-total+free)/max`; throttle falso cedo na execucao |
| CrashInterceptor race condition | Claude, Qwen (2/5) | MODERADO | `hasCrash()` + `consumeCrash()` nao atomico; segundo crash pode ser perdido |

### 19.3 Achados Unicos de Alto Valor (1 LLM, validacao pendente)

| Achado | LLM | Acao |
|--------|-----|------|
| `StuckDetector.update()` nunca chamado (recovery inteira morta) | Qwen | **VERIFICAR** — se confirmado, e CRITICO |
| Softmax T=50 inutil com deltas de 14K (plateau escape impossivel) | Minimax | Resolvido indiretamente pela remocao do RewardScorer (Bug B) |
| OOA multi-stage: BACK primeiro, depois forceStop, depois restart | Gemini | **CONSIDERAR** como melhoria ao fix do Bug C |
| Retry loop nao verifica crash entre acao e recaptura | Claude, Qwen | **CONSIDERAR** para Phase 2 |
| `ScreenNode.totalActions` setado so na primeira visita | Claude | Adicionado como Bug J |

### 19.4 Desacordos e Resolucoes

| Topico | Visoes | Resolucao |
|--------|--------|-----------|
| Anomalia 4 (CoverageDensityScorer) | Plano: "codigo morto". Claude: "wired mas quebrado por Bug H". | Irrelevante — ambos concordam em REMOVER |
| Anomalia 8 (adaptive wait root null) | Plano: concern. Claude: REFUTADO (codigo trata null corretamente). | Removido da lista de bugs |
| BUG 4 (ping-pong) — detector de ciclo dedicado? | Gemini: desnecessario (resolvido por Bug B). Minimax: precisa tambem fix de softmax. | Remover RewardScorer primeiro, reavaliar se ciclo persiste. Sem detector de ciclo na fase 1 |
| Severidade de Bug E | Plano: MODERADO. Qwen: SEVERO. | Manter MODERADO — impacto real apenas em apps tipo translator; fix e trivial |

### 19.5 Faseamento Revisado (pos-analise cruzada)

**Fase 1 — Desbloquear o sistema de scoring + parar vazamentos (CRITICO)**:
1. Bug A (StaticMap parser + normalizacao de activity names) — habilita MOP e WTG
2. Bug B (remover RewardScorer + RewardPropagator) — elimina dominacao de score e ping-pong
3. Bug G (AccessibilityNodeInfo recycle) — previne OOM em runs longos

**Fase 2 — Recovery e deteccao de efeito (SEVERO)**:
4. Bug C (OOA forceStop do foreground) — recupera ~58% de iteracoes perdidas
5. Bug D (splash screen wait) — recupera 85-93% de iteracoes perdidas
6. Bug E (SET_TEXT efeito implicito) — corrige falso negativo
7. Bug F (exception trace) — torna falhas visiveis

**Fase 3 — Consistencia interna (MODERADO)**:
8. Bug I (PathBuffer off-by-one) — habilita recovery multi-hop
9. Bug H (UICoverageTracker ID mismatch) — corrige metricas de cobertura
10. Anomalia 2 (usar updateWithActionType) — previne stuck prematuro em forms
11. Anomalia 6 (RESTART reseta stuck) — consistencia entre paths de recovery
12. Bug J (ScreenNode.totalActions) — corrige saturacao em telas transientes

**Fase 4 — Limpeza (P1/P3)**:
13. Remover: RewardPropagator.java, RewardScorer.java, CoverageDensityScorer.java + testes associados
14. Limpar: WtgScorer parametro vestigial, Config constantes de reward, ScreenNode.cumulativeRewards
15. Corrigir: HeapMonitor formula, FileReader nao fechado em StaticMap

**Estimativa total**: ~200 linhas de mudanca em 12 arquivos Java + 1 Python. Sem novas classes. Sem novos mecanismos.

### 19.6 Nota sobre o Bug A — Triplice Falha

3 de 5 LLMs enfatizaram que o Bug A nao e apenas "formato JSON errado" — sao 3 falhas sobrepostas:

1. **Formato**: `getAsJsonObject("reachability")` retorna null porque o JSON tem array
2. **Nomes de atividade**: trace usa `uiactivitiesSplashActivity` (pontos removidos), JSON usa `com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity` (fully qualified) — matching impossivel
3. **Estrutura de campos**: parser espera `Map<String, List<String>>` para transitions, JSON tem `List<{sourceId, targetId, events}>` — modelo de dados incompativel

Todas as 3 falhas precisam ser corrigidas juntas. A correcao parcial (so formato) nao resolve porque o matching de nomes ainda falharia.
