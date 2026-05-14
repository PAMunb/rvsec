# Relatório — Experimento RV-Android 2026-05-08

## 1. Sumário executivo

| Item | Valor |
|------|-------|
| Dispatch | 2026-05-08 21:50 BRT |
| Conclusão | 2026-05-12 10:41 BRT |
| Wall-clock total | ~85 h |
| VMs | 4 (m1-exp02, m2-exp02, m3-exp02, m4-exp04 — GCP us-central1) |
| Containers paralelos | 16 (4 por VM) |
| APKs | 190 (subset instrumentado com dexlib2 da JCA-226) |
| Tools | 11 (monkey, droidbot×4, ape, droidmate, humanoid, ares, fastbot, qtesting) |
| Timeouts | 3 (60 s, 180 s, 300 s) — 3 passadas sequenciais |
| Repetições | 3 |
| **Tasks únicas planejadas** | **18 810** |
| Tasks executadas (incl. retries) | 19 056 |
| Tasks únicas concluídas | 18 770 (99,79 %) |
| Tasks perdidas | 40 (todas em m3/exp_00 por OOMs em passes T60/T180) |
| Incidentes (OOM/hang) | 12 — recuperados via auto-resume |

## 2. Localização dos resultados

### 2.1 Raw por VM (cópia local)

`/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/`

| VM | tasks.json | .logcat | summary.csv |
|----|-----------|---------|-------------|
| m1 | 4 941 | 4 651 (94 %) | 4 321 (87 %) |
| m2 | 4 849 | 4 637 (96 %) | 4 307 (89 %) |
| m3 | 4 712 | 4 559 (97 %) | 4 229 (90 %) |
| m4 | 4 554 | 4 420 (97 %) | 4 095 (90 %) |
| **Σ** | **19 056** | **18 267** | **16 952** |

Estrutura por VM: `RESULTADOS/<vm>/results/<container>/<container>/{tasks.json, summary.csv, coverage.csv, errors.csv, performance.csv, *.logcat, *.trace}`.

Gaps esperados:
- tasks.json → .logcat (~3 %): execuções `state=ERROR` que morreram antes da captura iniciar
- .logcat → summary.csv (~10 %): execuções que rodaram o tool mas crashou o app/monkey-timeout antes da cobertura ser gravada

### 2.2 Consolidados na raiz de RESULTADOS

| Arquivo | Linhas (sem header) | Descrição |
|---------|---------------------|-----------|
| `summary_all.csv` | 16 952 | 1 linha por (apk × tool × rep × timeout) com coverage final + count de violações MOP |
| `coverage_all.csv` | 759 630 | snapshots periódicos de cobertura ao longo da execução |
| `errors_all.csv` | 237 156 | cada violação MOP detectada (apk, tool, rep, timeout, spec, class, method, message) |

Smoke tests (`vmsmoke/`, `minismoke/`) **não** entram nos consolidados.

### 2.3 INCIDENTES.md

`experimento-20260508/INCIDENTS.md` — registro cronológico de cada OOM/hang com timestamp, container afetado, diagnóstico e ação tomada.

## 3. Setup da campanha

### 3.1 Infraestrutura

| VM | Zone | Type | RAM | Batches | APKs |
|----|------|------|-----|---------|------|
| m1-exp02 | us-central1-a | n2-standard-16 | 64 GB | batch_00..03 | 48 |
| m2-exp02 | us-central1-f | n2-custom-16-32768 | 32 GB | batch_04..07 | 48 |
| m3-exp02 | us-central1-f | n2-custom-16-32768 | 32 GB | batch_08..11 | 48 |
| m4-exp04 | us-central1-f | n2-custom-16-32768 | 32 GB | batch_12..15 | 46 |

Cada VM rodou 4 containers Docker em paralelo, cada container 1 batch, totalizando 16 batches × ~11,9 APKs = 190 APKs sem duplicação.

### 3.2 Dataset

- **Origem**: JCA-400 (`fdroid_prs_top400.csv`)
- **Pipeline de preparação**: 400 → 380 (GATOR static-analyzed) → 226 (sa_reaches_mop=true) → 224 (dexlib2-instrumented, 99,1 %) → 190 (validados para execução)
- **Instrumentação**: dexlib2 com specs JCA (SSLContextSpec, SecureRandomSpec, TrustManagerFactorySpec, KeyStoreSpec, MessageDigestSpec)
- **Dois APKs perdidos no dexlib2**: `it.fast4x.riplay_74.apk` e `io.github.chrisimx.scanbridge_2001004.apk` — silent failures (instr-cli exit 0 sem APK produzido). Mesmas falhas reproduziram em AJC (d8 ArrayIndexOutOfBoundsException).

### 3.3 Arquitetura de execução

```
run_experiment.sh                   # 3 passes sequenciais
   └─ for TIMEOUT in 60 180 300:
        EXP_TIMEOUT=$TIMEOUT docker compose up -d  # 4 containers
        docker wait exp_00 exp_01 exp_02 exp_03    # bloqueia até todos completarem
        docker compose down
```

Cada container: rv-experiment + emulador Android (AVD API 30 x86_64 google_apis_playstore, 8 GB RAM limit, RV_HUMANOID_URL para o sidecar humanoid:50405).

## 4. Incidentes

12 incidentes ao longo das 85 h, distribuição:

| Tipo | Total | Detalhes |
|------|------:|----------|
| OOM (exit 137) | 11 | Padrão: docker-sibling (ARES/QTesting) cresce além do limite de 8 GB. m1 (64 GB): 4 OOMs; m2/m3/m4 (32 GB, sem folga p/ OS): 7 OOMs. |
| adb install hang | 1 | m1/exp_01 ficou ~3h22 sem progresso instalando `com.vishaltelangre.nerdcalci_371.apk`. Recuperado via `docker restart`. |

**Recuperação**: 100 % dos incidentes mitigados via `docker compose up -d <container>` + auto-resume do rv-experiment (tasks.json mantém estado por tuple `apk×tool×variant×rep×timeout`).

**Perdas**: 40 tasks únicas em m3/exp_00 (25 T60 + 15 T180) — quando o OOM ocorria no fim de uma passada e o script já tinha avançado para a próxima, as tasks faltantes daquela passada não retentavam. m3/exp_00 ficou com 1 148 tasks vs 1 188 ideais.

Para o futuro: aumentar VMs 32 GB para 64 GB ou reduzir limite Docker de 8 GB → 6 GB nas 32 GB VMs (em troca de menos paralelismo intra-container).

## 5. Análise superficial dos resultados

### 5.1 Ranking de tools por cobertura MOP (média de % methods reaches-MOP)

| Tool | N runs | Cov_MOP | % runs c/ violação |
|------|------:|--------:|------------------:|
| **monkey** | 356 | **32,62 %** | 36,0 % |
| **ape** | 1 649 | **27,14 %** | 36,6 % |
| ares | 1 658 | 24,68 % | 34,1 % |
| fastbot | 1 648 | 24,43 % | 33,9 % |
| droidmate | 1 666 | 24,05 % | 34,9 % |
| humanoid | 1 665 | 23,26 % | 34,2 % |
| droidbot:dfs_greedy | 1 663 | 23,18 % | 34,6 % |
| qtesting | 1 653 | 23,05 % | 33,5 % |
| droidbot:bfs_greedy | 1 668 | 23,04 % | 33,4 % |
| droidbot:dfs_naive | 1 655 | 21,92 % | 32,8 % |
| droidbot:bfs_naive | 1 671 | 21,86 % | 32,4 % |

**Observações**:
- **APE é a tool líder em pé de igualdade**: 1 649 runs estáveis, 2ª maior cobertura, maior contagem absoluta de violações detectadas (2 130).
- **Monkey aparenta liderar** mas com forte viés de sobrevivência — só 356/1 650 runs (~22 %) sobreviveram ao gravamento do summary.csv (os demais terminaram em ERROR cosmético por timeout do platform). A métrica só compara monkey nos apps "fáceis".
- **DroidBot heurísticas**: `greedy > naive` em ~1,3 pp; `dfs ≈ bfs` (~0,1 pp diferença). A priorização tem efeito; a ordem de visita não.
- **Cluster do meio**: ares, fastbot, droidmate, humanoid, droidbot:greedy, qtesting → 23-25 % MOP, dificultando ranqueamento robusto sem teste estatístico.

### 5.2 Sensibilidade ao tempo de execução

Δ(T300−T60) em pontos percentuais de Cov_MOP:

| Tool | T60 | T180 | T300 | Δ |
|------|----:|-----:|-----:|--:|
| monkey | 31,20 % | 35,34 % | 42,06 % | **+10,86 pp** |
| ape | 24,51 % | 27,35 % | 29,53 % | +5,01 pp |
| droidmate | 21,26 % | 25,01 % | 25,89 % | +4,63 pp |
| humanoid | 20,85 % | 23,79 % | 25,13 % | +4,28 pp |
| ares | 22,69 % | 25,38 % | 25,98 % | +3,29 pp |
| droidbot:bfs_greedy | 21,14 % | 23,70 % | 24,31 % | +3,17 pp |
| qtesting | 21,38 % | 23,39 % | 24,34 % | +2,97 pp |
| droidbot:dfs_greedy | 21,77 % | 23,24 % | 24,54 % | +2,77 pp |
| droidbot:bfs_naive | 20,62 % | 22,21 % | 22,74 % | +2,13 pp |
| fastbot | 23,34 % | 24,54 % | 25,39 % | +2,04 pp |
| droidbot:dfs_naive | 20,62 % | 22,55 % | 22,56 % | +1,94 pp |

**Padrões**:
- **monkey** ganha mais com tempo (random precisa de muito tempo para acertar).
- **fastbot e droidbot:dfs_naive** saturam cedo — esgotam estratégias entre 60 s e 180 s e ganham pouco no T300.
- **ape, droidmate, humanoid** continuam aproveitando T300 → exploração estruturada profunda.

### 5.3 Violações MOP totais

| Tool | T60 | T180 | T300 | Total |
|------|----:|-----:|-----:|------:|
| ape | 632 | 738 | 760 | **2 130** |
| droidmate | 643 | 705 | 700 | 2 048 |
| droidbot:dfs_greedy | 625 | 661 | 693 | 1 979 |
| humanoid | 613 | 660 | 696 | 1 969 |
| ares | 635 | 653 | 667 | 1 955 |
| droidbot:bfs_greedy | 618 | 641 | 662 | 1 921 |
| fastbot | 583 | 656 | 658 | 1 897 |
| qtesting | 595 | 636 | 642 | 1 873 |
| droidbot:bfs_naive | 603 | 621 | 637 | 1 861 |
| droidbot:dfs_naive | 588 | 639 | 622 | 1 849 |
| monkey | 370 | 96 | 37 | 503 |

`errors_all.csv` (237 156 linhas) detalha cada violação individual (apk, tool, rep, timeout, spec, class, method, message). O total da soma por tool acima vem do `summary.csv` (1 número de violações por execução); a contagem detalhada por evento em `errors_all.csv` é maior porque registra cada disparo individual.

## 6. Taxa de erros (ERROR-state de execução)

Diferente das violações MOP, este é o `state=ERROR` em `tasks.json`:

| | Quantidade |
|---|---|
| Tasks executadas | 12 910 (com retries) |
| COMPLETED | 11 576 (89,7 %) |
| **ERROR** | **1 334 (10,3 %)** |

Distribuição por tool:

| Tool | ERROR | % do total |
|------|------:|-----------:|
| monkey | 935 | 70,1 % ← **cosmético** (exit 100/130/255 ao matar o monkey no fim do timeout) |
| droidbot (4 variantes) | 127 | 9,5 % |
| ape | 44 | 3,3 % |
| qtesting | 43 | 3,2 % |
| fastbot | 42 | 3,1 % |
| ares | 37 | 2,8 % |
| humanoid | 29 | 2,2 % |
| droidmate | 27 | 2,0 % |

**Taxa de erro "real"** (descontando os 935 cosméticos do monkey): **399 / 12 910 = 3,1 %**, alinhada à validação prévia (3-5 % em apps Compose/R8).

Distribuição **uniforme** entre as VMs (9,7 %–11,3 %) — nenhuma VM doente; comportamento da campanha foi homogêneo.

## 7. Apêndices

### 7.1 Tools — variantes e nomenclatura

| Tool no compose | Descrição |
|-----------------|-----------|
| monkey | UI/Application Exerciser Monkey nativo do Android |
| droidbot:dfs_greedy | DroidBot com DFS + heurística de priorização |
| droidbot:bfs_greedy | DroidBot com BFS + heurística |
| droidbot:dfs_naive | DroidBot com DFS sem heurística |
| droidbot:bfs_naive | DroidBot com BFS sem heurística |
| ape | APE-RV (model-based exploration) |
| droidmate | DroidMate-2 |
| humanoid | Humanoid (HTTP sidecar em rv-humanoid:50405) |
| ares | ARES (docker sibling) |
| fastbot | Fastbot 2.0 (in-emulator via app_process) |
| qtesting | QTesting (docker sibling) |

### 7.2 Parâmetros de execução

- `RV_INSTRUMENTATION_VARIANT=dexlib2`
- `RV_SPEC_SET=jca`
- `RV_REPETITIONS=3`
- `RV_TIMEOUTS=60` (depois 180, depois 300 — controlado por `EXP_TIMEOUT` no loop)
- `RV_SKIP_MONITORS=true`, `RV_SKIP_INSTRUMENT=true`, `RV_SKIP_STATIC_ANALYSIS=true` (artefatos pré-processados, reutilizados)
- Filtros por container: `/opt/rvsec/rv-android/filters/batch_NN.txt`
- Memória por container: 8 GB (8g hard limit no `deploy.resources.limits`)
- CPUs por container: 4 (4 × 4 = 16 totais por VM)

### 7.3 Datas-marco

| Data | Evento |
|------|--------|
| 2026-05-08 21:50 | Dispatch das 4 VMs |
| 2026-05-09 02:59 | Primeiro OOM (m1/exp_00) |
| 2026-05-10 14:09 | m3 entra em T300 (primeira VM a fechar T180) |
| 2026-05-10 15:11 | m4 entra em T300 |
| 2026-05-10 19:19 | m1 entra em T300 |
| 2026-05-10 20:21 | m2 entra em T300 — **todas as 4 VMs em T300** |
| 2026-05-11 16:04 | 89 % concluído |
| 2026-05-12 02:24 | m3 100 % concluída |
| 2026-05-12 03:26 | m4 100 % concluída |
| 2026-05-12 09:39 | m1 100 % concluída |
| 2026-05-12 10:41 | m2 100 % concluída → **CAMPANHA FINALIZADA** |
| 2026-05-12-14 | Cópia para local + consolidação + análise |

### 7.4 Tabela de tasks (esperadas × executadas × registradas)

| | Tasks | % do esperado |
|---|------:|-------------:|
| **Esperadas** (11 × 3 × 3 × 190) | **18 810** | 100,00 % |
| Únicas concluídas | 18 770 | 99,79 % |
| .logcat geradas | 18 267 | 97,11 % |
| Linhas em summary_all.csv | 16 952 | 90,12 % |

### 7.5 Materiais complementares

- `experimento-20260508/README.md` — documentação operacional da campanha
- `experimento-20260508/INCIDENTS.md` — log cronológico dos 12 incidentes
- `experimento-20260508/docker-compose.gcp.yml` — definição dos 4 services exp_NN + humanoid
- `experimento-20260508/.env.m{1,2,3,4}` — mapeamento batch→container por VM
- `experimento-20260508/scripts/run_experiment.sh` — orquestração 3-pass
- `experimento-20260508/filters/batch_{00..15}.txt` — 16 listas round-robin de APKs
- `experimento-20260508/data/validation_filters/validation_apks.txt` — 190 APKs canônicos

## 8. Próximos passos (sugestões)

1. **Teste estatístico** entre tools no cluster do meio (ares/fastbot/droidmate/humanoid/droidbot:greedy/qtesting) — diferenças de 1-2 pp podem não ser significativas.
2. **Estratificação por categoria de app**: Compose+R8 vs Legacy, app simples vs complexo — investigar onde monkey/ape divergem mais.
3. **Reexecução dos 40 tasks perdidos** em m3/exp_00 (T60 e T180) se quiser fechar o cartesian em 100 %.
4. **Análise de coverage_all.csv** (759 630 snapshots) — curvas de cobertura ao longo do tempo, identificar plateau-time por tool.
5. **Investigação dos 2 silent failures dexlib2** (riplay, scanbridge) — root cause pendente; mesma falha em AJC sugere bug em R8/D8 obfuscation que afeta o bytecode original.
