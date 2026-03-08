# Analise de Validacao gh32-rvsmart-scoring-recovery

**Data**: 2026-03-07
**Experimento**: gh32_validation (5 APKs x rvsmart:mvp x 1 rep x 300s)
**Baseline**: gh31_mini (mesmos 5 APKs, mesma configuracao)
**Change**: gh32 -- 10 bug fixes, remocao RewardScorer/RewardPropagator, fixes de recovery

---

## 1. Resumo Executivo

| APK | Iters B | Iters A | it/s B | it/s A | Act% B | Act% A | Meth% B | Meth% A | MOP% B | MOP% A | Errs B | Errs A |
|-----|---------|---------|--------|--------|--------|--------|---------|---------|--------|--------|--------|--------|
| blippex | 141 | 286 | 0.48 | 0.97 | 100% | 100% | 15.5% | 15.5% | 21.4% | 21.4% | 0 | 0 |
| munch | 1072 | 118 | 3.63 | 0.40 | 80% | **20%** | 28.5% | **2.1%** | 48.0% | **3.5%** | 2 | **0** |
| translator | 112 | 302 | 0.38 | 1.02 | 50% | 50% | 17.1% | 17.1% | 25.0% | 25.0% | 2 | 2 |
| dnshero | 0 | 190042 | 0 | 646 | 20% | 20% | 2.9% | 2.9% | 3.0% | 3.0% | 0 | 0 |
| hourly | 268 | 337 | 0.91 | 1.15 | 50% | 50% | 29.9% | **34.9%** | 35.4% | **46.7%** | 2 | 2 |

**Diagnostico por APK:**
- **blippex**: Cobertura de codigo identica. UI coverage melhorou (7->20 hashes, 6->5 activities). Mas 28% OOA no NexusLauncher e 26% RESTART. OOA recovery funciona (max 2 RESTARTs consecutivos vs 104 antes).
- **munch**: REGRESSAO CRITICA. Preso na SplashActivity por 300s inteiros. 95.8% RESTART. 1 hash, 1 activity. Perdeu 196 metodos.
- **translator**: Cobertura de codigo identica. UI coverage melhorou ligeiramente (1->8 hashes, 1->3 activities). Mas 30% OOA no NexusLauncher. 20% RESTART (vs 86% antes).
- **dnshero**: Cobertura identica (vem da instrumentacao, nao do agente). 190K iteracoes de SKIP storm sem throttle. 0 interacoes reais.
- **hourly**: UNICO COM MELHORIA REAL. +51 metodos novos, +11.3% MOP. UI coverage quase dobrou (39->73 hashes). RESTART caiu de 58%->4.5%. 3 activities (antes 2).

---

## 2. Bugs/Anomalias

### 2.1 munch: SplashActivity RESTART loop (CRITICO)

- **Sintoma**: 118 iteracoes, 95.8% RESTART, 1 hash (`34661d74`), 1 activity (`uiactivitiesSplashActivity`)
- **Sequencia**: 3 SCROLLs no ViewPager (sem efeito) -> 105 RESTARTs consecutivos
- **Causa**: No gh31, o agente passava pela splash em 2 iteracoes (SCROLL com efeito). No gh32, os 3 SCROLLs nao tem efeito e o agente entra em RESTART loop. RESTART sempre volta para a splash, criando loop infinito.
- **Score**: total=-500 em 96.6% das iteracoes (Tier 4 = penalidade). O agente detecta que esta preso mas a unica recuperacao eh RESTART, que nao resolve.
- **Tempo medio por iteracao**: 2465ms (vs 271ms no gh31) -- scoring/recovery consome tempo enorme

### 2.2 dnshero: SKIP storm sem throttle (CRITICO)

- **Sintoma**: 190.042 iteracoes, 100% SKIP, action_source="system_dialog"
- **Activity/hash**: vazios em 100% dos records
- **Throughput**: 646 it/s (~1.4ms por iteracao)
- **Causa**: System dialog persistente que o `SystemDialogDetector.dismiss()` nao consegue fechar. Sem throttle, gira a 646 it/s por 300s gerando 44.4MB de trace.
- **Baseline**: 0 bytes (silent hang). O fix do Bug F tornou o problema visivel mas revelou que nao ha escalation path quando dismiss falha.

### 2.3 blippex: OOA no NexusLauncher (28% das iteracoes)

- **Sintoma**: 78 iteracoes no NexusLauncherActivity (27.3%), 9 iteracoes no Chrome (3.1%)
- **Acoes no launcher**: SET_TEXT no search bar (16), BACK (5), LONG_CLICK (4), CLICK (3)
- **Pior tela OOA**: `dc9471af` (NexusLauncher) -- 25 iteracoes, 100% BACK (tentando sair)
- **Pre-existente**: Mesmo comportamento no gh31 (mas la passava pouco tempo fora do app por causa de 93.6% RESTART)

### 2.4 translator: OOA no NexusLauncher (30% das iteracoes)

- **Sintoma**: 90 iteracoes no NexusLauncherActivity (29.8%)
- **Pior tela OOA**: `a671fbb5` (NexusLauncher) -- 49 iteracoes, 100% BACK
- **Pre-existente**: No gh31 o agente ficava preso na MainActivity com 86% RESTART. Agora explora mais (RESTART caiu para 20%) mas cai no launcher.

### 2.5 blippex: SplashActivity stuck (pre-existente, melhorou)

- **gh31**: 129 iteracoes na splash, 93.6% RESTART, 104 RESTARTs consecutivos
- **gh32**: 11 iteracoes na splash, 3.8% do total. Melhora enorme.

### 2.6 Reward field presente no gh31, ausente no gh32

- **gh31**: Campo `reward` presente em todos os traces. Valores acumulados: munch max=18350, hourly max=10469, blippex max=3385
- **gh32**: Campo `reward` AUSENTE em todos os traces. Confirmado: remocao funcional.

---

## 3. Cobertura de Codigo (Coverage)

### 3.1 Resumo final

| APK | Methods B | Methods A | Delta | New | Lost | Act% B | Act% A | Meth% B | Meth% A | MOP% B | MOP% A |
|-----|-----------|-----------|-------|-----|------|--------|--------|---------|---------|--------|--------|
| blippex | 20 | 20 | 0 | 0 | 0 | 100% | 100% | 15.5% | 15.5% | 21.4% | 21.4% |
| munch | 212 | 16 | -196 | 0 | 196 | 80% | 20% | 28.5% | 2.1% | 48.0% | 3.5% |
| translator | 7 | 7 | 0 | 0 | 0 | 50% | 50% | 17.1% | 17.1% | 25.0% | 25.0% |
| dnshero | 18 | 18 | 0 | 0 | 0 | 20% | 20% | 2.9% | 2.9% | 3.0% | 3.0% |
| hourly | 305 | 356 | +51 | 56 | 5 | 50% | 50% | 29.9% | 34.9% | 35.4% | 46.7% |

### 3.2 Progressao de cobertura ao longo do tempo

**blippex:**
| Tempo | Act% B | Meth% B | MOP% B | Act% A | Meth% A | MOP% A |
|-------|--------|---------|--------|--------|---------|--------|
| 30s | 100% | 13.2% | 21.4% | 100% | 10.9% | 21.4% |
| 60s | 100% | 13.2% | 21.4% | 100% | 15.5% | 21.4% |
| 120s | 100% | 15.5% | 21.4% | 100% | 15.5% | 21.4% |
| 300s | 100% | 15.5% | 21.4% | 100% | 15.5% | 21.4% |

Plateau em ~60s (gh32) vs ~120s (gh31). Identico no final.

**munch:**
| Tempo | Act% B | Meth% B | MOP% B | Act% A | Meth% A | MOP% A |
|-------|--------|---------|--------|--------|---------|--------|
| 30s | 40% | 11.7% | 19.3% | 20% | 2.1% | 3.5% |
| 60s | 60% | 17.6% | 32.2% | 20% | 2.1% | 3.5% |
| 120s | 80% | 28.0% | 47.0% | 20% | 2.1% | 3.5% |
| 300s | 80% | 28.5% | 48.0% | 20% | 2.1% | 3.5% |

gh32 nunca progrediu alem dos 16 metodos iniciais (instrumentacao). Plateau instantaneo.

**translator:**
| Tempo | Act% B | Meth% B | MOP% B | Act% A | Meth% A | MOP% A |
|-------|--------|---------|--------|--------|---------|--------|
| 30s | 50% | 17.1% | 25.0% | 50% | 17.1% | 25.0% |
| 300s | 50% | 17.1% | 25.0% | 50% | 17.1% | 25.0% |

Identico. Plateau instantaneo em ambos -- toda cobertura vem da instrumentacao.

**dnshero:**
Identico em ambos (20%, 2.9%, 3.0%). Toda cobertura vem da instrumentacao.

**hourly (UNICA MELHORIA):**
| Tempo | Act% B | Meth% B | MOP% B | Act% A | Meth% A | MOP% A |
|-------|--------|---------|--------|--------|---------|--------|
| 30s | 50% | 25.7% | 29.2% | 50% | 22.9% | 28.5% |
| 60s | 50% | 27.5% | 32.7% | 50% | 26.5% | 35.7% |
| 120s | 50% | 29.9% | 35.4% | 50% | 29.4% | 40.2% |
| 180s | 50% | 29.9% | 35.4% | 50% | 30.0% | 41.9% |
| 240s | 50% | 29.9% | 35.4% | 50% | 34.6% | 46.1% |
| 300s | 50% | 29.9% | 35.4% | 50% | 34.9% | 46.7% |

gh31 plateau em ~120s. gh32 continua crescendo ate 300s! +5% methods, +11.3% MOP. 56 metodos novos incluem fragmentos antes inalcancaveis: WeekSetFragment, RepeatDialogFragment, AlarmsFragment, RepeatIntervalFragment.

### 3.3 MOP Violations

| APK | Violations B | Violations A | Spec | Delta |
|-----|-------------|-------------|------|-------|
| munch | 2 (SSLContextSpec) | 0 | SSLContext | PERDIDAS (nao alcanca HomeActivity) |
| translator | 2 (MessageDigestSpec) | 2 | MessageDigest | MANTIDAS (t=27s, t=65s vs t=23s, t=42s) |
| hourly | 2 (MessageDigestSpec) | 2 | MessageDigest | MANTIDAS + mais timestamps (t=17,83,143,200,248s vs t=13,96s) |

gh31: 6 unique violations, 18 total occurrences
gh32: 4 unique violations, 14 total occurrences
LOST: 2 SSLContextSpec violations do munch (nao alcanca o codigo)

---

## 4. Distribuicao de Acoes (Action Distribution)

### 4.1 Distribuicao global por APK

**blippex:**
| Action | gh31 cnt | gh31 % | gh32 cnt | gh32 % | Delta |
|--------|----------|--------|----------|--------|-------|
| RESTART | 132 | 93.6% | 75 | 26.2% | -67.4pp |
| BACK | 1 | 0.7% | 124 | 43.4% | +42.7pp |
| SKIP | 0 | 0% | 36 | 12.6% | +12.6pp |
| SET_TEXT | 5 | 3.5% | 31 | 10.8% | +7.3pp |
| CLICK | 2 | 1.4% | 14 | 4.9% | +3.5pp |
| LONG_CLICK | 1 | 0.7% | 6 | 2.1% | +1.4pp |

RESTART caiu enormemente. Mas BACK subiu (43.4%) -- indica OOA recovery tentando voltar.

**munch:**
| Action | gh31 cnt | gh31 % | gh32 cnt | gh32 % | Delta |
|--------|----------|--------|----------|--------|-------|
| CLICK | 583 | 54.4% | 0 | 0% | -54.4pp |
| BACK | 446 | 41.6% | 0 | 0% | -41.6pp |
| RESTART | 4 | 0.4% | 113 | 95.8% | +95.4pp |
| SCROLL | 9 | 0.8% | 3 | 2.5% | +1.7pp |
| SKIP | 0 | 0% | 2 | 1.7% | +1.7pp |

Completa inversao. De 54% CLICK para 96% RESTART. Agente completamente quebrado.

**translator:**
| Action | gh31 cnt | gh31 % | gh32 cnt | gh32 % | Delta |
|--------|----------|--------|----------|--------|-------|
| RESTART | 96 | 85.7% | 60 | 19.9% | -65.8pp |
| BACK | 0 | 0% | 104 | 34.4% | +34.4pp |
| SKIP | 0 | 0% | 70 | 23.2% | +23.2pp |
| SET_TEXT | 9 | 8.0% | 51 | 16.9% | +8.9pp |
| CLICK | 7 | 6.2% | 11 | 3.6% | -2.6pp |
| LONG_CLICK | 0 | 0% | 6 | 2.0% | +2.0pp |

RESTART caiu de 86% para 20%. Diversidade de acoes aumentou. Mas BACK alto (34%) indica OOA.

**hourly (MELHOR COMPORTAMENTO):**
| Action | gh31 cnt | gh31 % | gh32 cnt | gh32 % | Delta |
|--------|----------|--------|----------|--------|-------|
| CLICK | 97 | 36.2% | 244 | 72.4% | +36.2pp |
| RESTART | 156 | 58.2% | 15 | 4.5% | -53.7pp |
| SET_TEXT | 10 | 3.7% | 28 | 8.3% | +4.6pp |
| SKIP | 0 | 0% | 39 | 11.6% | +11.6pp |
| SCROLL | 2 | 0.7% | 4 | 1.2% | +0.5pp |
| LONG_CLICK | 3 | 1.1% | 4 | 1.2% | +0.1pp |
| BACK | 0 | 0% | 3 | 0.9% | +0.9pp |

RESTART caiu de 58% para 4.5%. CLICK subiu de 36% para 72%. Comportamento explorador saudavel.

### 4.2 Distribuicao por widget class

**blippex gh32:**
| Widget | Count | % | Acoes |
|--------|-------|---|-------|
| (none) | 234 | 81.8% | BACK:124, RESTART:75, SKIP:35 |
| EditText | 36 | 12.6% | SET_TEXT:31, LONG_CLICK:3, CLICK:2 |
| LinearLayout | 6 | 2.1% | CLICK:5, SKIP:1 |
| TextView | 4 | 1.4% | LONG_CLICK:2, CLICK:2 |
| ImageButton | 3 | 1.0% | CLICK:3 |
| FrameLayout | 2 | 0.7% | CLICK:1, LONG_CLICK:1 |
| View | 1 | 0.3% | CLICK:1 |

81.8% sem widget -- sao BACK/RESTART/SKIP (acoes de sistema, nao de UI).

**munch gh32:**
| Widget | Count | % | Acoes |
|--------|-------|---|-------|
| (none) | 115 | 97.5% | RESTART:113, SKIP:2 |
| ViewPager | 3 | 2.5% | SCROLL:3 |

Praticamente zero interacao com UI.

**munch gh31 (baseline funcional):**
| Widget | Count | % | Acoes |
|--------|-------|---|-------|
| ImageView | 476 | 44.4% | CLICK:476 |
| (none) | 450 | 42.0% | BACK:446, RESTART:4 |
| LinearLayout | 38 | 3.5% | CLICK:38 |
| TextView | 26 | 2.4% | CLICK:26 |
| ImageButton | 24 | 2.2% | CLICK:24 |
| Spinner | 24 | 2.2% | LONG_CLICK:15, SCROLL:6, CLICK:3 |
| EditText | 16 | 1.5% | SET_TEXT:13, LONG_CLICK:2, CLICK:1 |
| LinearLayoutCompat | 11 | 1.0% | CLICK:11 |
| Button | 3 | 0.3% | CLICK:3 |
| ViewPager | 2 | 0.2% | SCROLL:2 |
| ListView | 1 | 0.1% | SCROLL:1 |
| FrameLayout | 1 | 0.1% | CLICK:1 |

Rico mix de widgets: 12 tipos diferentes, bom coverage de componentes.

**translator gh32:**
| Widget | Count | % | Acoes |
|--------|-------|---|-------|
| (none) | 234 | 77.5% | BACK:104, SKIP:70, RESTART:60 |
| TextView | 37 | 12.3% | SET_TEXT:31, CLICK:3, LONG_CLICK:3 |
| EditText | 24 | 7.9% | SET_TEXT:20, LONG_CLICK:3, CLICK:1 |
| Button | 7 | 2.3% | CLICK:7 |

77.5% sem widget (acoes de sistema). Apenas 3 tipos de widget UI.

**hourly gh32 (MELHOR):**
| Widget | Count | % | Acoes |
|--------|-------|---|-------|
| ImageButton | 58 | 17.2% | CLICK:58 |
| (none) | 57 | 16.9% | SKIP:39, RESTART:15, BACK:3 |
| FrameLayout | 54 | 16.0% | CLICK:54 |
| ActionBar$Tab | 49 | 14.5% | CLICK:49 |
| CheckBox | 35 | 10.4% | CLICK:35 |
| EditText | 30 | 8.9% | SET_TEXT:28, CLICK:1, LONG_CLICK:1 |
| Button | 20 | 5.9% | CLICK:20 |
| LinearLayout | 8 | 2.4% | CLICK:8 |
| Switch | 6 | 1.8% | CLICK:6 |
| CheckedTextView | 6 | 1.8% | CLICK:6 |
| Spinner | 6 | 1.8% | LONG_CLICK:3, CLICK:2, SCROLL:1 |
| TextView | 5 | 1.5% | CLICK:5 |
| ViewPager | 3 | 0.9% | SCROLL:3 |

13 tipos de widget! Apenas 17% acoes de sistema. Excelente diversidade de interacao.

---

## 5. Cobertura de UI (UI Coverage)

### 5.1 Resumo

| APK | Hashes B | Hashes A | Delta | Activities B | Activities A | Delta | unique_states A |
|-----|----------|----------|-------|-------------|-------------|-------|-----------------|
| blippex | 7 | 20 | +13 | 6 | 5 | -1 | 11 |
| munch | 29 | 1 | -28 | 5 | 1 | -4 | 1 |
| translator | 1 | 8 | +7 | 1 | 3 | +2 | 2 |
| dnshero | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hourly | 39 | 73 | +34 | 2 | 3 | +1 | 69 |

### 5.2 Per-activity detail

**blippex gh32:**
| Activity | Iters | % total | Hashes | Acoes dominantes |
|----------|-------|---------|--------|-----------------|
| uiMainActivity | 89 | 31.1% | 5 | BACK:80 (90%), SET_TEXT:7, CLICK:1, LONG_CLICK:1 |
| NexusLauncherActivity (OOA) | 78 | 27.3% | 7 | BACK:41 (53%), SET_TEXT:20 (26%), CLICK:8, LONG_CLICK:4 |
| (empty/system) | 99 | 34.6% | 0 | RESTART:64, SKIP:35 |
| uiSplashActivity | 11 | 3.8% | 1 | RESTART:11 |
| Chrome (OOA) | 9 | 3.1% | 7 | CLICK:3, SET_TEXT:2, BACK:2, LONG_CLICK:1 |

**Problema**: 30.4% do tempo fora do app (Launcher + Chrome). 34.6% em telas vazias (RESTART/SKIP). Apenas 31.1% na MainActivity real. O agente gasta mais tempo OOA do que explorando.

**munch gh32 (PRESO):**
| Activity | Iters | % total | Hashes | Acoes |
|----------|-------|---------|--------|-------|
| uiactivitiesSplashActivity | 116 | 98.3% | 1 | RESTART:113, SCROLL:3 |
| (empty/system) | 2 | 1.7% | 0 | SKIP:2 |

1 hash, 1 activity. Zero exploracao.

**munch gh31 (baseline funcional):**
| Activity | Iters | % total | Hashes | Acoes dominantes |
|----------|-------|---------|--------|-----------------|
| uiactivitiesHomeActivity | 1056 | 98.5% | 20 | CLICK:548 (52%), BACK:442 (42%) |
| uiactivitiesSettingsActivity | 7 | 0.7% | 4 | CLICK:4, SET_TEXT:2 |
| NexusLauncherActivity (OOA) | 4 | 0.4% | 3 | CLICK:2, LONG_CLICK:1 |
| uiactivitiesSplashActivity | 2 | 0.2% | 1 | SCROLL:2 |
| uiactivitiesAboutActivity | 1 | 0.1% | 1 | CLICK:1 |

Rich exploration: 20 hashes na HomeActivity, 4 em Settings, 1 em About. Passou pela splash em 2 iteracoes.

**translator gh32:**
| Activity | Iters | % total | Hashes | Acoes dominantes |
|----------|-------|---------|--------|-----------------|
| (empty/system) | 126 | 41.7% | 0 | SKIP:67, RESTART:59 |
| MainActivity | 85 | 28.1% | 1 | BACK:42 (49%), SET_TEXT:31 (36%), CLICK:6, LONG_CLICK:3, SKIP:3 |
| NexusLauncherActivity (OOA) | 90 | 29.8% | 6 | BACK:49 (54%), SET_TEXT:12 (13%), CLICK:2 |
| WhatsNewFullScreen (OOA) | 1 | 0.3% | 1 | RESTART:1 |

**Problema**: Apenas 1 hash na MainActivity (a658526f) apesar de 85 iteracoes. 29.8% no Launcher. 41.7% em telas vazias. O agente fica preso entre MainActivity (1 tela) e Launcher, sem descobrir novas telas.

**hourly gh32 (MELHOR):**
| Activity | Iters | % total | Hashes | Acoes dominantes |
|----------|-------|---------|--------|-----------------|
| activitiesMainActivity | 279 | 82.8% | 69 | CLICK:238 (85%), SET_TEXT:17 (6%), SCROLL:4, LONG_CLICK:4, BACK:2 |
| (empty/system) | 54 | 16.0% | 0 | SKIP:39, RESTART:15 |
| activityGalleryActivity | 3 | 0.9% | 3 | CLICK:3 |
| pickerPickActivity | 1 | 0.3% | 1 | CLICK:1 |

69 hashes na MainActivity! 3 activities reais exploradas. 85% CLICK na MainActivity = exploracao ativa. Apenas 16% em acoes de sistema (down from 58% RESTART no gh31).

**hourly gh31 (baseline):**
| Activity | Iters | % total | Hashes | Acoes dominantes |
|----------|-------|---------|--------|-----------------|
| activitiesMainActivity | 112 | 41.8% | 38 | CLICK:94 (84%), SET_TEXT:10, SCROLL:2, LONG_CLICK:3 |
| (empty/system) | 155 | 57.8% | 0 | RESTART:155 |
| activityGalleryActivity | 1 | 0.4% | 1 | CLICK:1 |

58% RESTART vs 16% no gh32. Apenas 38 hashes vs 69. Melhoria clara.

### 5.3 Per-screen detail (top screens por APK)

**hourly gh32 -- top 15 telas:**
| Hash | Activity | Iters | Acoes | Anomalia |
|------|----------|-------|-------|----------|
| (empty) | -- | 54 | SKIP:39, RESTART:15 | sistema |
| 7acabae9 | MainActivity | 42 | CLICK:41, SCROLL:1 | STUCK (98% CLICK) |
| e41eef3c | MainActivity | 30 | SET_TEXT:17, CLICK:11, LONG_CLICK:2 | mix saudavel |
| 5dfd1176 | MainActivity | 21 | CLICK:19, SCROLL:1, BACK:1 | STUCK (90% CLICK) |
| 170c3de2 | MainActivity | 12 | SET_TEXT:10, CLICK:2 | STUCK (83% SET_TEXT) |
| c99b8d77 | MainActivity | 11 | CLICK:11 | STUCK |
| 895c1fe4 | MainActivity | 10 | CLICK:10 | STUCK |
| b0ad5a54 | MainActivity | 10 | CLICK:10 | STUCK |
| 621840c6 | MainActivity | 9 | CLICK:8, BACK:1 | STUCK |
| f25a4130 | MainActivity | 8 | CLICK:7, SET_TEXT:1 | STUCK |
| 66cfaa3b | MainActivity | 7 | CLICK:6, BACK:1 | STUCK |
| d855c023 | MainActivity | 6 | CLICK:6 | STUCK |
| 98c39a67 | MainActivity | 5 | CLICK:5 | -- |
| 675d2cdd | MainActivity | 5 | CLICK:4, SCROLL:1 | -- |
| c5cf74fb | MainActivity | 5 | CLICK:5 | -- |
| + 59 mais telas (1-5 iters cada) | | | | |

**Observacao**: Muitas telas com >80% CLICK marcadas como STUCK, mas com poucos iters (<15). Isso pode indicar que o agente visita, clica nos elementos disponiveis, e segue em frente (comportamento normal para telas com poucos elementos interagiveis).

**blippex gh32 -- todas as telas:**
| Hash | Activity | Iters | Acoes | Anomalia |
|------|----------|-------|-------|----------|
| (empty) | -- | 99 | RESTART:64, SKIP:35 | 35% do tempo |
| 008003a1 | uiMainActivity | 42 | BACK:42 | STUCK 100% BACK |
| a5c177a0 | NexusLauncher | 28 | SET_TEXT:16, BACK:5, LONG_CLICK:4, CLICK:3 | OOA |
| 4500117f | uiMainActivity | 27 | BACK:23, SET_TEXT:2, CLICK:1, LONG_CLICK:1 | STUCK 85% BACK |
| dc9471af | NexusLauncher | 25 | BACK:25 | STUCK OOA 100% BACK |
| 94213d0d | NexusLauncher | 19 | BACK:11, CLICK:5, SET_TEXT:2, SKIP:1 | OOA |
| 40b5f5ee | uiMainActivity | 14 | BACK:14 | STUCK 100% BACK |
| 99f6ffb3 | uiSplashActivity | 11 | RESTART:11 | STUCK |
| 29627ca5 | uiMainActivity | 5 | SET_TEXT:5 | -- |
| + 12 mais telas (1-3 iters) | | | | |

**Problema grave**: 3 telas de MainActivity com 100% BACK (total 83 iters). O agente nao sabe explorar a UI da MainActivity -- so faz BACK.

### 5.4 Screens visitadas apenas 1 vez

| APK | 1-visit screens B | 1-visit screens A | Total screens B | Total screens A |
|-----|-------------------|-------------------|-----------------|-----------------|
| blippex | 4 | 12 | 7 | 20 |
| munch | 13 | 0 | 29 | 1 |
| translator | 0 | 3 | 1 | 8 |
| hourly | 14 | 33 | 39 | 73 |

Hourly gh32: 33 telas visitadas apenas 1 vez (45% das telas). Isso eh bom -- indica exploracao ampla com pouca revisitacao.

---

## 6. Plateau/Stochastic/Recovery

### 6.1 Stochastic selection %

| APK | Stochastic B | Stochastic A | Esperado normal | Esperado plateau |
|-----|-------------|-------------|-----------------|-----------------|
| blippex | 0.7% | 19.9% | ~15% | ~50% |
| munch | 42.6% | 0.9% | ~15% | ~50% |
| translator | 2.7% | 6.4% | ~15% | ~50% |
| hourly | 17.7% | 17.3% | ~15% | ~50% |

- **hourly**: 17.3% stochastic -- dentro do range normal. Bom.
- **blippex**: 19.9% -- ligeiramente acima do normal, mas nao em plateau
- **munch gh31**: 42.6% -- perto do plateau (o agente ja estava saturado depois de explorar HomeActivity)
- **munch gh32**: 0.9% -- quase zero (preso na splash, nunca entra em modo exploratorio)
- **translator**: 6.4% -- abaixo do normal, indica que o agente raramente faz escolhas aleatorias

### 6.2 Plateau detection (iteracoes sem novos hashes)

**blippex:**
- gh31: 7 hashes alcancados em ~120s. Plateau de 120s-300s (180s sem progresso)
- gh32: 20 hashes. Crescimento: 6 em 30s, 11 em 60s, 15 em 120s, 20 em 180s. Plateau 180s-300s (120s).
- **Melhoria**: plateau mais tardio, mais hashes descobertos

**munch:**
- gh31: 29 hashes. Crescimento: 8 em 30s, 17 em 60s, 29 em 120s. Plateau 120s-300s.
- gh32: 1 hash. Plateau instantaneo (t=0).

**translator:**
- gh31: 1 hash. Plateau instantaneo.
- gh32: 8 hashes. Crescimento: 2 em 30s, 2 em 60s, 6 em 120s, 7 em 180s, 8 em 240s. Crescimento lento mas continuo.
- **Melhoria**: saiu do plateau instantaneo para crescimento distribuido

**hourly:**
- gh31: 39 hashes. Crescimento: 16 em 30s, 25 em 60s, 39 em 120s. Plateau 120s-300s (180s sem progresso).
- gh32: 73 hashes. Crescimento: 6 em 30s, 20 em 60s, 33 em 120s, 52 em 180s, 67 em 240s, 73 em 300s. **NUNCA entra em plateau!** Crescimento continuo ate o fim do timeout.
- **Melhoria significativa**: 73 vs 39 hashes, sem plateau

### 6.3 Recovery analysis

**Max consecutive RESTARTs:**
| APK | gh31 | gh32 | Diagnostico |
|-----|------|------|-------------|
| blippex | 104 | 2 | MELHOROU drasticamente. OOA recovery funcional. |
| munch | 1 | 105 | PIOROU drasticamente. RESTART loop na splash. |
| translator | 93 | 1 | MELHOROU drasticamente. Nao fica mais preso em RESTART loop. |
| hourly | 155 | 1 | MELHOROU drasticamente. OOA recovery funcional. |

**Max consecutive same hash:**
| APK | gh31 | gh32 | Diagnostico |
|-----|------|------|-------------|
| blippex | 103 | 5 | MELHOROU |
| munch | 8 | 105 | PIOROU (splash) |
| translator | 112 | 28 | MELHOROU |
| hourly | 10 | 15 | Ligeiramente pior (mais tempo no hash 7acabae9) |

### 6.4 OOA (out-of-app) %

| APK | OOA % B | OOA % A | Diagnostico |
|-----|---------|---------|-------------|
| blippex | 1.4% | 28.0% | PIOROU -- launcher + Chrome |
| munch | 0.4% | 0% | -- (preso na splash) |
| translator | 0% | 29.8% | PIOROU -- launcher |
| hourly | 0% | 0% | OK |

OOA piorou em blippex e translator. A reducao de RESTART revelou um novo problema: quando o agente nao fica preso em RESTART loop, ele sai do app e nao consegue voltar eficientemente.

### 6.5 Score tier distribution

**hourly gh32 (scores por tier):**
- Tier 2 (exploring): maioria das iteracoes (score 600-850)
- Score total mean: 727.1, median: 716, max: 850

**munch gh32:**
- Tier 4 (penalty): 96.6% das iteracoes (score = -500)
- Score total mean: -459.3

**blippex gh32:**
- Score total mean: 601.4, median: 641, max: 950
- MOP scorer ativo em 68.3% das iteracoes (max=300)

### 6.6 Saturation rate

| APK | Sat rate range B | Sat rate range A |
|-----|-----------------|-----------------|
| blippex | -- | 0.0 - (not tracked in gh31) |
| hourly | 0.0 | 0.0 (reset after each new hash, stays low due to constant discovery) |

---

## 7. Score Breakdown Detalhado

### 7.1 Per-scorer statistics

**blippex gh32:**
| Scorer | Mean | Median | Max | >0% |
|--------|------|--------|-----|-----|
| mop | 204.8 | 300 | 300 | 68.3% |
| wtg | 0.0 | 0 | 0 | 0.0% |
| decay | 141.6 | 139 | 200 | 93.5% |
| coverage | 87.3 | 85 | 100 | 100% |
| confirmed | 33.8 | 16 | 150 | 97.8% |
| component | 147.3 | 100 | 200 | 98.9% |
| system | 0.0 | 0 | 0 | 0.0% |
| **total** | **601.4** | **641** | **950** | |

**munch gh32:**
| Scorer | Mean | Median | Max | >0% |
|--------|------|--------|-----|-----|
| mop | 300.0 | 300 | 300 | 100% |
| wtg | 0.0 | 0 | 0 | 0.0% |
| decay | 8.5 | 0 | 200 | 6.9% |
| coverage | 100.0 | 100 | 100 | 100% |
| confirmed | 6.4 | 2 | 150 | 100% |
| component | 1.5 | 0 | 100 | 3.4% |
| system | 0.0 | 0 | 0 | 0.0% |
| **total** | **-459.3** | **-500** | **850** | |

MOP=300 (maximo) em 100% das iteracoes porque a SplashActivity tem metodos com alcance a operacoes monitoradas. Mas total=-500 por Tier 4 (penalidade de stuck).

**translator gh32:**
| Scorer | Mean | Median | Max | >0% |
|--------|------|--------|-----|-----|
| mop | 78.0 | 0 | 300 | 26.0% |
| wtg | 0.0 | 0 | 0 | 0.0% |
| decay | 163.0 | 200 | 200 | 100% |
| coverage | 100.0 | 100 | 100 | 100% |
| confirmed | 3.8 | 0 | 150 | 26.0% |
| component | 173.4 | 200 | 200 | 100% |
| system | 0.0 | 0 | 0 | 0.0% |
| **total** | **518.3** | **500** | **950** | |

MOP ativo em 26% das iteracoes. Component e decay altos indicam boas candidatas mas em tela unica.

**hourly gh32:**
| Scorer | Mean | Median | Max | >0% |
|--------|------|--------|-----|-----|
| mop | 300.0 | 300 | 300 | 100% |
| wtg | 0.0 | 0 | 0 | 0.0% |
| decay | 188.7 | 200 | 200 | 100% |
| coverage | 97.2 | 100 | 100 | 100% |
| confirmed | 38.8 | 18 | 150 | 71.4% |
| component | 102.5 | 100 | 200 | 100% |
| system | 0.0 | 0 | 0 | 0.0% |
| **total** | **727.1** | **716** | **850** | |

Todos os scorers ativos (exceto WTG e system). Scores saudaveis e bem distribuidos.

### 7.2 Comparacao gh31 vs gh32 (scores)

| Scorer | blippex B | blippex A | hourly B | hourly A |
|--------|-----------|-----------|----------|----------|
| mop | 0.0 | 204.8 | 0.0 | 300.0 |
| decay | 13.9 | 141.6 | 197.6 | 188.7 |
| coverage | 99.5 | 87.3 | 94.2 | 97.2 |
| confirmed | 10.3 | 33.8 | 45.8 | 38.8 |
| component | 9.4 | 147.3 | 101.5 | 102.5 |
| reward | **presente** | **ausente** | **presente** | **ausente** |
| total | -372.7 | 601.4 | 1387.6 | 727.1 |

O total mean do hourly CAIU de 1387.6 para 727.1. Mas isso eh porque o reward scorer foi removido (ele inflava o total com acumulacao). Os scorers reais (mop, decay, component, confirmed) estao mais saudaveis.

### 7.3 WTG scorer

WTG = 0 em 100% das iteracoes em todos os 5 APKs. Nao eh bug -- os APKs nao tem cross-transitions acessiveis pelo agente (ja investigado: blippex 0 cross-transitions, hourly 0 cross-transitions, munch/translator/dnshero tem transitions mas agente nao alcanca as activities).

---

## 8. Comparacao com Criterios de Validacao

| Metrica | Esperado | Resultado | Status |
|---------|----------|-----------|--------|
| blippex activities | Manter ou melhorar | 100% = 100% | OK |
| munch activities | >= 80% | **20%** (regressao) | FALHOU |
| translator activities | > 50% | 50% (igual) | PARCIAL |
| dnshero iters | > 0 | 190042 (mas 100% SKIP) | PARCIAL |
| hourly activities | > 50% | 50% (igual, +1 activity nova) | PARCIAL |
| MOP scorer | > 0 em APKs com dados | 26-100% (funcional) | OK |
| WTG scorer | > 0 em APKs com transitions | 0% (dados insuficientes) | PARCIAL |
| RESTART % | < 10% | hourly 4.5% OK, blippex 26.2%, munch 95.8%, translator 20% | PARCIAL |
| Reward max | N/A (removido) | Removido | OK |
| PathBuffer recovery | Sucesso em multi-hop | Nao testavel (munch preso) | INDETERMINADO |
| Saturation tracking | Coerente por tela | hourly 69 unique_states = funcional | OK |

**Resultado global**: 3 OK, 1 FALHOU, 5 PARCIAL, 2 INDETERMINADO.

---

## 9. Conclusao

### O que realmente melhorou

Apenas **hourly** teve melhoria concreta e mensuravel:
- +56 metodos novos (+5% coverage, +11.3% MOP)
- 73 hashes vs 39 (quase dobrou UI coverage)
- 3 activities vs 2 (+1: pickerPickActivity)
- RESTART 58.2% -> 4.5%
- Crescimento continuo ate 300s (sem plateau)
- 13 tipos de widget interagidos (excelente diversidade)

### O que ficou igual

- **blippex**: Cobertura de codigo identica. UI coverage melhorou (20 vs 7 hashes) mas o agente gasta 28% do tempo no Launcher (OOA) e 35% em telas vazias. So 31% do tempo na MainActivity real.
- **translator**: Cobertura identica. Menos RESTART (20% vs 86%) mas OOA piorou (30% no Launcher). Uma unica tela na MainActivity.
- **dnshero**: Cobertura identica. De silent hang para SKIP storm. Zero interacoes reais em ambos.

### O que piorou

- **munch**: Regressao critica. 80% -> 20% activities, 28.5% -> 2.1% methods, 48% -> 3.5% MOP. Perdeu 196 metodos e 2 violations SSL. Preso na SplashActivity por 300s com 95.8% RESTART.

### Bugs encontrados (a corrigir antes de arquivar)

1. **CRITICO: munch SplashActivity trap** -- RESTART nao resolve splash com auto-transition. Precisa de wait ou acao alternativa quando SCROLLs falham repetidamente.
2. **CRITICO: dnshero SKIP storm** -- System dialog dismiss sem throttle gera 190K linhas (44MB). Precisa de throttle (sleep 500ms) e/ou limite de SKIPs consecutivos.
3. **OOA detection incompleta** -- NexusLauncher nao eh detectado como OOA em blippex/translator, desperdicando ~30% do tempo.
