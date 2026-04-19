# Validação do Experimento rvsmart:mvp vs ape (169 APKs)

**Data**: 2026-03-11
**Experimento**: rvsmart:mvp (pure algorithm) vs ape, 169 APKs, 3 repetições, 600s timeout, JCA specs
**Imagem Docker**: phtcosta/rvandroid:0.8.0
**Infraestrutura**: 10 containers (4 CPUs + 10 GB RAM cada), staggered delays 0-90s
**Duração**: ~18h (2026-03-10 14:28 → 2026-03-11 08:22)

---

## Área 1 — Resumo Executivo

### Completude

| Métrica | Valor |
|---------|-------|
| Total de tasks | 1014 |
| Completadas | 1010 (99.6%) |
| Falhas | 4 (0.4%) |
| APKs | 169 |
| Tools | 2 (rvsmart:mvp, ape) |
| Repetições | 3 |

### Métricas Agregadas por Ferramenta

| Métrica | rvsmart:mvp | ape | Diferença |
|---------|-------------|-----|-----------|
| **Method coverage (mean)** | **24.43%** | **27.75%** | **-3.31pp** |
| Method coverage (median) | 21.64% | 26.67% | -5.02pp |
| Method coverage (stdev) | 17.07 | 18.16 | — |
| Method coverage (max) | 66.67% | 75.00% | — |
| **Activity coverage (mean)** | **60.41%** | **62.58%** | **-2.16pp** |
| Activity coverage (median) | 60.00% | 64.10% | — |
| **MOP coverage (mean)** | **31.96%** | **36.99%** | **-5.03pp** |
| MOP coverage (median) | 27.29% | 35.00% | — |
| Total errors (sum) | 686 | 771 | -85 |
| Total method calls (sum) | 68,558 | 79,758 | -11,200 |

### Head-to-Head (threshold >2pp)

| Resultado | Method Cov | Activity Cov | MOP Cov |
|-----------|-----------|-------------|---------|
| rvsmart vence | 21 | 25 | 28 |
| ape vence | 77 | 45 | 85 |
| Empate | 71 | 99 | 56 |

### Distribuição das Diferenças (rvsmart - ape, method coverage)

| Faixa | Count |
|-------|-------|
| < -20pp | 9 |
| [-20, -10) | 17 |
| [-10, -5) | 22 |
| [-5, -1) | 44 |
| [-1, +1) (empate) | 51 |
| [+1, +5) | 14 |
| [+5, +10) | 5 |
| [+10, +20) | 6 |
| >= +20pp | 1 |

### Distribuição de Method Coverage

| Faixa | rvsmart:mvp | ape |
|-------|-------------|-----|
| >50% | 19 APKs | 25 APKs |
| >30% | 57 APKs | 75 APKs |
| >10% | 124 APKs | 134 APKs |
| =0% | 2 APKs | 2 APKs |

### Tempo de Execução

| Métrica | rvsmart:mvp | ape |
|---------|-------------|-----|
| n tasks | 506 | 504 |
| Mean | 671.8s | 662.8s |
| Median | 671.0s | 662.0s |
| Min | 655s | 648s |
| Max | 696s | 688s |
| Stdev | 6.9s | 6.4s |

### Top 10 APKs onde rvsmart vence ape

| APK | rvsmart | ape | diff |
|-----|---------|-----|------|
| git.rrgb.kinolog_11.apk | 40.4% | 17.7% | +22.7pp |
| org.asdtm.fas_3.apk | 53.5% | 35.8% | +17.7pp |
| com.orpheusdroid.screenrecorder_33.apk | 19.3% | 1.9% | +17.4pp |
| com.jlyr_41.apk | 29.5% | 15.0% | +14.5pp |
| com.reddyetwo.hashmypass.app_24.apk | 51.5% | 37.2% | +14.3pp |
| com.gbeatty.arxiv_39.apk | 21.0% | 9.1% | +11.8pp |
| com.blippex.app_5.apk | 46.0% | 35.4% | +10.6pp |
| ohm.quickdice_48.apk | 41.9% | 32.3% | +9.6pp |
| is.zi.huewidgets_8.apk | 14.9% | 5.6% | +9.3pp |
| net.sourceforge.subsonic.androidapp_59.apk | 43.7% | 35.4% | +8.3pp |

### Top 10 APKs onde ape vence rvsmart

| APK | rvsmart | ape | diff |
|-----|---------|-----|------|
| com.linuxcounter.lico_update_003_8.apk | 6.1% | 56.7% | -50.6pp |
| io.github.powerinside.syncplay_23.apk | 5.6% | 37.4% | -31.8pp |
| de.koelle.christian.trickytripper_25.apk | 22.6% | 50.9% | -28.3pp |
| byrne.utilities.hashpass_2.apk | 30.9% | 57.1% | -26.2pp |
| uk.ac.swansea.eduroamcat_59.apk | 32.8% | 58.2% | -25.4pp |
| org.jamienicol.episodes_12.apk | 16.4% | 39.9% | -23.5pp |
| com.mde.potdroid_82.apk | 16.9% | 37.9% | -21.0pp |
| re.jcg.playmusicexporter_110.apk | 2.9% | 23.4% | -20.6pp |
| jp.gr.java_conf.hatalab.mnv_40.apk | 20.8% | 41.3% | -20.5pp |
| net.fabiszewski.ulogger_309.apk | 20.5% | 38.9% | -18.5pp |

### Comparação com Baseline

**comparacao_v2 (100 APKs sobrepostos)**:

| Tool | Baseline | Atual | Delta |
|------|----------|-------|-------|
| rvsmart:mvp | 23.99% | 24.91% | +0.92pp |
| ape | 28.38% | 27.67% | -0.71pp |

**exp01 histórico (100 APKs sobrepostos, ape only, 300s timeout)**:

| | exp01 (300s) | Atual (600s) | Delta |
|-|-------------|-------------|-------|
| ape | 23.53% | 27.67% | +4.14pp |

---

## Área 2 — Bugs/Anomalias

### 2.1 Tasks Não Completadas

4 tasks falharam com `EmulatorError: Failed to start emulator RVSec` — falhas transientes de startup de emulador dentro dos containers Docker.

| Container | APK | Tool | Rep | Exec Time |
|-----------|-----|------|-----|-----------|
| exp_01 | com.example.root.analyticaltranslator_6.apk | rvsmart:mvp | 2 | 663s |
| exp_02 | com.quaap.launchtime_850.apk | ape | 3 | 125s |
| exp_05 | io.github.powerinside.syncplay_23.apk | ape | 1 | 660s |
| exp_07 | net.sf.andhsli.hotspotlogin_20.apk | ape | 2 | 510s |

Impacto mínimo: cada combinação APK/tool afetada ainda tem 2 reps válidas.

### 2.2 APKs com 0% de Cobertura (ambos os tools)

2 APKs têm 0% method coverage em todas as repetições para ambas as ferramentas:

| APK | rvsmart | ape | Act Coverage |
|-----|---------|-----|-------------|
| nz.gen.geek_central.ObjViewer_1.apk | 0.0% | 0.0% | 0% / 0% |
| tranquvis.simplesmsremote_140.apk | 0.0% | 0.0% | 0% / 0% |

Esses APKs provavelmente crasham no launch ou requerem permissões/setup especial.

### 2.3 Tempos de Execução

- **Nenhuma task com tempo < 100s** (exceto a falha de exp_02 com 125s que é um EmulatorError)
- **Nenhuma task com tempo > 700s**
- Faixa consistente: 648-696s (média ~667s = 600s timeout + ~67s overhead de boot/setup)

### 2.4 Anomalias de Execução

- **0 error_messages** em tasks completadas — todas as 1010 têm `error_message: null`
- Nenhum padrão de crash sistemático por APK
- 4 falhas são distribuídas uniformemente entre containers (1 por container afetado)

---

## Área 3 — Cobertura de Código

### 3.1 Violações MOP (JCA Specifications)

**80 de 169 APKs (47.3%)** tiveram pelo menos uma violação MOP detectada.

| Spec | Eventos | % do Total |
|------|---------|-----------|
| SSLContextSpec | 21,485 | 52.9% |
| MessageDigestSpec | 8,845 | 21.8% |
| SecretKeySpecSpec | 5,186 | 12.8% |
| CipherSpec | 1,735 | 4.3% |
| KeyStoreSpec | 1,085 | 2.7% |
| IvParameterSpecSpec | 630 | 1.6% |
| PBEKeySpec | 511 | 1.3% |
| MacSpec | 423 | 1.0% |
| SecureRandomSpec | 408 | 1.0% |
| KeyManagerFactorySpec | 136 | 0.3% |
| KeyPairSpec | 97 | 0.2% |
| TrustManagerFactorySpec | 42 | 0.1% |
| SignatureSpec | 18 | <0.1% |
| PBEParameterSpec | 14 | <0.1% |
| PBEKeySpecSpec | 7 | <0.1% |

**Cobertura de detecção por ferramenta**:

| Situação | Count |
|----------|-------|
| Ambos detectam | 68 APKs |
| Só rvsmart detecta | 3 APKs |
| Só ape detecta | 9 APKs |
| Nenhum detecta | 89 APKs |

Top APKs com mais violações (rvsmart): net.sf.andhsli.hotspotlogin_20 (4,710 eventos), org.mosad.seil0.projectlaogai_6000 (2,394), io.gresse.hugo.anecdote_23 (1,211).

### 3.2 Assimetria rvsmart vs ape

A assimetria é pronunciada:
- **7 APKs** onde rvsmart vence ape por >10pp
- **26 APKs** onde ape vence rvsmart por >10pp
- Quando rvsmart vence, a margem máxima é +22.7pp (git.rrgb.kinolog)
- Quando ape vence, a margem máxima é -50.6pp (com.linuxcounter.lico)

---

## Área 4 — Distribuição de Ações (rvsmart:mvp)

### 4.1 Distribuição Global

Total: 201,807 ações em 507 traces.

| Tipo | Count | % |
|------|-------|---|
| CLICK | 82,021 | 40.6% |
| SKIP | 38,304 | 19.0% |
| RESTART | 32,372 | 16.0% |
| SET_TEXT | 23,912 | 11.8% |
| LONG_CLICK | 11,874 | 5.9% |
| BACK | 7,879 | 3.9% |
| SCROLL | 5,445 | 2.7% |

### 4.2 Estatísticas Per-APK

| Tipo | Mean | Median | Min | Max | StdDev |
|------|------|--------|-----|-----|--------|
| CLICK | 37.0% | 38.5% | 0.0% | 79.5% | 24.0% |
| SKIP | 17.9% | 7.7% | 0.0% | 100.0% | 22.2% |
| RESTART | 19.3% | 14.5% | 0.0% | 100.0% | 18.1% |
| SET_TEXT | 12.5% | 4.4% | 0.0% | 65.4% | 16.2% |
| LONG_CLICK | 5.7% | 2.8% | 0.0% | 32.3% | 6.9% |
| BACK | 5.1% | 1.0% | 0.0% | 57.6% | 9.2% |
| SCROLL | 2.5% | 0.9% | 0.0% | 45.3% | 4.7% |

### 4.3 APKs Anômalos (41/169 = 24.3%)

Critérios: SKIP>50%, RESTART>30%, CLICK<10% (com >20 ações), BACK>30%.

**100% RESTART (3 APKs)** — rvsmart nunca avança além da tela inicial:
- `de.nellessen.usercontrolleddecryptionoperations_6.apk`
- `idv.markkuo.ambitsync_9.apk`
- `in.blogspot.anselmbros.torchie_34.apk`

**100% SKIP (1 APK)** — interface textual sem elementos acionáveis:
- `ohi.andre.consolelauncher_205.apk` (3,570 ações, todas SKIP)

**Alto SKIP + RESTART (sem CLICK)** — rvsmart alcança o app mas não consegue interagir:
- `com.spisoft.quicknote_241.apk` (67.8% SKIP, 32.2% RESTART)
- `com.mishiranu.dashchan_1043.apk` (67.7% SKIP, 32.3% RESTART)
- `info.metadude.android.debconf.schedule_85.apk` (64% SKIP, 36% RESTART)
- `pw.thedrhax.mosmetro_77.apk` (68.7% SKIP, 31.3% RESTART)
- `tk.giesecke.painlessmesh_14.apk` (66.3% SKIP, 33.7% RESTART)

**Alto BACK (>30%)** — rvsmart preso em loops de navegação:
- `com.maxfierke.sandwichroulette_2.apk` (57.6% BACK)
- `org.openintents.safe_30.apk` (50.4% BACK)
- `net.etuldan.sparss.floss_75.apk` (47.0% BACK)

### 4.4 Efetividade das Ações

- **Mean action_had_effect=true**: 63.6%
- **Median**: 72.6%
- **Min**: 0.0% (10 APKs com 0% — zero-state APKs)
- **Max**: 98.7%

~36% das ações não têm efeito observável na UI.

---

## Área 5 — Cobertura de UI

### 5.1 RVSmart — Estatísticas Agregadas (169 APKs)

| Métrica | Mean | Median | Min | Max | StdDev |
|---------|------|--------|-----|-----|--------|
| Unique States | 25.0 | 16.0 | 0 | 194 | 29.9 |
| Unique Activities | 5.2 | 5.0 | 0 | 17 | 3.4 |
| Structural Clusters | 19.9 | 14.0 | 0 | 104 | 20.1 |
| Nav Map Edges | 78.5 | 60.0 | 0 | 369 | 73.1 |
| Iterations | 296.4 | 298.0 | 0 | 704 | 168.0 |
| Throughput (evt/s) | 0.49 | 0.50 | 0.0 | 1.2 | 0.28 |
| Total Transitions | 67.7 | 44.0 | 0 | 432 | 75.7 |

Nota: `unique_states` == `unique_hashes` == `content_states` em todos os 169 APKs (métricas redundantes).

### 5.2 RVSmart — Distribuição de Estados

| Faixa | Count | % | Cum% |
|-------|-------|---|------|
| [0, 1) | 10 | 5.9% | 5.9% |
| [1, 2) | 10 | 5.9% | 11.8% |
| [2, 3) | 6 | 3.6% | 15.4% |
| [3, 5) | 11 | 6.5% | 21.9% |
| [5, 10) | 20 | 11.8% | 33.7% |
| [10, 20) | 42 | 24.9% | 58.6% |
| [20, 50) | 42 | 24.9% | 83.4% |
| [50, 100) | 22 | 13.0% | 96.4% |
| [100, 200) | 6 | 3.6% | 100.0% |

**26 APKs (15.4%) têm <=2 estados**, incluindo 10 com exatamente 0 estados.

### 5.3 APKs com 0 Estados (rvsmart nunca parseou uma tela)

`com.mishiranu.dashchan_1043.apk`, `com.spisoft.quicknote_241.apk`, `info.guardianproject.gilga_11.apk`, `info.metadude.android.debconf.schedule_85.apk`, `io.github.installalogs_10.apk`, `io.github.x0b.rcx_220.apk`, `ohi.andre.consolelauncher_205.apk`, `org.moire.ultrasonic_129.apk`, `pw.thedrhax.mosmetro_77.apk`, `tk.giesecke.painlessmesh_14.apk`

### 5.4 Top 5 APKs com mais estados (rvsmart)

| APK | States | Activities | Iterations | Throughput |
|-----|--------|------------|------------|------------|
| jp.co.kayo.android.localplayer_2071400330.apk | 194 | 8 | 635 | 1.10 |
| org.asdtm.fas_3.apk | 165 | 13 | 704 | 1.20 |
| com.quaap.launchtime_850.apk | 131 | 16 | 375 | 0.60 |
| com.cyanogenmod.filemanager.ics_1015.apk | 114 | 6 | 453 | 0.80 |
| com.github.axet.hourlyreminder_476.apk | 101 | 2 | 448 | 0.70 |

### 5.5 APE — Estatísticas (159 APKs com dados parseáveis)

| Métrica | Mean | Median | Min | Max | StdDev |
|---------|------|--------|-----|-----|--------|
| Unique States | 95.5 | 77.0 | 1 | 416 | 87.1 |
| Max Steps | 517.4 | 553.0 | 1 | 865 | 184.2 |

### 5.6 Comparação Direta rvsmart vs ape (159 APKs comuns)

| Métrica | RVSmart | APE | Razão |
|---------|---------|-----|-------|
| Mean states | 26.3 | 95.5 | **3.6x** |
| Median states | 17.0 | 77.0 | **4.5x** |

| Resultado | Count | % |
|-----------|-------|---|
| APE vence | 141 | 88.7% |
| RVSmart vence | 14 | 8.8% |
| Empate | 4 | 2.5% |

**Razão APE/RVSmart**: mean=6.22x, median=3.70x (APE descobre 3.7x mais estados na mediana).

**Maiores vantagens APE**: org.decsync.flym_46 (rv=36 vs ape=416, delta=-380), org.mupen64plusae.v3.alpha_246 (42 vs 376), net.frju.flym_40 (37 vs 353).

**Maiores vantagens rvsmart** (todas pequenas): com.blippex.app_5 (rv=10 vs ape=3, delta=+7), com.aptasystems.dicewarepasswordgenerator_8 (17 vs 11), org.opengpx_192 (20 vs 14). Vantagem máxima do rvsmart: +7 estados.

### 5.7 Throughput Distribution (rvsmart)

| Faixa (evt/s) | Count | % |
|----------------|-------|---|
| [0.00, 0.25) | 36 | 21.3% |
| [0.25, 0.50) | 41 | 24.3% |
| [0.50, 0.75) | 61 | 36.1% |
| [0.75, 1.00) | 20 | 11.8% |
| [1.00, +inf) | 11 | 6.5% |

Mediana: 0.50 evt/s (~300 iterações em 600s) vs APE mediana 553 steps. APE executa ~1.85x mais passos, mas a diferença de estados (3.7x) é maior que a diferença de passos, indicando que a estratégia SATA do APE é mais eficiente por passo na descoberta de novos estados.

---

## Área 6 — Plateau/Stochastic/Recovery

### 6.1 Distribuição de Fases (169 APKs)

| Fase | Mean% | Median% | Min% | Max% |
|------|-------|---------|------|------|
| Phase 1 (systematic) | 83.0 | 100.0 | 0.0 | 100.0 |
| Phase 2 (coverage-nav) | 11.0 | 0.0 | 0.0 | 98.2 |
| Phase 3 (stochastic) | 0.2 | 0.0 | 0.0 | 25.6 |

- **106/169 (62.7%)** ficaram inteiramente em Phase 1
- **53/169 (31.4%)** alcançaram Phase 2
- **2/169 (1.2%)** alcançaram Phase 3

Top APKs por uso de Phase 2+3: com.crazyhitty.chdev.ks.munch_14 (98.2% P2), de.nellessen.usercontrolleddecryptionoperations_6 (98.1% P2), digital.selfdefense.lucia_20001 (98.1% P2).

### 6.2 Crashes, Forced Backs, Retries

| Métrica | Mean | Median | Min | Max | Sum |
|---------|------|--------|-----|-----|-----|
| Crashes | 4.4 | 0.0 | 0 | 92 | 740 |
| Forced backs | 21.2 | 6.0 | 0 | 158 | 3,581 |
| Multi-attempt retries | 152.7 | 144.0 | 0 | 414 | 25,804 |
| System dialogs | 22.3 | 2.0 | 0 | 315 | 3,762 |

- **89/169 (52.7%)** APKs tiveram zero crashes
- Top crashers: com.lostrealm.lembretes_93 (92), org.pixmob.freemobile.netstat_63 (73), com.gbeatty.arxiv_39 (65)
- Multi-attempt retries são muito comuns (mean=152.7 por APK) — esperado pois o algoritmo retenta ações no mesmo estado

### 6.3 Tier Distribution (133,991 RVTRACK:STRATEGY lines)

| Tier | Count | % |
|------|-------|---|
| Tier 1 | 100,108 | 74.7% |
| Tier 2 | 3,997 | 3.0% |
| Tier 3 | 29,886 | 22.3% |

### 6.4 Strategy Reason Distribution

| Reason | Count | % |
|--------|-------|---|
| p1_untested | 51,756 | 38.6% |
| p1_nav_cluster | 48,352 | 36.1% |
| p3_stochastic | 29,886 | 22.3% |
| p2_coverage_nav | 3,997 | 3.0% |

**Sistemático vs Estocástico**:
- **Sistemático: 77.7%** (p1_untested + p1_nav_cluster + p2_coverage_nav)
- **Estocástico: 22.3%** (p3_stochastic)

### 6.5 Saturação

Estatísticas de saturação (133,991 observações):
- Mean: 0.548, Median: 1.000, Min: 0.000, Max: 1.000

**Distribuição bimodal**:

| Faixa | Count | % |
|-------|-------|---|
| [0.0, 0.2) | 57,375 | 42.8% |
| [0.2, 0.8) | 6,450 | 4.8% |
| [0.8, 1.0) | 662 | 0.5% |
| [1.0] | 70,166 | 52.4% |

O algoritmo opera em dois regimes: estados frescos (42.8% perto de 0) e estados totalmente explorados (52.4% em 1.0).

**96.9% dos APKs** atingem saturação alta (>=0.8) em algum momento — o algoritmo efetivamente satura os espaços de widgets disponíveis.

### 6.6 Score Tier Distribution

| Tier | Significado | % das Decisões |
|------|------------|----------------|
| Tier 1 | Melhor (untested/high-value) | 74.7% |
| Tier 2 | Coverage-guided navigation | 3.0% |
| Tier 3 | Stochastic fallback | 22.3% |

---

## Área 7 — Score Breakdown Detalhado

### 7.1 Métricas por Ferramenta (tasks.json, 507 tasks rvsmart, 504 tasks ape)

**rvsmart:mvp**:

| Métrica | Mean | Median | Min | Max | Std |
|---------|------|--------|-----|-----|-----|
| method_coverage | 24.42 | 21.88 | 0.00 | 70.00 | 17.20 |
| activities_coverage | 60.41 | 60.00 | 0.00 | 100.00 | 31.85 |
| mop_coverage | 31.96 | 27.31 | 0.00 | 100.00 | 28.45 |
| total_errors | 1.36 | 0.00 | 0.00 | 18.00 | 2.55 |
| total_method_calls | 135.22 | 69.00 | 0.00 | 1,270.00 | 175.39 |

**ape**:

| Métrica | Mean | Median | Min | Max | Std |
|---------|------|--------|-----|-----|-----|
| method_coverage | 27.70 | 26.24 | 0.00 | 75.00 | 18.46 |
| activities_coverage | 62.48 | 62.50 | 0.00 | 100.00 | 32.08 |
| mop_coverage | 36.96 | 33.33 | 0.00 | 100.00 | 30.03 |
| total_errors | 1.54 | 0.00 | 0.00 | 23.00 | 2.78 |
| total_method_calls | 157.31 | 72.00 | 0.00 | 1,535.00 | 205.26 |

### 7.2 Distribuição de Method Coverage (por task)

| Faixa | rvsmart | ape |
|-------|---------|-----|
| >50% | 54/507 (10.7%) | 76/507 (15.0%) |
| >70% | 0/507 (0.0%) | 3/507 (0.6%) |
| >90% | 0/507 (0.0%) | 0/507 (0.0%) |

### 7.3 Distribuição de MOP Coverage (por task)

| Faixa | rvsmart | ape |
|-------|---------|-----|
| =0% | 70 (13.8%) | 69 (13.6%) |
| >50% | 113 (22.3%) | 161 (31.8%) |
| >70% | 62 (12.2%) | 77 (15.2%) |
| =100% | 27 (5.3%) | 32 (6.3%) |

### 7.4 Total Method Calls

| Tool | Sum | Mean | Median |
|------|-----|------|--------|
| rvsmart:mvp | 68,558 | 135.2 | 69.0 |
| ape | 79,758 | 157.3 | 72.0 |

APE dispara ~16% mais method calls.

### 7.5 Detected Errors

| Tool | Sum | Tasks com erros | Mean |
|------|-----|-----------------|------|
| rvsmart:mvp | 688 | 198/507 (39.1%) | 1.36 |
| ape | 783 | 221/507 (43.6%) | 1.54 |

APE detecta ~14% mais erros, com ligeira vantagem na cobertura de detecção.

---

## Área 8 — Comparação com Critérios de Validação

| Métrica | Esperado | Resultado | Status |
|---------|----------|-----------|--------|
| Completion rate | >95% | 99.6% (1010/1014) | **OK** |
| Execution time consistency | ~660s ± 30s | 648-696s (σ=6.5s) | **OK** |
| No systematic crashes | 0 systematic | 4 transient EmulatorError | **OK** |
| Method coverage rvsmart > 20% | >20% mean | 24.43% | **OK** |
| Activity coverage > 50% | >50% mean | 60.41% | **OK** |
| MOP violations detected | >30% APKs | 47.3% (80/169) | **OK** |
| rvsmart vs ape competitive | Gap < 5pp | -3.31pp method, -5.03pp MOP | **PARCIAL** |
| Systematic > stochastic | >70% systematic | 77.7% systematic | **OK** |
| Throughput rvsmart | >0.3 evt/s median | 0.50 evt/s | **OK** |
| Phase 1 dominant | >60% Phase 1 | 62.7% exclusively P1 | **OK** |
| Zero-state APKs | <10% | 5.9% (10/169) | **OK** |
| State discovery competitive | Gap < 2x | 3.7x median (APE wins) | **FALHOU** |
| Baseline regression | No regression | +0.92pp vs baseline | **OK** |
| Error detection parity | Similar | 686 vs 771 (89% ratio) | **OK** |

---

## Área 9 — Conclusão

### O que melhorou (vs baseline)

1. **rvsmart method coverage subiu +0.92pp** em relação à comparacao_v2 (23.99% → 24.91% nos 100 APKs sobrepostos)
2. **Gap com ape diminuiu** de 4.39pp para 2.76pp nos APKs sobrepostos
3. **Decisões sistemáticas dominam** (77.7%) — o algoritmo é predominantemente guiado, não aleatório
4. **Throughput estável** a 0.50 evt/s mediana, com 96.9% dos APKs atingindo saturação alta
5. **Confiabilidade do experimento** excelente: 99.6% completion rate, tempos consistentes

### O que ficou igual

1. **Cobertura de atividades** similar entre as ferramentas (60.41% vs 62.58%)
2. **MOP detection** comparável (80 APKs com violações, 68 detectados por ambos)
3. **APKs intestáveis** (2 APKs com 0% para ambos, 10 APKs com 0 estados para rvsmart vs 8 para APE)

### O que piorou / problemas identificados

1. **APE domina em descoberta de estados**: 3.7x mais estados na mediana (77 vs 16), vencendo em 88.7% dos APKs
2. **APE vence em method coverage**: -3.31pp global, com 77 APKs perdendo vs 21 vencendo (threshold 2pp)
3. **Assimetria pronunciada**: quando ape vence, margem é grande (até -50.6pp); quando rvsmart vence, margem é menor (máx +22.7pp)
4. **35% das ações rvsmart são SKIP+RESTART** — desperdício significativo de orçamento de exploração
5. **10 APKs (5.9%) com 0 estados** — rvsmart completamente incapaz de parsear a UI
6. **Throughput gap**: rvsmart ~300 iterações vs APE ~553 steps em 600s (1.85x), mas o gap de estados (3.7x) é maior que o gap de throughput, indicando menor eficiência por iteração

### Bugs a corrigir

1. **10 APKs zero-state**: investigar por que rvsmart não consegue parsear essas UIs (console apps, custom views, etc.)
2. **3 APKs 100% RESTART**: rvsmart fica preso sem avançar — investigar o loop de restart
3. **SKIP+RESTART overhead (35%)**: principal gargalo — cada SKIP e RESTART não contribui para exploração
4. **unique_states/unique_hashes/content_states redundância**: métricas idênticas em 100% dos APKs — simplificar
5. **Phase 2/3 subutilizados**: apenas 31.4% alcançam Phase 2 e 1.2% Phase 3 — pode indicar que os thresholds de escalação são muito altos

### Diagnóstico principal

O **gargalo principal do rvsmart é throughput + eficiência de exploração**, não a qualidade das decisões. Com 77.7% de decisões sistemáticas e saturação alta em 96.9% dos APKs, o algoritmo toma decisões razoáveis, mas:

1. Executa ~1.85x menos passos que APE (overhead de parsing, UIAutomator latency)
2. Desperdiça ~35% dos passos em SKIP/RESTART
3. Descobre ~3.7x menos estados (eficiência por passo é menor)

O caminho para melhorar passa por: (a) reduzir overhead de SKIP/RESTART, (b) aumentar throughput de iterações, e (c) melhorar a eficiência de descoberta de novos estados por iteração.
