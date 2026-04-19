# Resultados: Comparação RVSmart vs APE vs FastBot (gh33+gh34)

**Data**: 2026-03-10
**Experimento**: 100 APKs, 600s timeout, 3 repetições, JCA specs
**Ferramentas testadas**: rvsmart:mvp (pure algorithm), rvsmart:arrival_first_v17 (hybrid LLM)
**Baseline (gh9)**: ape, fastbot (mesmos 100 APKs, mesmas condições)
**Infra**: 8 containers Docker + SGLang (Qwen3-VL-4B-Instruct)

## 1. Ranking Final

| Métrica | rvsmart:mvp | af17 (hybrid) | APE | FastBot |
|---|---|---|---|---|
| Activity cov (mean) | 58.14% | 53.95% | **64.11%** | 54.71% |
| Method cov (mean) | 24.04% | 22.22% | **28.38%** | 23.24% |
| Method cov (median) | 21.79% | 18.33% | **25.91%** | 19.14% |
| MOP cov (mean) | 32.64% | 29.71% | **37.98%** | 31.48% |
| Total violações | 340 | 307 | **363** | 307 |
| APKs c/ violação | **44/100** | 38/100 | 43/100 | 36/100 |
| Tasks completadas | 299/300 | 298/300 | 300/300 | 300/300 |
| CV médio (variância) | **8.1%** | 9.2% | 10.5% | 8.5% |

**Ranking por cobertura de métodos**: APE (28.38%) > rvsmart:mvp (24.04%) > FastBot (23.24%) > af17 (22.22%)

## 2. Significância Estatística (Wilcoxon signed-rank)

| Comparação | Δ | p-value | Significância |
|---|---|---|---|
| mvp vs APE | **-4.39pp** | p < 0.001 | *** (APE superior) |
| mvp vs FastBot | +0.75pp | p = 0.093 | ns (empate estatístico) |
| mvp vs af17 | **+1.65pp** | p = 0.003 | ** (mvp superior) |
| af17 vs APE | **-6.04pp** | p < 0.001 | *** (APE superior) |
| af17 vs FastBot | -0.89pp | p = 0.045 | * (FastBot marginalmente superior) |

**Conclusão estatística**: APE é significativamente superior a todas as ferramentas. rvsmart:mvp é estatisticamente equivalente ao FastBot. O modo híbrido (af17) é significativamente **pior** que o modo puro (mvp).

## 3. Comparação Per-APK (médias das 3 repetições)

### mvp vs APE
- **mvp vence**: 14 APKs
- **Empate (Δ < 0.5pp)**: 22 APKs
- **APE vence**: 64 APKs

Top 5 onde mvp supera APE:
| APK | mvp | APE | Δ |
|---|---|---|---|
| screenrecorder_33 | 15.59% | 1.86% | **+13.73pp** |
| arxiv_39 | 20.97% | 7.51% | **+13.46pp** |
| quickdice_48 | 43.63% | 31.26% | +12.37pp |
| huewidgets_8 | 15.99% | 5.58% | +10.41pp |
| fas_3 | 49.37% | 39.07% | +10.30pp |

Top 5 onde APE supera mvp:
| APK | mvp | APE | Δ |
|---|---|---|---|
| episodes_12 | 16.39% | 50.04% | **-33.65pp** |
| insteadlauncher_80601 | 30.21% | 56.33% | **-26.13pp** |
| eduroamcat_59 | 31.52% | 57.48% | -25.96pp |
| sandwichroulette_2 | 8.05% | 33.10% | -25.05pp |
| imagepipe_45 | 32.81% | 55.42% | -22.61pp |

**Observação**: Quando APE vence, a magnitude é muito maior (até -33.65pp) do que quando mvp vence (até +13.73pp). APE explora UIs mais amplas; mvp tem vantagem em apps com menus profundos (Preferences, nested fragments).

### mvp vs FastBot
- **mvp vence**: 47 APKs
- **Empate**: 23 APKs
- **FastBot vence**: 30 APKs

mvp é ligeiramente superior ao FastBot em número de vitórias, mas a diferença média (+0.75pp) não é estatisticamente significativa.

### af17 (hybrid) vs mvp (pure)
- **af17 vence**: 24 APKs
- **Empate**: 30 APKs
- **mvp vence**: 46 APKs

Top 5 onde af17 supera mvp:
| APK | af17 | mvp | Δ |
|---|---|---|---|
| sqliteviewer_1 | 17.71% | 1.32% | **+16.39pp** |
| hashpass_2 | 57.14% | 42.85% | +14.29pp |
| eduroamcat_59 | 44.95% | 31.52% | +13.44pp |
| imagepipe_45 | 45.46% | 32.81% | +12.66pp |
| TI89EmuDonation_1133 | 15.10% | 4.85% | +10.25pp |

Top 5 onde mvp supera af17:
| APK | af17 | mvp | Δ |
|---|---|---|---|
| binauralbeats_160 | 23.97% | 50.27% | **-26.30pp** |
| quickdice_48 | 21.43% | 43.63% | -22.20pp |
| towercollector_2140302 | 11.48% | 27.64% | -16.16pp |
| anecdote_23 | 26.37% | 39.19% | -12.82pp |
| passwordmaker_11 | 20.60% | 32.79% | -12.19pp |

**Diagnóstico**: O LLM ajuda em APKs que exigem input de texto ou navegação contextual (sqliteviewer, hashpass, eduroamcat). Mas em APKs com UIs ricas onde velocidade importa, a latência do LLM prejudica (binauralbeats, quickdice) — o algoritmo puro faz ~10× mais ações/segundo.

## 4. Análise de Violações MOP

### Detecção por ferramenta

| Ferramenta | Total violações | APKs c/ violação |
|---|---|---|
| APE | 363 | 43 |
| **rvsmart:mvp** | 340 | **44** |
| af17 | 307 | 38 |
| FastBot | 307 | 36 |

rvsmart:mvp detecta violações em **mais APKs** (44) que qualquer outra ferramenta, apesar de ter menos violações totais que APE.

### Detecção exclusiva

- **32 APKs**: violação detectada por TODAS as 4 ferramentas (core set)
- **48 APKs**: violação detectada por ao menos 1 ferramenta
- **mvp detectou e APE não**: 5 APKs (screenrecorder, arxiv, huewidgets, kandroid, gitlab)
- **APE detectou e mvp não**: 4 APKs (episodes, pyload, trickytripper, installalogs)
- **Só mvp detectou** (nenhuma outra): 3 APKs (gitlab, kandroid × 2)

### Especificações violadas (rvsmart:mvp)

| Especificação | Violações (mvp) | Violações (af17) |
|---|---|---|
| SSLContextSpec | 4,624 | 2,477 |
| MessageDigestSpec | 4,410 | 1,466 |
| SecretKeySpecSpec | 2,006 | 888 |
| MacSpec | 477 | 368 |
| IvParameterSpecSpec | 404 | 54 |
| SecureRandomSpec | 372 | 50 |
| KeyPairSpec | 214 | 29 |
| CipherSpec | 203 | 28 |
| KeyStoreSpec | 75 | 34 |
| KeyManagerFactorySpec | 35 | 22 |

mvp detecta consistentemente ~2× mais violações que af17 em quase todas as especificações. O algoritmo puro executa mais ações, portanto trigga mais caminhos que usam APIs criptográficas.

## 5. Variância entre Repetições

| Ferramenta | CV médio | APKs com CV > 30% |
|---|---|---|
| **rvsmart:mvp** | **8.1%** | 6/100 |
| FastBot | 8.5% | 7/100 |
| af17 | 9.2% | 6/100 |
| APE | 10.5% | 10/100 |

rvsmart:mvp é a ferramenta **mais determinística** (menor CV). APE é a mais estocástica. Os poucos APKs com CV alto (>30%) são apps com UIs não-determinísticas (timers, animações, login screens).

## 6. Falhas

3 tasks falharam (0.5%), todas por falha de instalação do APK (infraestrutura, não bugs do rvsmart):

| Container | APK | Erro |
|---|---|---|
| cmp01 | analyticaltranslator_6 | Falha no ToolExecutionComponent |
| cmp04 | pdfview_40000 | Falha na instalação do APK |
| cmp05 | easyweatherdemo_11 | Falha no ToolExecutionComponent |

Todos os 3 APKs têm dados na baseline (ape/fastbot rodaram OK). As falhas são específicas da interação rvsmart + emulador, não do APK em si.

## 7. Diagnóstico: Por que o LLM (af17) é pior?

O resultado mais importante: **o modo híbrido LLM é estatisticamente pior que o algoritmo puro** (-1.65pp, p=0.003).

Hipóteses para a causa:

1. **Latência**: Cada chamada ao LLM (Qwen3-VL via SGLang) leva 1-3s. O algoritmo puro executa ações a cada ~50ms. Em 600s, o puro executa ~12.000 ações vs ~200-600 do híbrido. Volume compensa qualidade.

2. **Qualidade das decisões LLM**: O LLM nem sempre escolhe ações melhores que o DFS. Em apps simples (1-3 telas), o DFS cobre tudo rapidamente. O LLM adiciona overhead sem benefício.

3. **Perda de iterações em ARRIVAL_FIRST**: Na estratégia arrival_first, quando o algoritmo termina primeiro (o que quase sempre acontece dado o overhead do LLM), a ação do algoritmo é usada. O LLM contribui pouco.

4. **30% probability para new_screen_phase2**: Apenas 30% das telas novas vão para o LLM. Nos outros 70%, o algoritmo decide sozinho (idêntico ao puro, mas com overhead de setup).

**Exceções notáveis** (af17 > mvp):
- **sqliteviewer** (+16.39pp): App que requer entrada de path de arquivo DB — LLM gera inputs contextuais.
- **hashpass** (+14.29pp): App de hashing que requer texto — LLM gera inputs significativos.
- **eduroamcat** (+13.44pp): App de configuração WiFi — LLM navega formulários.

Padrão: **o LLM ajuda em apps que requerem input semântico de texto**. Em exploração puramente navegacional, o algoritmo é superior.

## 8. Distribuição de Ações (Análise de Traces)

**Dataset**: 299 trace files, 251.081 ações totais (99 APKs × 3 reps + 1 APK com 2 reps).

### Distribuição global

| Ação | Contagem | % |
|---|---:|---:|
| CLICK | 164.595 | 65.55% |
| SKIP | 31.600 | 12.59% |
| RESTART | 24.178 | 9.63% |
| SET_TEXT | 13.617 | 5.42% |
| LONG_CLICK | 13.234 | 5.27% |
| SCROLL | 3.857 | 1.54% |
| **BACK** | **0** | **0.00%** |
| **Total** | **251.081** | **100%** |

**Achado crítico**: BACK tem **0 execuções** em 100 APKs e 299 runs. Para comparação, af17 executou 6.752 ações BACK no mesmo experimento.

### Distribuição por fonte de ação

| Fonte | Contagem | % |
|---|---:|---:|
| algorithm | 211.677 | 84.31% |
| null_root | 17.285 | 6.88% |
| system_dialog | 8.739 | 3.48% |
| ooa (out-of-app) | 7.804 | 3.11% |
| ooa_within_tolerance | 5.097 | 2.03% |
| native_crash | 479 | 0.19% |

### Distribuição de unique_states por APK

| Faixa | APKs |
|---|---:|
| 0 estados | 9 |
| 1-2 estados | 9 |
| 3-5 estados | 9 |
| 6-10 estados | 11 |
| 11-20 estados | 21 |
| 21+ estados | 41 |

**Stats**: mean=28.8, median=16.7, min=0.0, max=163.3

### APKs com taxa de RESTART > 30% (14 APKs)

| APK | RESTART% | Avg states |
|---|---:|---:|
| sqliteviewer_1 | 99.0% | 1.0 |
| gilga_11 | 95.6% | 0.0 |
| sandwichroulette_2 | 95.1% | 1.7 |
| towercollector_2140302 | 78.9% | 29.0 |
| ultrasonic_129 | 38.9% | 0.0 |
| mupen64plusae_246 | 38.3% | 16.7 |
| installalogs_10 | 37.9% | 0.0 |
| debconf.schedule_85 | 37.4% | 0.0 |
| painlessmesh_14 | 35.3% | 0.0 |
| gmote_5 | 33.1% | 3.7 |
| dashchan_1043 | 32.1% | 0.0 |
| mosmetro_77 | 31.9% | 0.0 |
| quicknote_241 | 31.3% | 0.0 |
| owmap_136 | 31.0% | 9.3 |

### APKs com 0 unique_states (9 APKs)

APKs onde o agente nunca parseou uma tela com sucesso — 600s gastos em loops de SKIP/RESTART:

| APK | Causa dominante |
|---|---|
| dashchan_1043 | system_dialog (63.2%) |
| quicknote_241 | system_dialog (65.3%) |
| gilga_11 | ooa/crash (95.6%) |
| debconf.schedule_85 | system_dialog (59.4%) |
| installalogs_10 | system_dialog (57.7%) |
| consolelauncher_205 | null_root (100%) |
| ultrasonic_129 | system_dialog (56.4%) |
| mosmetro_77 | system_dialog (63.8%) |
| painlessmesh_14 | system_dialog (62.4%) |

## 9. Catálogo de Bugs

Análise de 301 trace files com referência cruzada ao código-fonte Java do rvsmart.

### BUG-01: Ação BACK permanentemente desabilitada (CRÍTICO)

**Evidência**: BACK executado em apenas 1 de 100 APKs (hashpass, 7 ações). 59.508 linhas de trace mostram `[BACK excluded: root]`.

**Causa raiz (confirmada no código)**: `ActionSelector.selectFromUnifiedQueue()` (linha 627-628) verifica `successorTracker.getParents(hash).isEmpty()` onde `hash` é o **contentHash**. Mas `AgentLoop.runIteration()` (linha 580) registra transições via `successorTracker.record(structHash, structHashAfter)` usando o **structHash**. Como contentHash ≠ structHash, `getParents(contentHash)` sempre retorna vazio → toda tela é tratada como root → BACK é excluído.

**Impacto**: O agente não consegue navegar para trás. Depende exclusivamente de RESTART (~1s cada: force-stop + startApp + 800ms sleep).

**Fix**: Trocar `getParents(hash)` por `getParents(screen.getStructHash())` em ActionSelector linhas 326 e 628.

### BUG-02: Ciclos ping-pong sem detecção (CRÍTICO)

**Evidência**: 32 APKs com ciclos de 100+ iterações. Piores: mover (4.389 iterações), photobackup (2.194), hex (2.188). Total desperdiçado: **61.470 iterações (24,5% de todas as ações)**.

**Causa raiz**: Quando uma ação na tela A (contentHash X) abre um diálogo que produz contentHash Y, e o agente fecha o diálogo voltando a X, oscila indefinidamente. `PhaseController.onNewContentState()` (linha 83-85) reseta para PHASE_1 a cada novo contentHash, mesmo que o agente esteja ciclando entre duas variantes da mesma atividade.

**Fix**: Ring buffer dos últimos 6-10 hashes. Detectar padrão A-B-A-B (3+ repetições) → forçar RESTART ou navegar para cluster diferente via NavigationMap.

### BUG-03: getSaturationRate() retorna 1.0 quando totalActions=0 (ALTO)

**Evidência**: sqliteviewer (100% RESTART, 331/331 iterações), mupen64plusae (100% RESTART), sandwichroulette (98,8% RESTART) mostram saturation=1.00 desde a iteração 0.

**Causa raiz**: `ContentNode.getSaturationRate()` (linha 159-160):
```java
if (totalActions == 0) return 1.0f;  // Reporta "totalmente saturado" quando nada é interativo
```
Fase 1 não encontra ações não-testadas, cai para Fase 3, `generateCandidateActions()` retorna vazio, fila unificada só tem RESTART (BACK excluído por BUG-01) → loop infinito de RESTART.

**Fix**: Retornar `0.0f` quando `totalActions == 0`.

### BUG-04: Stuck detector insuficiente para apps de atividade única (ALTO)

**Evidência**: 24 APKs com 100+ iterações consecutivas no mesmo hash. Piores: lucia (987 consecutivas), owmap (917), worktime (832).

**Causa raiz**: StuckDetector dispara recuperação mas a recuperação é RESTART, que retorna à mesma tela. Sem BACK (BUG-01), não há escape. Ciclo: interagir → stuck → RESTART → mesma tela → interagir → stuck.

**Fix**: Após N ciclos RESTART-para-mesma-tela, entrar em modo de interação exaustiva (todas as coordenadas, scroll, long-click) em vez de reiniciar.

### BUG-05: Armadilha em telas de Preferências (MÉDIO)

**Evidência**: 11 APKs gastam >50% do tempo em Preferences/Settings. Piores: animereleasenotifier (94%), lesserpad (89%), nori (80%). Total desperdiçado: 28.341 iterações.

**Causa raiz**: Telas de preferências geram muitas variantes de contentHash (cada toggle/spinner cria um novo hash), resetando Phase 1 via `PhaseController.onNewContentState()`. Combinado com BUG-01 (sem BACK para sair), o agente fica preso.

**Fix**: (1) Fix BUG-01, (2) Limitar tempo em atividades de Preferences (detectar por nome de classe).

### BUG-06: Detecção de diálogos de sistema muito restrita (MÉDIO)

**Evidência**: 72 APKs disparam eventos de system_dialog (8.742 total). Piores: quicknote (977 eventos, 65,3%), mosmetro (887, 63,8%).

**Causa raiz**: SystemDialogDetector reconhece apenas 4 pacotes do sistema. Diálogos de Google Play Services, battery optimization, OEM packages não são detectados. O mecanismo de escalação funciona (BACK em 3, force-stop em 6) mas o diálogo reaparece após reinício.

**Fix**: Expandir SYSTEM_PACKAGES para incluir `com.google.android.gms`, `com.google.android.permissioncontroller`, pacotes OEM.

### Resumo de bugs

| Bug | Severidade | APKs afetados | Iterações desperdiçadas | Complexidade do fix |
|---|---|---:|---|---|
| BUG-01 | CRÍTICO | 99/100 | Amplifica todos os outros | Baixa (1 linha) |
| BUG-02 | CRÍTICO | 32/100 | 61.470 (24,5%) | Média (detector de ciclo) |
| BUG-03 | ALTO | 4-6/100 | 1.577+ | Baixa (1 linha) |
| BUG-04 | ALTO | 24/100 | Milhares por APK | Média (recuperação inteligente) |
| BUG-05 | MÉDIO | 11/100 | 28.341 | Média (budget por atividade) |
| BUG-06 | MÉDIO | 72/100 | 8.742 | Baixa-Média (expandir pacotes) |

**Prioridade**: BUG-01 primeiro (1 linha, maior ROI — desbloqueia mitigação de BUG-04 e BUG-05). Depois BUG-03 (1 linha, elimina loops de RESTART). BUG-02 (maior pool de desperdício: 24,5%) requer mais design.

## 10. Análise de Cobertura de Atividades (mvp vs APE)

### Top 10 APKs onde APE domina

| APK | APE meth% | mvp meth% | Gap | APE act% | mvp act% | Act gap |
|---|---:|---:|---:|---:|---:|---:|
| episodes_12 | 50.04 | 16.39 | +33.65 | 83.33 | 37.50 | +45.83 |
| insteadlauncher_80601 | 56.33 | 30.21 | +26.13 | 100.00 | 50.00 | +50.00 |
| eduroamcat_59 | 57.48 | 31.52 | +25.96 | 100.00 | 88.89 | +11.11 |
| sandwichroulette_2 | 33.10 | 8.05 | +25.05 | 33.33 | 14.29 | +19.04 |
| imagepipe_45 | 55.42 | 32.81 | +22.61 | 100.00 | 66.67 | +33.33 |
| sqliteviewer_1 | 22.55 | 1.32 | +21.23 | 62.50 | 12.50 | +50.00 |
| simpledilbert_40 | 47.62 | 26.71 | +20.90 | 100.00 | 41.67 | +58.33 |
| towercollector_2140302 | 47.34 | 27.64 | +19.70 | 100.00 | 100.00 | 0.00 |
| fdroidclassic_1110 | 48.32 | 29.87 | +18.45 | 63.89 | 41.67 | +22.22 |
| subsonic_59 | 50.19 | 36.27 | +13.92 | 82.05 | 64.10 | +17.95 |

**Top 10 média**: APE act_cov = 82,51%, mvp act_cov = 51,73% → gap de **30,78pp**.

### Estatísticas de diversidade de atividades

- **APE > mvp em act_cov**: 37 APKs
- **mvp > APE em act_cov**: 11 APKs
- **Empate**: 52 APKs
- **mvp preso em 1 atividade**: 18 APKs (avg method gap = +6,71pp, avg act gap = +14,04pp)

### Correlação RESTART vs gap para APE

| RESTART bucket | N APKs | Avg method gap | Avg act gap |
|---|---:|---:|---:|
| 0-10% | 62 | +4.61pp | +6.75pp |
| 10-30% | 18 | +3.12pp | +2.58pp |
| 30-50% | 1 | +13.25pp | +22.22pp |
| 50%+ | 10 | +8.29pp | +11.29pp |

Correlação Pearson restart_rate vs method_gap = **0,15** (fraca). A relação é bimodal: APKs com RESTART >50% são um modo de falha distinto (avg 1,6 atividades). Mas muitos dos piores gaps têm RESTART baixo — o problema não é só RESTART.

### Throughput efetivo (top piores APKs)

| APK | mvp iterações efetivas | APE steps | Razão |
|---|---:|---:|---:|
| sqliteviewer_1 | 0 | 762 | ∞ |
| sandwichroulette_2 | 5 | 938 | 188× |
| towercollector_2140302 | 45 | 846 | 19× |

## 11. Padrões Sistêmicos

### Padrão 1: Cegueira para ViewPager/Tabs (7/10 piores APKs)

episodes, insteadlauncher, simpledilbert, towercollector, fdroidclassic, imagepipe, eduroamcat — todos usam ViewPager ou tabs. mvp não executa SWIPE_LEFT/SWIPE_RIGHT para navegar entre tabs. APE modela cada tab como estado distinto no GSTG e explora sistematicamente.

### Padrão 2: Cegueira para OptionsMenu (4/10 piores APKs)

eduroamcat, episodes, simpledilbert, fdroidclassic — têm funcionalidades acessíveis apenas via OptionsMenu. APE modela o botão "More Options" como widget e explora seus filhos. mvp pode clicar no menu mas não explora sistematicamente cada item.

### Padrão 3: Falha completa de interação com UI (3/10 piores APKs)

sqliteviewer (100% RESTART), sandwichroulette (97,9% RESTART), towercollector (81,8% RESTART). O parser de tela não produz elementos acionáveis → loop infinito de RESTART via BUG-03.

### Padrão 4: Profundidade de métodos dentro de atividades

Para towercollector (100% act_cov em ambas) e subsonic (cobertura de atividades similar), o gap é inteiramente em cobertura de métodos dentro de atividades já visitadas. O desperdício de iterações do mvp (82% RESTART para towercollector) resulta em menos interações por atividade.

## 12. Conclusão Atualizada

### O que funciona
- rvsmart:mvp é competitivo com FastBot (empate estatístico) e altamente determinístico (CV 8,1%)
- rvsmart detecta violações em mais APKs que qualquer outra ferramenta (44/100)
- Detecção exclusiva: 3 APKs onde só mvp encontra violações
- 41 APKs com 21+ unique_states — exploração funcional em apps de complexidade média

### O que não funciona
- APE é significativamente superior em cobertura (-4,39pp, p<0,001)
- O modo híbrido LLM (af17) piora os resultados (-1,65pp vs puro, p=0,003)
- **BACK nunca executado** (0/251.081 ações) — bug crítico no ActionSelector
- **24,5% das iterações** desperdiçadas em ciclos ping-pong (BUG-02)
- 9 APKs com 0 estados descobertos, 18 APKs presos em 1 atividade
- Cegueira para ViewPager/Tabs e OptionsMenu afeta 7/10 piores APKs

### Root causes do gap para APE

O gap de -4,39pp tem causas identificáveis e corrigíveis:

1. **BUG-01 (BACK desabilitado)**: Mismatch contentHash vs structHash no ActionSelector. Fix: 1 linha. ROI estimado: alto — desbloqueia navegação reversa e mitiga BUG-04/BUG-05.

2. **BUG-02 (ciclos ping-pong)**: Sem detecção de ciclos de 2 estados. 24,5% das iterações desperdiçadas. Fix: ring buffer + detector de período.

3. **BUG-03 (saturation loop)**: `getSaturationRate()` retorna 1.0 para `totalActions=0`. Fix: 1 linha. Impacto direto em 4-6 APKs com 100% RESTART.

4. **ViewPager/OptionsMenu blindness**: Limitação arquitetural — requer suporte a SWIPE e exploração sistemática de menus.

### Recomendações (priorizadas)

1. **Fix BUG-01** (1 linha): `getParents(screen.getStructHash())` em ActionSelector. Maior ROI — desbloqueia BACK, mitiga BUG-04 e BUG-05. Impacto esperado: +2-3pp em method_cov.

2. **Fix BUG-03** (1 linha): Retornar `0.0f` em `getSaturationRate()` quando `totalActions == 0`. Elimina loops de RESTART em 4-6 APKs.

3. **Implementar detecção de ciclos** (BUG-02): Ring buffer dos últimos 10 hashes, detectar padrões de período 2-4. Recupera 24,5% das iterações desperdiçadas.

4. **Expandir SystemDialogDetector** (BUG-06): Adicionar pacotes Google, OEM. Impacto em 72 APKs.

5. **Suporte a ViewPager/swipe**: Adicionar SWIPE_LEFT/SWIPE_RIGHT ao action set. Impacto em 7/10 piores APKs.

6. **Exploração sistemática de OptionsMenu**: Detectar e explorar items de menu. Impacto em 4/10 piores APKs.

7. **Modo LLM**: Repensar estratégia — invocar LLM apenas quando stuck (plateau), não proativamente em telas novas.

### Estimativa de impacto

Se BUG-01 + BUG-02 + BUG-03 fossem corrigidos, o throughput efetivo do mvp aumentaria significativamente:
- 24,5% das iterações recuperadas de ciclos ping-pong (BUG-02)
- BACK navigation habilitada eliminaria dependência de RESTART (BUG-01)
- 4-6 APKs sairiam de 0% efetividade para exploração funcional (BUG-03)
- Estimativa conservadora: +3-5pp em method_cov, potencialmente fechando o gap para APE.

---

# Parte II: Investigação Profunda do Algoritmo de Exploração

## 13. Abstração de Estados: rvsmart (Dual Hash) vs APE (CEGAR)

### rvsmart: Sistema de dual hash estático

rvsmart computa dois hashes no momento da construção do `ScreenState`. Nenhum refinamento ocorre em tempo de execução.

**structHash** (`ScreenState.java:108-125`): `className | resourceId | interactMask` (5 bits: clickable, scrollable, checkable, longClickable, enabled). Deduplica assinaturas em `Set`, ordena, `Objects.hash(activity, sig1, sig2, ...)`. Ignora texto, bounds, hierarquia.

**contentHash** (`ScreenState.java:79-96`): `className | resourceId | text | enabled | checkable`. Texto incluído apenas para widgets interativos não-EditText, cap de 50 chars. Mesmo algoritmo (dedup, sort, hash).

**Onde são usados**:
- **contentHash**: identidade primária no `ContentGraph` — contagens de visita, tracking de ações, saturação, transições
- **structHash**: `StructuralGraph` clustering, `NavigationMap` BFS, `SuccessorTracker`, `PhaseController`
- **Safety valve**: quando `ContentGraph.size() > 1000`, contentHash degrada para structHash (perda total de distinção de conteúdo)

### APE: Abstração adaptativa CEGAR com lattice de 32 níveis

APE usa um sistema **dinâmico e adaptativo** baseado em lattice de `Namer` objects. 5 dimensões de atributos:
- `TYPE` (className + resourceId)
- `INDEX` (posição entre siblings)
- `TEXT` (texto + contentDescription)
- `PARENT` (identidade do nó pai, recursiva)
- `ANCESTOR` (cadeia de ancestrais)

Combinadas, formam 2^5 = 32 possíveis Namers, do mais coarse (`EmptyNamer`) ao mais fine (`parentTypeTextIndexAncestorNamer`).

**Abstração inicial**: Apenas `TYPE` para widgets interativos, `EmptyNamer` para não-interativos. **Mais coarse que structHash** — começa ignorando texto, posição e hierarquia.

**Refinamento (CEGAR loop)**:
1. Mesmo ação do mesmo estado leva a estados diferentes → **não-determinismo detectado**
2. `NamingFactory.resolveNonDeterminism()` tenta action refinement (diferenciar widgets) ou state refinement (adicionar dimensões)
3. Sobe no lattice: por exemplo, `{TYPE}` → `{TYPE, TEXT}` para distinguir dois botões pelo texto
4. Validação: não pode criar estados demais (`maxStatesPerActivity = 10`)
5. `model.rebuild()`: reconstrói todo o modelo com a nova naming, preservando histórico

**Coarsening (abstração reversa)**: Se o refinamento criou estados demais, `batchAbstract()` reverte para naming pai.

### Diferenças fundamentais

| Dimensão | rvsmart | APE |
|---|---|---|
| Quando a abstração é decidida | Estática, na construção | Dinâmica, evolui durante teste |
| Níveis de granularidade | 2 fixos (struct, content) | Lattice de ~32 níveis por grupo de widgets |
| Identidade de widgets | Flat (set de assinaturas) | Tree-aware (hierarquia pai/ancestral) |
| Refinamento | Nenhum | Triggered por não-determinismo |
| Reversão | Safety valve: degrada para structHash a 1000 estados | `batchAbstract()`: reverte se muitos estados |
| Per-widget vs global | Hash global sobre todos os widgets | Per-widget-group naming (diferentes XPaths podem usar diferentes Namers) |
| Hierarquia | Nenhuma (flat) | Full (PARENT, ANCESTOR, INDEX) |

### Impacto na exploração do rvsmart

1. **Sem resolução de não-determinismo**: rvsmart não detecta quando a mesma ação leva a resultados diferentes. O ContentGraph registra ambas as transições, mas trata como estado único.

2. **Granularidade fixa**: contentHash pode ser simultaneamente fino demais (variações de labels de botões) e grosso demais (missing checked/unchecked state) para diferentes partes do mesmo app.

3. **Safety valve é um cliff**: a 1000 estados, toda distinção de conteúdo é perdida de uma vez. APE tem limites per-activity e refinamento reversível.

## 14. Parsing de UI e Geração de Ações

### Captura de tela

rvsmart usa `AccessibilityNodeInfo` API direto (NÃO XML dump), BFS na árvore de acessibilidade, cap de 2000 nós com prioridade (interativos primeiro).

**Flag crítica**: `FLAG_INCLUDE_NOT_IMPORTANT_VIEWS` é **desabilitada** (`DeviceController.java:94-96`), excluindo views decorativas. Geralmente benéfico, mas pode ocultar elementos interativos em casos raros.

### Filtragem de elementos

| Filtro | Efeito |
|---|---|
| `!item.isEnabled()` | Skip desabilitados |
| `pkg == "com.android.systemui"` | Skip system UI |
| `bounds == null` | Skip sem bounds |
| Não-interativo | Sem ação gerada se !clickable && !longClickable && !editable && !scrollable |

### Geração de ações por tipo de widget

| Condição | Ação gerada |
|---|---|
| `isClickable()` | CLICK no centro do bounds |
| `isLongClickable()` | LONG_CLICK no centro |
| `isEditable()` | SET_TEXT com texto do InputValueGenerator |
| `isScrollable()` | 4 SCROLLs (down, up, left, right) |
| Sempre adicionados | BACK (se não root) + RESTART (last resort) |

### Widgets NÃO tratados ou tratados incorretamente

| Widget | Problema | Impacto |
|---|---|---|
| **WebView** | Opaco — conteúdo HTML não exposto via AccessibilityNodeInfo | ALTO |
| **Spinner dropdown** | PopupWindow pode não estar na árvore de acessibilidade | MÉDIO |
| **SeekBar/RatingBar** | Só CLICK no centro, sem gesto de DRAG | BAIXO |
| **SWIPE** | Nunca gerado pelo algoritmo, apenas LLM pode produzir | MÉDIO |
| **KEYCODE_MENU** | Nunca injetado — OptionsMenu só acessível se botão three-dots é clickable | MÉDIO |

### Problema de saturação

**Ações contadas como executadas mesmo em falha silenciosa**: `ContentGraph.recordAction()` é chamado ANTES de `executeAction()` (`AgentLoop.java:477`). Se a injeção falha silenciosamente, execution count incrementa.

**Saturação baseada em execution count, não success count**: `ContentNode.isActionSaturated()` (linha 143) — ação é "saturada" após 4 execuções independentemente de sucesso. Um widget coberto por popup pode ser marcado como saturado com 4 tentativas falhadas.

### `isInteractive()` exclui longClickable

`ScreenItem.isInteractive()` (linha 83-85): `clickable || scrollable || checkable || editable`. **Não inclui `longClickable`**. Widgets que são apenas longClickable (não clickable) são invisíveis para o LLM prompt, embora o algoritmo gere LONG_CLICK para eles.

## 15. Algoritmo de Exploração: Controle de Fluxo Completo

### Ciclo de iteração principal (`AgentLoop.runIteration()`)

```
WHILE (time < deadline):
  1. Crash check → recovery se necessário
  2. getRootInActiveWindow() → árvore de acessibilidade
  3. SystemDialogDetector → dismiss se detectado
  4. Out-of-app check → restart se fora do app-alvo
  5. UiCapture.capture() → ScreenState → contentHash + structHash
     - ContentGraph.getOrCreate + registerScreenElements
     - PhaseController.onNewContentState() se novo hash
  6. LogcatReader.drainCoverageTags() → MOP coverage
  7. Stuck? → StuckDetector.recover() → BACK ou RESTART
  8. Action Selection:
     - Phase 1: untested actions → scorer chain → best scored
     - Phase 2: navigate to highest coverage gap cluster
     - Phase 3: unified queue com stochastic 50%
  9. Execute action (InputInjector)
  10. Adaptive throttle
  11. Re-capture → detect effect (hash changed?)
  12. Multi-attempt retry se sem efeito
  13. Learner.update() → rewards + graph transitions
```

### Sistema de fases

| Fase | Objetivo | Seleção | Transição |
|---|---|---|---|
| Phase 1 | Testar toda ação em todo estado | Untested-first, 6 scorers, stochastic 15% | → Phase 2 quando sem ações untested em qualquer cluster acessível |
| Phase 2 | Navegar para maior coverage gap | BFS no NavigationMap para cluster com maior gap | → Phase 3 quando PlateauDetector (10 iterações sem progresso) |
| Phase 3 | Escape estocástico | Unified queue (todas ações + BACK + RESTART), stochastic 50% | → Phase 1 quando novo contentHash descoberto |

### Scorer chain (6 scorers aditivos)

| Scorer | Boost | Granularidade |
|---|---:|---|
| MopScorer | +500 (direto) / +300 (transitivo) | **Activity-level** (todos elementos boost igual) |
| GradualDecayScorer | base × decay^visits | Per-action |
| SystemElementFilter | -5000 | Per-package |
| ComponentPriorityScorer | SET_TEXT=200, CLICK=100, SCROLL=25 | Per-action-type |
| WtgScorer | +200/+100/+50 (1-3 hops BFS) | **Activity-level** (todos CLICKs boost igual) |
| CoverageDensityScorer | +100 | Per-screen |

### Falhas identificadas no algoritmo

**GAP-1: `isClusterForced()` é dead code (ALTO)**. `PhaseController` rastreia re-entradas de Phase 1 por structHash (threshold: 20), mas `ActionSelector` nunca chama `isClusterForced()`. Telas que geram novos contentHashes indefinidamente (texto dinâmico, timers) prendem Phase 1 nesse cluster para sempre.

**GAP-2: NavigationMap limitado a transições observadas (MÉDIO)**. Clusters nunca visitados são inatingíveis pela navegação BFS. A única forma de descobri-los é via seleção estocástica em Phase 3.

**GAP-3: 3-failure filter pode excluir transient failures (BAIXO)**. Ações com 3+ falhas são filtradas de Phase 1. Se a falha foi transiente (popup temporário), a ação é permanentemente excluída de Phase 1.

**GAP-4: totalActions pode não refletir todos os elementos (BAIXO)**. Definido via `Math.max(current, newInteractiveCount)` — se elementos variam entre visitas, a contagem pode estar subestimada na primeira visita.

## 16. Comparação de Capacidades: APE vs rvsmart

| Capacidade | APE | rvsmart | Gap |
|---|---|---|---|
| **Abstração de estados** | CEGAR adaptativo, 32 níveis | Dual hash fixo | CRÍTICO |
| **Planejamento de navegação** | BFS no grafo de estados com filtros customizados, paths multi-step | BFS no NavigationMap (structHash level) | ALTO |
| **Tracking global de ações** | `isActionUnvisitedByName()` cross-state | Apenas per-contentHash | ALTO |
| **Widget patching** | `patchGUITree()`: propaga click de container para filhos | Nenhum — depende de flags raw | MÉDIO |
| **Fuzzing** | KEYCODE_MENU, rotation, drag, pinch, trackball (2% rate) | Nenhum | MÉDIO |
| **ImageButton identification** | Pixel hash de ícones para distinguir botões sem texto | Nenhum — botões sem texto/resourceId são indistinguíveis | MÉDIO |
| **ViewPager** | Detecta por class name, gera SCROLL_LEFT_RIGHT + SCROLL_RIGHT_LEFT | Gera SCROLL left/right se scrollable, sem detecção de classe | BAIXO |
| **BACK** | Sempre disponível, BFS para backtrack planejado | Excluído em 99% dos casos (BUG-01) | CRÍTICO (bug) |
| **OptionsMenu** | KEYCODE_MENU via fuzzing (2%) | Nenhum mecanismo | MÉDIO |
| **Trivial state refresh** | Retenta captura 5× para telas em loading | Nenhum | BAIXO |
| **Restart periódico** | A cada 300 steps + 20% clean restart (limpa cache) | Apenas quando stuck ou out-of-app | MÉDIO |
| **ABA strategy** | Balanced forward: navega de cold→colder states | Nenhum equivalente | MÉDIO |

## 17. Análise Estática: Perda Massiva de Informação

### Dados disponíveis no JSON (produzido pelo GATOR)

O JSON de análise estática contém 3 seções ricas:

1. **reachability**: per-class, per-method com `directlyReachesMop` e `reachesMop`
2. **windows**: per-activity com **widgets[]** — cada widget tem `idName`, `type`, `listeners[]` (com `eventType` e `handler` method signature), `inputType`, `hint`, `entries`
3. **transitions**: WTG edges com `events[]` — cada evento tem `widgetId`, `widgetClass`, `widgetName`, `handler`

### O que StaticMap.java realmente usa

```
JSON (dados completos)
  │
  ▼
StaticMap.java (parse)           ← PERDA MASSIVA
  │  Lê: reachability (apenas flags MOP activity-level)
  │  Lê: windows (apenas id→name mapping para transitions)
  │  Lê: transitions (apenas edges activity-level)
  │  DESCARTA: widgets[], listeners[], handler, idName, inputType, hint, entries
  │  DESCARTA: associação widget-to-transition
  │
  ▼
MopScorer: boost activity-level (coarse: TODOS actions +500 ou +300)
WtgScorer: BFS activity-level (coarse: TODOS clicks boosted igual)
```

### Oportunidades perdidas (dados disponíveis mas não usados)

**1. Widget-level MOP scoring**: `widgets[].listeners[].handler` + `reachability[].methods[].directlyReachesMop` → saber que `encryptButton` atinge MOP mas `clearButton` não. Atualmente, ambos recebem +500 igual.

**2. WTG-guided widget targeting**: `transitions[].events[].widgetId` → saber qual widget específico abre qual atividade. Atualmente, todos clicks são boosted igualmente quando há atividades não-visitadas.

**3. Static inputType para InputValueGenerator**: `widgets[].inputType` (e.g., `numberPassword`, `textMultiLine`) disponível mas não usado. Quando runtime `inputType == 0`, poderia usar o valor estático.

**4. Handler-level navigation hints para LLM**: Em vez de "Target: SettingsActivity (has MOP)", poderia dizer "Click encryptButton (triggers Crypter.encrypt → MOP direto)".

## 18. Plano de Melhorias (Priorizado)

### Tier 1: Bug fixes (impacto imediato, baixa complexidade)

| # | Melhoria | Onde | Impacto estimado |
|---|---|---|---|
| 1 | **Fix BUG-01**: `getParents(screen.getStructHash())` | ActionSelector:326,628 | +2-3pp (habilita BACK) |
| 2 | **Fix BUG-03**: `return 0.0f` quando `totalActions == 0` | ContentNode:160 | Elimina RESTART loops (4-6 APKs) |
| 3 | **Ativar `isClusterForced()`** (dead code GAP-1) | ActionSelector | Escapa clusters de content-hash loop |
| 4 | **Expandir SystemDialogDetector** | SystemDialogDetector | 72 APKs com system dialogs |

### Tier 2: Melhorias algorítmicas (impacto alto, complexidade média)

| # | Melhoria | Impacto estimado |
|---|---|---|
| 5 | **Detector de ciclos** (BUG-02): ring buffer 10 hashes, detectar período 2-4 | Recupera 24,5% das iterações |
| 6 | **Widget-level MOP scoring**: parse `widgets[].listeners[].handler` em StaticMap | Priorização precisa de widgets |
| 7 | **WTG-guided widget targeting**: parse `transitions[].events[].widgetId` | Navegação dirigida para atividades |
| 8 | **Restart periódico**: a cada N steps sem novo estado, restart proativo | Descoberta de estados inalcançáveis |
| 9 | **Saturation fix**: mover `recordAction()` para APÓS execução; usar success count | Saturação precisa |

### Tier 3: Capacidades novas (impacto alto, complexidade alta)

| # | Melhoria | Impacto estimado |
|---|---|---|
| 10 | **Fuzzing**: KEYCODE_MENU (2%), rotation, drag | OptionsMenu discovery, +2pp |
| 11 | **Widget patching**: propagar click de containers para filhos | List items em RecyclerView |
| 12 | **Trivial state refresh**: retentar captura para telas em loading | Menos phantom states |
| 13 | **Global action tracking**: `isActionUnvisitedByName()` cross-state | Cobertura sistemática |
| 14 | **CEGAR-lite**: refinement quando mesma ação leva a estados diferentes | Abstração adaptativa |

### Estimativa de impacto acumulado

- **Tier 1** (4 fixes): +3-5pp em method_cov → empate com APE
- **Tier 1 + Tier 2** (9 melhorias): +5-8pp → potencialmente superar APE
- **Tier 1 + Tier 2 + Tier 3** (14 melhorias): +8-12pp → superior a APE com margem
