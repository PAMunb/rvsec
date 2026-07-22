# Experimento Comparativo: RVSmart vs APE vs FastBot

**Data**: 2026-03-08
**Status**: Planejamento
**Objetivo**: Comparação informal mas rigorosa das 3 ferramentas de exploração algorítmica, focando em identificar anomalias, bugs e pontos de melhoria do RVSmart.

## 1. Configuração do Experimento

### 1.1 Dados Existentes (Baseline gh9)

A baseline da gh9 (`results/baseline_v2/`) já contém dados completos de APE e FastBot:

| Ferramenta | APKs | Reps | Timeout | Dados disponíveis |
|-----------|------|------|---------|-------------------|
| **ape** | 169 | 3 | 600s | summary.csv + trace + logcat por task |
| **fastbot** | 174 | 3 | 600s | summary.csv + trace + logcat por task |
| rvagent:pure_algorithm | 174 | 3 | 600s | summary.csv + trace + logcat + metrics |

**Todos os 100 APKs da seleção estratificada estão na baseline**. Não precisamos re-executar APE e FastBot.

Estrutura dos dados baseline:
```
results/baseline_v2/
├── summary.csv          # 1551 rows (APK × tool × rep): cov_act, cov_method, cov_rv_method, errors
├── aggregated_summary.csv
├── batch_0/batch_0/     # Trace files + logcats por APK
├── batch_1/batch_1/
├── batch_2/batch_2/
└── batch_3/batch_3/
```

Cada APK tem: `{apk}__{rep}__{timeout}__{tool}.trace` e `.logcat` para APE e FastBot.

### 1.2 Parâmetros (Execução RVSmart apenas)

| Parâmetro | Valor |
|-----------|-------|
| Dataset | calibration_dataset_v2 (subset de 100 APKs, estratificado) |
| Ferramenta | `rvsmart:mvp` (apenas) |
| Timeout | 600s (10 minutos) — mesmo da baseline |
| Repetições | 3 (mesmo da baseline para ape/fastbot) |
| Containers | 6 |
| APKs/container | ~17 |
| Tasks/container | 17 APKs × 1 tool × 3 reps = 51 |
| Tempo estimado/container | 51 × 720s ≈ 10.2h |
| Specification set | JCA |
| Skip flags | `--skip-monitors --skip-instrument --skip-static` |
| Imagem Docker | `phtcosta/rvandroid:0.8.0` (rebuild com código atual) |
| Comparação | APE e FastBot da baseline gh9 (3 reps, 600s) |

### 1.3 Janela de Execução

- **Início**: 2026-03-08 ~14:00 (após build + setup)
- **Deadline**: 2026-03-09 12:00
- **Janela total**: ~22h
- **Tempo estimado**: ~10h (sobram ~12h de margem)

### 1.4 Recursos para Análise de APKs Problemáticos

Códigos-fonte dos APKs disponíveis em: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-testes-jca/sources/` (187 APKs). Para APKs onde o rvsmart apresentar anomalias, o código-fonte pode ser consultado para entender o comportamento esperado e identificar causa raiz.

### 1.5 Recursos da Máquina

| Recurso | Total | Alocado (6 containers) | Livre |
|---------|-------|----------------------|-------|
| CPUs | 64 | 24 (4/container) | 40 |
| RAM | 123GB | 48GB (8GB/container) | 75GB |
| KVM | sim | compartilhado | - |

### 1.4 Dataset

Fonte: `modules/rv-agent-validation/data/calibration_dataset_v2/`
- 167 APKs instrumentados (JCA) + 167 JSONs de análise estática unificada (gh27)
- Subconjunto de **100 APKs selecionados por amostragem estratificada**
- Estratificação: `primary_category × size_bucket` (métodos count) via `scripts/select_dataset.py`
- Seed: 42 (reprodutível)

Distribuição da amostra (100 APKs):

| Size bucket | APKs | % |
|------------|------|---|
| tiny (0-50) | 9 | 9% |
| small (50-200) | 24 | 24% |
| medium (200-500) | 31 | 31% |
| large (500-1500) | 23 | 23% |
| xlarge (1500+) | 13 | 13% |

Top categorias: Internet (17), Multimedia (14), System (12), Security (8), Games (7).
Detalhes completos: `data/selection/`

Gerar seleção estratificada:
```bash
uv run python scripts/select_dataset.py \
    --passed-apks modules/rv-agent-validation/data/calibration_dataset_v2/all_valid_apks.txt \
    --csv modules/rv-agent-validation/data/apks_complete.csv \
    --cal-size 100 --output-dir data/selection --seed 42
# Converter para formato com extensão .apk:
sed 's/$/.apk/' data/selection/calibration_set_v2.txt > data/comparacao_100apks.txt
```

## 2. Infraestrutura Docker

### 2.1 Docker Compose

Arquivo: `docker/docker-compose.comparacao.yml`

Cada container recebe:
- Seu batch de APKs via `RV_APKS_FILTER` (arquivo com lista de APKs do batch)
- `RV_TOOLS=rvsmart:mvp,ape,fastbot` — as 3 ferramentas numa única execução
- Volume compartilhado de APKs (read-only) e volume isolado de resultados
- Stagger delay para evitar boot-storm simultâneo

Variáveis de ambiente por container:
```yaml
RV_TOOLS: "rvsmart:mvp"
RV_TIMEOUTS: "600"
RV_REPETITIONS: "3"
RV_NO_WINDOW: "true"
RV_JCA_SPEC: "true"
RV_SKIP_MONITORS: "true"
RV_SKIP_INSTRUMENT: "true"
RV_SKIP_STATIC_ANALYSIS: "true"
RV_APKS_DIR: "/opt/rvsec/rv-android/apks"   # OBRIGATÓRIO com skip flags
RV_EXPERIMENT_NAME: "cmpXX"        # cmp01..cmp06
RV_DEVICE_PORT: "5554"             # cada container tem seu emulador interno
RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/batch_XX.txt"
RV_DELAY: "0/10/20/30/40/50"      # stagger de 10s entre containers
```

> **NOTA**: `RV_APKS_DIR` é obrigatório quando skip flags estão ativas. Sem ele, o entrypoint
> não passa `--apks-dir` e o rv-experiment usa o default `./apks_examples/` (vazio no container).
> Descoberto durante teste (ver Seção 3.5).

### 2.2 Distribuição de APKs

```
100 APKs ÷ 6 containers:
- cmp01..cmp04: 17 APKs cada (68 total)
- cmp05..cmp06: 16 APKs cada (32 total)
Total: 100 APKs
```

Gerar batches (feito automaticamente pelo `scripts/setup_comparacao.sh`):
```bash
cd data/apks
split -l 17 -d -a 2 --additional-suffix=.txt ../../data/comparacao_100apks.txt batch_
# batch_00.txt..batch_04.txt: 17 APKs cada
# batch_05.txt: 15 APKs
```

### 2.3 Estrutura de Volumes

```
data/
├── apks/                          # Montado read-only em todos os containers
│   ├── *.apk                      # 100 APKs instrumentados
│   ├── *.apk.json                 # 100 JSONs de análise estática
│   ├── batch_00.txt .. batch_05.txt  # Listas por container
│   └── comparacao_100apks.txt     # Lista completa
├── results/
│   ├── cmp01/                     # Resultados container 1
│   │   ├── summary.csv
│   │   ├── coverage.csv
│   │   ├── errors.csv
│   │   └── tasks/                 # Task dirs com trace, logcat, metrics
│   ├── cmp02/
│   ⋮
│   └── cmp06/
└── out/                           # Artefatos temporários (compartilhado)
```

### 2.4 Build da Imagem

```bash
# Rebuild com código atualizado (rvsmart gh30/31/32 fixes + output package)
bash docker/rvandroid/build.sh
# Imagem: phtcosta/rvandroid:0.8.0
```

**Nota**: O build clona `branch modules` do GitHub. Garantir que todo código esteja pushado antes do build. Na primeira tentativa, o package `br.unb.cic.rvsmart.output` (TraceWriter, MetricsCollector, RvTrack) não estava no repo — causou falha de compilação Maven.

### 2.5 Detalhes das Ferramentas

**rvsmart:mvp** — Agente Java de exploração via `app_process` no emulador
- Modo: `pure_algorithm` (DFS com 4 tiers de scoring)
- Throttle: 50ms entre ações
- Execução device-side (Java), não host-side
- Métricas auto-reportadas via `RVSMART_METRICS:` no stdout → `rvsmart_metrics.json`
- Usa análise estática (JSON) para guiar exploração quando disponível
- Health check antes da execução principal

**ape** (default variant) — Monkey estendido com estratégia SATA
- Modo: SATA (Static Analysis Targeted Abstraction), debug enabled
- Execução via `app_process` com `ape.jar` (similar ao rvsmart)
- Timeout convertido de segundos para minutos (`--running-minutes`)
- Output: trace binário no trace file

**fastbot** (default variant) — Monkey com agente RL (reuseq)
- Estratégia: balanced, max 10K steps, throttle 500ms
- Execução via `app_process` com 3 JARs (`monkeyq.jar`, `framework.jar`, `fastbot-thirdpart.jar`)
- Pode usar libs nativas (.so) para aceleração
- Timeout convertido de segundos para minutos
- Learning rate: 0.1, exploration rate configurável

## 3. Execução

### 3.1 Setup

```bash
# Script automatizado (seleção estratificada + cópia + batches)
bash scripts/setup_comparacao.sh
```

O script executa:
1. Cria diretórios `data/{apks, results/cmp01..cmp06}`
2. Roda `select_dataset.py` para seleção estratificada de 100 APKs (seed=42)
3. Copia APKs instrumentados + JSONs de SA para `data/apks/`
4. Gera batch files (`batch_00.txt`..`batch_05.txt`)
5. Verifica contagens

### 3.2 Lançamento

```bash
docker compose -f docker/docker-compose.comparacao.yml up -d
```

### 3.3 Monitoramento

```bash
# Status dos containers
docker compose -f docker/docker-compose.comparacao.yml ps

# Logs de um container específico
docker logs -f cmp01

# Progresso (tasks completas por container)
for c in cmp01 cmp02 cmp03 cmp04 cmp05 cmp06; do
  count=$(find data/results/$c -name "tasks.json" -exec grep -l "COMPLETED" {} \; 2>/dev/null | wc -l)
  total=$(cat data/apks/batch_*.txt 2>/dev/null | wc -l)  # aproximado
  echo "$c: $count tasks completas"
done

# Monitoramento contínuo
watch -n 60 'for c in cmp01 cmp02 cmp03 cmp04 cmp05 cmp06; do
  echo -n "$c: "; ls data/results/$c/*/tasks.json 2>/dev/null | wc -l
done'
```

### 3.4 Troubleshooting

| Problema | Diagnóstico | Ação |
|----------|------------|------|
| Container parou | `docker logs cmpXX` | Reiniciar: `docker compose restart cmpXX` (resume automático via `--name`) |
| Emulador não boota | Verificar `/dev/kvm` e memória | Reduzir containers ou aumentar memória |
| APK install falha | Verificar trace file do task | APK corrompido — ignorar |
| rvsmart.jar not found | `docker exec cmpXX ls /opt/rvsec/...` | Rebuild imagem |
| Sem métricas rvsmart | Verificar trace file | Bug no rvsmart — documentar na validação |
| "No APK files found" | Falta `RV_APKS_DIR` | Adicionar `RV_APKS_DIR=/opt/rvsec/rv-android/apks` |
| "batch_XX.txt does not exist" | Path relativo resolve para `docker/data/` | Usar `../data` no compose (compose file está em `docker/`) |
| Permissão negada em results/ | Container roda como root | Usar `docker run --rm alpine rm -rf` para limpar |

### 3.5 Descobertas do Teste Preliminar

Teste realizado com 1 APK (`byrne.utilities.hashpass_2.apk`), 3 ferramentas, timeout 120s, 1 rep.

**Problemas encontrados e corrigidos**:

1. **`RV_APKS_DIR` obrigatório com skip flags**: Quando `--skip-monitors --skip-instrument --skip-static` estão ativos, o pré-processador não produz `instrumented_apks/`, e o rv-experiment faz fallback para o `apks_dir` configurado. Sem `RV_APKS_DIR` explícito, o entrypoint não passa `--apks-dir` ao CLI, que usa o default `./apks_examples/` (inexistente ou vazio no container). **Correção**: Adicionado `RV_APKS_DIR: "/opt/rvsec/rv-android/apks"` ao compose.

2. **APK de teste fora do dataset estratificado**: O primeiro APK do dataset original (`biz.gyrus.yaab_30.apk`) não estava na seleção estratificada de 100 APKs. O filtro listava um APK que não existia no volume. **Correção**: Usar APK da lista estratificada.

3. **Permissão em results/**: Container roda como root, criando arquivos com owner root. Para limpar, necessário `docker run --rm alpine rm -rf`. **Mitigação**: documentado no troubleshooting.

4. **Build Docker falhou na primeira tentativa**: Package `br.unb.cic.rvsmart.output` (com `TraceWriter`, `MetricsCollector`, `RvTrack`) não estava no repo remoto. Causa: código desenvolvido em outra máquina sem push. **Correção**: Push do código faltante, rebuild OK na segunda tentativa.

5. **`RVSMART_METRICS` não emitida em timeout**: Quando o rvsmart é interrompido por timeout (comportamento esperado), a linha summary `RVSMART_METRICS:` não é escrita — ela é emitida no shutdown graceful que não ocorre em kill. **Impacto**: `rvsmart_metrics.json` não é gerado. **Mitigação**: O trace file contém dados JSON por iteração muito mais ricos que o summary — toda a análise da validação deve usar o **trace file** como fonte primária, não o metrics JSON.

6. **Formato do trace file do rvsmart**: Cada linha é um JSON com campos detalhados por iteração:
   ```json
   {
     "iteration": 128, "elapsed_s": 116.1, "activity": "HashPassActivity",
     "action_type": "RESTART", "action_source": "algorithm",
     "hash": "f9eb320a", "unique_states": 4, "saturation_rate": 0.6,
     "score_tier": 4, "action_had_effect": false, "retries": 2,
     "scores": {"coverage": 100, "component": 25, "mop": 500, "wtg": 0, "decay": 0, "total": 627, "stochastic": true, "confirmed": 2},
     "widget_class": "", "capture_ms": 0, "exec_ms": 128, "scoring_ms": 3, "total_ms": 2626
   }
   ```
   Dados disponíveis para análise: action_type, scores breakdown, timing (capture/exec/scoring/total ms), hash de tela, activity, widget_class, saturation_rate, stochastic flag, retries.

### 3.6 Resultado do Teste

Teste com `byrne.utilities.hashpass_2.apk`, 120s timeout, 1 rep, 3 ferramentas:

**Task 1 — rvsmart:mvp**: Completou via timeout (esperado)
- 128 iterações em ~116s efetivos (~1.1 it/s)
- 4 unique_states, 1 activity (HashPassActivity)
- Methods: 35.71% (5/14), Activities: 100%, MOP: 100%
- Violações MOP detectadas: MessageDigestSpec (MD5 em vez de SHA-256/384/512)
- Scoring ativo: tiers 2-4, scores coverage=100, mop=500, wtg=0
- Ações: CLICK, SET_TEXT, SCROLL, BACK, RESTART
- `rvsmart_metrics.json` NÃO gerado (timeout interrompeu antes do summary)

**Task 2 — ape**: Completou via timeout
- Methods: 57.14% (8/14), Activities: 100%, MOP: 100%
- 0 violações MOP — APE não triggou o path de MessageDigest com MD5
- Cobertura de métodos superior ao rvsmart (+21.43pp)

**Task 3 — fastbot**: Completou via timeout
- Methods: 21.43% (3/14), Activities: 100%, MOP: 50%
- 0 violações MOP
- Menor cobertura das 3 ferramentas

**Resumo comparativo (1 APK, 120s)**:

| Ferramenta | Act% | Meth% | MOP% | Violações |
|-----------|------|-------|------|-----------|
| rvsmart:mvp | 100% | 35.71% | 100% | 2 (MessageDigestSpec: MD5) |
| ape | 100% | 57.14% | 100% | 0 |
| fastbot | 100% | 21.43% | 50% | 0 |

**Observações do teste**:
- RVSmart detectou violações que APE/FastBot não — exploração guiada para MOP paths
- APE cobriu mais métodos — exploração mais ampla
- FastBot ficou atrás em cobertura — throttle alto (500ms) pode limitar
- Todos completaram sem erros — pipeline Docker funcional
- Tempo total: ~9min (3 tasks × ~3min cada: boot + exec + cleanup)

## 4. Protocolo de Validação

### Princípios

- **Rigor**: Cada anomalia é investigada até a causa raiz
- **Quantitativo**: Todas as afirmações acompanhadas de números exatos
- **Comparativo**: RVSmart sempre comparado com APE e FastBot no mesmo APK
- **Reprodutível**: Dados brutos preservados, análise scriptada

### 4.1 Coleta de Dados

Após conclusão dos 6 containers, consolidar:

```bash
# Unificar resultados
python scripts/merge_parallel_results.py \
  --results-dirs data/results/cmp01 data/results/cmp02 ... data/results/cmp06 \
  --output data/results/consolidated/
```

Arquivos consolidados esperados:
- `summary.csv` — 1 linha por (APK × tool × rep): status, duração, métricas agregadas
- `coverage.csv` — 1 linha por (APK × tool × rep × método): cobertura por método
- `errors.csv` — 1 linha por violação MOP detectada
- `performance.csv` — tempos de execução

**Fontes primárias de dados por ferramenta**:

| Fonte | rvsmart | ape | fastbot |
|-------|---------|-----|---------|
| **Trace file** | JSON por iteração (riquíssimo) | Binário Monkey | Binário Monkey |
| **Logcat** | RVSEC + RVSEC-COV tags | RVSEC + RVSEC-COV tags | RVSEC + RVSEC-COV tags |
| **rvsmart_metrics.json** | NÃO gerado em timeout | N/A | N/A |

> **IMPORTANTE**: O `rvsmart_metrics.json` **NÃO é gerado** quando a execução termina por timeout
> (que é o caso normal). A linha `RVSMART_METRICS:` é emitida no shutdown graceful, que não ocorre
> quando o processo é killed. Toda análise do rvsmart deve usar o **trace file** como fonte
> primária — ele contém 1 JSON por iteração com scores, actions, timing, hashes, etc.

### 4.2 Área 1 — Resumo Executivo

**Tabela principal** (1 linha por APK, colunas por ferramenta):

| APK | Tool | Rep1 its | Rep2 its | it/s | Act% | Meth% | MOP% | Errs | Status |
|-----|------|----------|----------|------|------|-------|------|------|--------|

Métricas:
- **its**: Iterações totais (rvsmart: `total_iterations` do metrics JSON; ape/fastbot: contagem de eventos no trace)
- **it/s**: Iterações por segundo
- **Act%**: Percentual de activities visitadas (do total de activities no JSON de análise estática)
- **Meth%**: Percentual de métodos chamados (do total de métodos monitorados)
- **MOP%**: Percentual de MOPs (monitored operations) triggadas
- **Errs**: Número de violações MOP detectadas

**Diagnóstico por APK**: Classificar cada APK em:
- OK: Todas as 3 ferramentas executaram normalmente
- ANOMALIA: Comportamento inesperado em >= 1 ferramenta
- FALHA: >= 1 ferramenta crashou ou não produziu resultados

### 4.3 Área 2 — Bugs e Anomalias

Para cada anomalia identificada:

```
### Anomalia #N: [título descritivo]
- **APK**: nome do APK
- **Ferramenta**: qual(is) ferramenta(s) afetada(s)
- **Sintoma**: Descrição observável (ex: "190K SKIPs a 646 it/s")
- **Sequência de eventos**: Timeline do que aconteceu (com timestamps do logcat)
- **Causa raiz**: Análise do código-fonte que explica o comportamento
- **Métricas quantitativas**: Números exatos que evidenciam o problema
- **Impacto**: Como afeta a cobertura/resultados
- **Severidade**: Crítico / Alto / Médio / Baixo
- **Recomendação**: Correção sugerida
```

Tipos de anomalia a investigar:
1. **SKIP storms**: Iterações altas sem progresso (unique_states estagnado)
2. **Empty traces**: Tool executou mas não produziu saída
3. **Crash loops**: Restarting repetidos sem exploração
4. **Coverage plateau**: Cobertura estagna muito cedo (<30s)
5. **Métricas ausentes**: `metrics_unavailable` no rvsmart
6. **Divergência entre reps**: Rep1 e Rep2 com resultados muito diferentes
7. **Tempo de execução anômalo**: Tool termina muito antes do timeout
8. **Violações MOP perdidas**: Tool A detecta, Tool B não — por quê?

### 4.4 Área 3 — Cobertura de Código

**Tabela comparativa por APK**:

| APK | rvsmart Meth | ape Meth | fastbot Meth | rvsmart MOP% | ape MOP% | fastbot MOP% |
|-----|-------------|---------|-------------|-------------|---------|-------------|

**Progressão temporal** (requer parsing de timestamps no logcat):

Para cada APK e ferramenta, extrair cobertura acumulada em:
- t=30s, t=60s, t=120s, t=180s, t=300s, t=600s
- Identificar: quando cada ferramenta atinge 50%, 80%, 90% da cobertura final
- Ferramentas que saturam cedo vs. as que continuam descobrindo

**MOP violations por especificação**:
- Agrupar por spec (ex: `JCA.InsecureRandom`, `JCA.WeakHash`)
- Comparar: quais specs cada ferramenta consegue triggar
- Specs que nenhuma ferramenta trigga — por quê?

**Análise delta entre ferramentas**:
- Métodos que SÓ rvsmart encontra (e vice-versa)
- Métodos que TODAS encontram (core path)
- Métodos que NENHUMA encontra (deep paths)

### 4.5 Área 4 — Distribuição de Ações

**RVSmart** (extrair do `rvsmart_metrics.json` — campo `actions.by_type`):

Por APK, tabela completa com TODOS os tipos de ação:

| APK | CLICK | LONG_CLICK | SCROLL | BACK | RESTART | SKIP | TEXT_INPUT | SWIPE | OTHER | Total | Valid% |
|-----|-------|------------|--------|------|---------|------|-----------|-------|-------|-------|--------|

Análise detalhada:
- Contagem absoluta e % de cada `action_type`
- `valid_rate` — ações aceitas pelo dispositivo vs. rejeitadas
- Ações por widget class (ex: quantos CLICKs em Button vs. TextView vs. ImageView)
- Ações por activity — qual activity recebe mais interações
- Ratio exploração/navegação: (CLICK + LONG_CLICK + SCROLL + TEXT_INPUT) / (BACK + RESTART)
- Detecção de padrões degenerados: SKIP > 50%, BACK > 40%, RESTART consecutivos

**APE e FastBot** (extrair do trace file):
- Parsing dos eventos do trace (ambos usam formato Monkey-compatible)
- Contagem por tipo de evento: tap, motion, key, rotation, etc.
- Se trace parsing não é viável: extrair do logcat (eventos ADB)

**Comparação cross-tool**:
- Diversidade de ações: quantos tipos diferentes cada ferramenta usa
- Eficiência: ações produtivas (que mudam estado) vs. improdutivas
- Padrões de recovery: como cada ferramenta reage quando presa

### 4.6 Área 5 — Cobertura de UI

**Métricas por APK e ferramenta**:

| APK | Tool | unique_states | activities_visited | activities_total | act_coverage% | revisit_rate | elements_discovered | elements_interacted |
|-----|------|--------------|-------------------|-----------------|--------------|-------------|--------------------|--------------------|

**Per-activity detail** (por APK × ferramenta):

| Activity | visits | % total iters | unique_hashes | actions_dominant | first_visit_t | last_visit_t |
|----------|--------|--------------|--------------|-----------------|--------------|-------------|

- Activities visitadas apenas 1 vez (exploração superficial)
- Activities com muitas visitas (stuck loop? ou hub central?)
- Activities nunca visitadas — requerem navegação profunda?

**Per-screen detail** (top 10 telas mais visitadas por APK):

| Screen hash | visits | % total | activity | actions por tipo | anomalias |
|------------|--------|---------|----------|-----------------|-----------|

- Telas com visitas excessivas sem ações produtivas
- Telas com alta diversidade de ações (exploração ativa)
- Telas visitadas apenas 1 vez (one-shot exploration)

**Element coverage** (RVSmart-específico do metrics JSON):
- `element_coverage.types_seen` — tipos de widgets encontrados
- `element_coverage.type_counts` — distribuição por tipo
- `element_coverage.interactive_elements` — elementos clicáveis descobertos vs. interagidos
- Proporção elementos interagidos / elementos descobertos = eficiência de exploração

**Cross-tool UI coverage delta**:
- Activities que SÓ uma ferramenta alcança
- Screens (hashes) únicos por ferramenta
- Profundidade de navegação: max distância da MainActivity por ferramenta

### 4.7 Área 6 — Plateau, Stochastic e Recovery (RVSmart-específico)

Estas métricas são específicas do RVSmart e revelam a saúde da estratégia de exploração:

- **Stochastic selection %**: Frequência com que o rvsmart recorre a seleção aleatória (vs. guiada)
- **Plateau detection**: Períodos sem novos `unique_states` — duração e frequência
- **Max consecutive RESTARTs**: Reinícios consecutivos sem progresso
- **Max consecutive same-hash**: Iterações na mesma tela
- **OOA (Out of Actions) %**: Percentual de iterações sem ação válida disponível
- **Score tier distribution**: Se scoring está ativo — distribuição Tier 1-4
- **Saturation rate**: Velocidade com que cobertura estabiliza

### 4.8 Área 7 — Score Breakdown (RVSmart-específico)

Se scoring está ativo no rvsmart:mvp:
- Por scorer: mean, median, max, % de APKs com score > 0
- Comparação entre scorers: qual contribui mais para exploração
- WTG scorer status (depende de análise estática)
- Correlação score vs. cobertura final — score alto = cobertura alta?

### 4.9 Área 8 — Consistência Interna de Métricas

Cruzar dados auto-reportados pelo rvsmart com dados observáveis externamente para detectar bugs de rastreamento:

**Métricas auto-reportadas vs. observáveis**:

| Métrica rvsmart | Fonte interna | Fonte externa | Como cruzar |
|-----------------|--------------|---------------|-------------|
| `total_iterations` | metrics JSON | Contagem de linhas de ação no trace | Devem ser iguais |
| `unique_states` | metrics JSON | Hashes únicos no trace | Devem ser iguais |
| `activities_discovered` | metrics JSON | Activities no logcat (RVSEC-COV) | Internas >= externas |
| `execution_time_s` | metrics JSON | `task.tool_execution_duration` (platform) | Diferença < 5s |
| `actions.by_type` totais | metrics JSON | Contagem no trace | Devem ser iguais |
| `element_coverage` | metrics JSON | Elementos no trace/logcat | Consistente |

**Anomalias a detectar**:
- Iterations reportadas >> iterations no trace = contador bugado
- Unique states reportados mas coverage externa zerada = monitor não captura
- execution_time_s << timeout mas task marcada como timeout = bug no timer
- Activities reportadas mas sem nenhum método coberto nelas = visitou mas não interagiu

### 4.10 Área 9 — Análise de Trace File e Erros Silenciosos

Parsing profundo do trace file (stdout do processo Java) para cada task do rvsmart:

**Buscar padrões de erro**:
```
grep -i "exception\|error\|null\|fatal\|stacktrace\|caused by" trace_file
```

Classificar por tipo:
- `NullPointerException` — bug no rvsmart (acessando estado não inicializado)
- `OutOfMemoryError` — vazamento de memória no agente
- `ClassNotFoundException` — problema de classpath/JAR
- `SecurityException` — permissão negada no dispositivo
- `ActivityNotFoundException` — tentou lançar activity inexistente
- `IllegalStateException` — estado inconsistente no app ou no rvsmart
- `SocketTimeoutException` — timeout de rede (modo hybrid/LLM)

**Quantificar por APK**:

| APK | Exceptions | Tipos | Primeira ocorrência (t) | Impacto na exploração |
|-----|-----------|-------|------------------------|----------------------|

- APKs com exceptions mas task COMPLETED = erros silenciosos (bug mais perigoso)
- Exceptions que se repetem = bug sistemático vs. edge case

### 4.11 Área 10 — Análise de Logcat (Crashes e ANRs)

**IMPORTANTE**: O `LogcatComponent` da plataforma captura apenas tags `RVSEC` e `RVSEC-COV`. Para análise de crashes/ANRs, é necessário captura adicional de logcat com tags extras ou logcat completo. Duas opções:

**Opção A — Logcat paralelo via script externo** (recomendado):
Executar `adb logcat` em paralelo dentro do container, capturando tags adicionais:
```bash
# No entrypoint ou wrapper script, antes da execução:
adb logcat -v threadtime *:E AndroidRuntime:E ActivityManager:W System.err:W > /results/full_logcat.txt &
```

**Opção B — Análise post-hoc do trace file**:
O trace file do rvsmart (stdout) pode conter mensagens de erro do app_process. Também o logcat filtrado existente pode conter crash info se o app crasha durante chamada monitorada.

**Padrões críticos a buscar (no trace file + logcat disponível)**:
- `FATAL EXCEPTION` — crash no app sob teste ou no rvsmart
- `ANR in` — Application Not Responding
- `Force finishing activity` — sistema forçou fechamento
- `Process crashed` / `has died` / `killing` — processo morreu

**Por APK e ferramenta**:

| APK | Tool | FATAL | ANR | Force finish | Process crash | Total |
|-----|------|-------|-----|-------------|--------------|-------|

- Se rvsmart causa mais crashes que ape/fastbot no mesmo APK = bug na interação
- Se app crasha com todas as ferramentas = app frágil (não é bug do rvsmart)
- ANRs frequentes = rvsmart gerando eventos rápido demais? Ou app lento?
- Correlação crash → RESTART: o rvsmart detecta o crash e faz recovery?

### 4.12 Área 11 — Timing Anomalies

**Distribuição de duração por ferramenta**:

| Faixa | rvsmart | ape | fastbot |
|-------|---------|-----|---------|
| < 30s (crash?) | ? | ? | ? |
| 30s - 300s (terminou cedo) | ? | ? | ? |
| 300s - 590s (terminou antes) | ? | ? | ? |
| 590s - 610s (timeout normal) | ? | ? | ? |
| > 610s (timeout excedido) | ? | ? | ? |

**Anomalias a investigar**:
- **Término precoce** (< 300s com exit code 0): rvsmart achou que explorou tudo? App fechou e não conseguiu reabrir? Bug no loop principal?
- **Timeout excedido** (> 610s): bug no mecanismo de timeout do rvsmart ou da plataforma?
- **Divergência entre reps**: rep1 terminou em 50s, rep2 em 600s = comportamento não-determinístico
- **Tempo real vs. reportado**: `execution_time_s` (metrics) vs. duração da task (platform) — discrepância > 5s indica overhead ou bug

### 4.13 Área 12 — Determinismo e Variância entre Repetições

Para cada APK × ferramenta, comparar rep1 vs. rep2:

**Métricas de variância**:

| APK | Tool | CV(iterations) | CV(unique_states) | CV(Meth%) | CV(MOP%) | Δ activities |
|-----|------|---------------|-------------------|-----------|----------|-------------|

Onde CV = coeficiente de variação (std/mean × 100%)

**Classificação**:
- CV < 10%: Altamente determinístico (esperado para DFS puro do rvsmart)
- CV 10-30%: Variância aceitável (elementos aleatórios)
- CV > 30%: Anomalia — investigar causa

**Análise específica para rvsmart**:
- DFS puro deveria ser quase determinístico (mesmo seed → mesmo caminho)
- Se CV alto: seed não fixada? Race condition no parsing de UI? Estado do emulador diferente?
- Comparar: quais APKs têm alta variância em rvsmart mas baixa em ape/fastbot (ou vice-versa)

**Análise detalhada para APKs com CV > 30%**:
- Diff do trace file: onde as execuções divergem
- Timestamp da divergência: início (boot diferente) vs. meio (decisão diferente)
- Activities diferentes entre reps: uma rep alcançou área que outra não

### 4.14 Área 13 — Utilização da Análise Estática

Verificar se o rvsmart efetivamente usa os dados de análise estática:

**Dados disponíveis no JSON de SA** (por APK):
- Activities declaradas no manifest
- Métodos monitorados (MOPs)
- Grafo de transições (WTG)
- Classes e métodos da aplicação

**Como verificar utilização**:
1. Comparar activities visitadas pelo rvsmart vs. activities no JSON de SA
   - Se rvsmart visita activities que NÃO estão no JSON = descoberta dinâmica (bom)
   - Se rvsmart NÃO visita activities que ESTÃO no JSON = não usou os dados (bug?)
2. Correlação: APKs com mais dados de SA → mais cobertura no rvsmart?
   - Se não há correlação = SA não está sendo usada efetivamente
3. Verificar no trace se há mensagens de carregamento de SA:
   ```
   grep -i "static.analysis\|loaded.*json\|activities.*found" trace_file
   ```
4. APKs sem JSON de SA (se houver): como rvsmart se comporta? Fallback funciona?

### 4.15 Área 14 — Ordem de Execução e Contaminação entre Tasks

A plataforma executa tasks sequencialmente no mesmo container. Verificar se há contaminação:

**Risco**: task N deixa estado residual que afeta task N+1 (mesmo APK, ferramenta diferente)

**Como detectar**:
- Comparar resultados de uma ferramenta quando roda 1ª vs. 2ª vs. 3ª no mesmo APK
- Se ordem `rvsmart→ape→fastbot` produz resultados diferentes de `ape→fastbot→rvsmart` = contaminação
- Verificar: emulador é reiniciado entre tasks? APK é reinstalado? Dados do app são limpos?

**Verificações no logcat**:
- Processos residuais: `ps | grep rvsmart` entre tasks
- App state: `pm clear <package>` executado entre tasks?
- Emulador state: boot fresh por task ou reutilizado?

**Análise estatística**:
- Para cada ferramenta: média de Meth% quando é 1ª tool vs. 2ª vs. 3ª
- Se diferença significativa = evidência de contaminação
- Controle: comparar com variância entre reps (que não tem efeito de ordem)

### 4.16 Área 15 — Exit Conditions e Modos de Término

Analisar como cada task terminou para detectar padrões anômalos:

**Classificação de exit conditions**:
- **TIMEOUT** (esperado): Ferramenta rodou até o timeout da plataforma — comportamento normal
- **EXIT_OK** (exit code 0, antes do timeout): Ferramenta decidiu parar — exploração completa? Ou bug no loop?
- **EXIT_ERROR** (exit code != 0): Falha explícita — crash, erro de classpath, permissão
- **KILLED**: Processo morto externamente — OOM killer, emulador crash

**Por ferramenta**:

| Exit condition | rvsmart | ape | fastbot |
|---------------|---------|-----|---------|
| TIMEOUT | ? | ? | ? |
| EXIT_OK (< timeout) | ? | ? | ? |
| EXIT_ERROR | ? | ? | ? |
| KILLED | ? | ? | ? |

**Investigar cada EXIT_OK precoce**:
- Quanto tempo rodou? (se < 60s de um timeout de 600s = muito suspeito)
- O que diz o trace file? Mensagem de "exploration complete"? Ou nada?
- O app crashou e o rvsmart não conseguiu reabrir?
- Comparar com mesma APK em ape/fastbot — eles também terminam cedo?

### 4.17 Área 16 — Comparação com Critérios de Validação

Tabela de validação geral:

| Métrica | Esperado | rvsmart | ape | fastbot | Status |
|---------|----------|---------|-----|---------|--------|
| Tasks completadas | 100% | ? | ? | ? | |
| Métricas disponíveis | 100% | ? | N/A | N/A | |
| Act% média | >30% | ? | ? | ? | |
| Meth% média | >10% | ? | ? | ? | |
| MOP% média | >5% | ? | ? | ? | |
| Crash rate | <5% | ? | ? | ? | |
| Empty trace rate | <5% | ? | ? | ? | |
| Rep variance (CV) | <30% | ? | ? | ? | |

### 4.18 Área 17 — Conclusão

Estrutura obrigatória:

1. **O que realmente melhorou** (rvsmart vs. ape/fastbot, com números)
2. **O que ficou igual** (métricas comparáveis)
3. **O que piorou** (pontos onde rvsmart perde)
4. **Bugs encontrados** (lista com severidade e referência à Área 2)
5. **Recomendações** (priorizadas por impacto)
6. **Próximos passos** (o que testar/corrigir antes do experimento formal)

## 5. Scripts de Análise

### 5.1 Consolidação de Resultados

```bash
# Script para unificar resultados dos 6 containers
python scripts/consolidate_comparison.py \
  --results-dirs data/results/cmp{01..06} \
  --output data/results/comparison_consolidated/
```

### 5.2 Geração de Relatório

```bash
# Script para gerar relatório de validação
python scripts/comparison_report.py \
  --consolidated data/results/comparison_consolidated/ \
  --static-analysis data/apks/ \
  --output docs/20260309_rvsmart_comparacao_resultados.md
```

## 6. Checklist Pré-Execução

- [ ] Imagem Docker rebuilada (`phtcosta/rvandroid:0.8.0`)
- [ ] 100 APKs + 100 JSONs copiados para `data/apks/`
- [ ] Arquivos de batch gerados (`batch_00.txt` .. `batch_05.txt`)
- [ ] `docker-compose.comparacao.yml` criado e validado
- [ ] Teste rápido com 1 container + 1 APK + 1 ferramenta
- [ ] Espaço em disco suficiente (estimativa: ~50GB para 600 tasks)
- [ ] `/dev/kvm` acessível

## 7. Checklist Pós-Execução

- [ ] Todos os 6 containers finalizaram
- [ ] Verificar tasks com status != COMPLETED
- [ ] Consolidar resultados
- [ ] Executar protocolo de validação (Áreas 1-9)
- [ ] Documentar bugs encontrados
- [ ] Gerar relatório final
