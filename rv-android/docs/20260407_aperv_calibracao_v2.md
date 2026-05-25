# APE-RV: Plano de Calibracao MACRO v2 via Optuna em GCP

**Data**: 2026-04-07 (atualizado 2026-04-13)
**Status**: Pronto para implementacao — budget aprovado, JAR selecionado
**Dependencias**: ~~MadEvolve (melhor mutante)~~ RESOLVIDO: baseline (`5bd97f7`), VMs GCP
**Refs**: `docs/20260318_rvape_calibracao.md` (plano v1), `openspec/changes/archive/2026-04-04-gh9-docker-calibration/` (infra), `data/results/_analysis/final_experiment_report.md` (resultado MadEvolve)

---

## 1. Motivacao

A calibracao MACRO v1 (130 trials, 14 params, 30 APKs, 1 rep) produziu params que
scoraram 38.99 no subset de calibracao mas **regrediram** no dataset completo:

| Variante | Dataset | Method% | MOP% | Score |
|----------|---------|---------|------|-------|
| sata_mop_v1 (defaults) | 169 APKs (exp2) | 28.35 | 37.02 | 32.69 |
| **sata_mop_cal (calibrado v1)** | **169 APKs (exp4)** | **27.55** | **35.96** | **31.76** |
| sata_mop_comp (code changes gh9) | 169 APKs (exp6) | 28.96 | 38.61 | 33.78 |

A calibracao v1 perdeu **-0.93pp** vs defaults. A conclusao anterior foi que "o problema
eh estrutural, nao parametrico" e iniciou-se o MadEvolve (evolucao de codigo via LLM).

Este plano propoe uma segunda tentativa de calibracao, corrigindo os problemas
metodologicos da v1, para ser aplicada sobre o melhor mutante do MadEvolve.

---

## 2. Analise de por que a calibracao v1 falhou

### 2.1 Causa 1 — Overfitting ao subset de 30 APKs

Os 30 APKs foram selecionados por terem alto gap entre tools (37% com gap >= 10pp,
gap medio 9.5pp). Sao os APKs mais "improvaveis" — onde mudancas de parametros TEM
chance de fazer diferenca. No dataset completo de 169 APKs, muitos apps tem coverage
determinada pela estrutura do app (apps que crasham, single-screen, apps que precisam
de auth), nao pelos parametros de exploracao.

O Optuna otimizou para os APKs atipicos, nao para a populacao representativa.

### 2.2 Causa 2 — Ruido de 1 repeticao

Cada trial avaliou cada APK apenas 1 vez. Android testing tem alta variancia — o
mesmo app com os mesmos parametros produz resultados diferentes em cada execucao.
Fontes de variancia: timing do emulador, nondeterminismo do app, estado de rede,
ordem de execucao de threads.

**Evidencia**: Na `aperv_comparacao_consolidated.csv`, APKs individuais variam
10-15pp entre 2 reps da MESMA tool com os MESMOS parametros:
- `com.quaap.launchtime`: 37.16% vs 42.42% (ape, reps 1 e 2) = **+5.3pp**
- `com.aptasystems.dicewarepasswordgenerator`: 53.77% vs 39.62% (ape) = **-14.2pp**

Com 1 rep x 30 APKs, o score de cada trial eh dominado por execucoes lucky/unlucky.
O Optuna encontrou params que tiveram "sorte" no subset, nao params genuinamente melhores.

### 2.3 Causa 3 — Muitos parametros para o sample size

14 params com 30 APKs x 1 rep = 30 pontos por trial. A razao pontos/params eh apenas
2.1:1. O TPE precisa de muito mais dados por parametro para distinguir sinal de ruido.
Com 30 pontos e 14 dimensoes, o Optuna encontrou correlacoes espurias.

### 2.4 Causa 4 — Scoring com trimmed mean em amostra pequena

Trimmed mean 10% em 30 APKs = cortar 3 extremos de cada lado. Num sample pequeno, os
extremos podem ser justamente os APKs mais informativos (onde params fazem diferenca).
A trimming mascara tanto falhas quanto sucessos reais.

### 2.5 Causa 5 — Parametros de baixo impacto no espaco de busca

`do_fuzzing`, `do_back_to_trivial_activity`, `max_states_per_activity`, e
`max_extra_priority_aliased_actions` tem impacto marginal na selecao de acoes —
adicionam dimensoes sem sinal util, diluindo a capacidade do TPE.

### 2.6 Validacao cruzada com MadEvolve

O MadEvolve (evolucao de codigo, rodando localmente com 2 ilhas) confirma estes
problemas:

- **Variancia entre subsets**: Island 0 baseline = 37.22 fitness vs Island 1 baseline =
  32.61 (mesmo codigo, subsets diferentes de 50 APKs cada). Diferenca de **4.6pp** so
  por amostragem — comparavel ao "ganho" inteiro da calibracao v1 (38.99 - 35.34 = 3.65pp).

- **MOP weights sao criticos**: As mutacoes mais bem-sucedidas (staleness tiebreaker,
  MOP shortcut, isTrivialActivity MOP fast-path) todas interagem com como os MOP weights
  influenciam a selecao de acoes. Isto reforça que os 4 MOP weights devem ser o foco
  principal da calibracao.

- **Threshold de priority**: A mutacao "MOP shortcut" (fitness 37.27) faz bypass do
  epsilon-greedy quando `action.getPriority() > 32`. Isso implica que os MOP weights
  precisam ser altos o suficiente para que as acoes ultrapassem este threshold.

---

## 3. Design da calibracao v2

### 3.1 Reducao de parametros: 14 → 10

Baseado na analise do codigo Java (Config.java:146-149, SataAgent.java:1236-1293,
StatefulAgent.java:952-1033, State.java:greedyPickLeastVisited, MopScorer.java:38-65):

**MANTER (10 params):**

| # | Grupo | Parametro | Range | Step | Default | Impacto | Ref |
|---|-------|-----------|-------|------|---------|---------|-----|
| 1 | MOP | `mop_weight_direct` | [100, 1000] | 50 | 500 | CRITICO | StatefulAgent:1236 |
| 2 | MOP | `mop_weight_transitive` | [50, 600] | 50 | 300 | CRITICO | MopScorer:38 |
| 3 | MOP | `mop_weight_activity` | [0, 300] | 25 | 100 | ALTO | MopScorer:39 |
| 4 | MOP | `mop_weight_wtg` | [0, 600] | 50 | 200 | MEDIO-ALTO | MopScorer:53-65 |
| 5 | Exploration | `default_epsilon` | [0.01, 0.20] | — | 0.05 | ALTO | SataAgent:190-203 |
| 6 | Exploration | `graph_stable_restart_threshold` | [30, 300] | 10 | 100 | ALTO | StatefulAgent:952-957 |
| 7 | Exploration | `state_stable_restart_threshold` | [20, 150] | 10 | 50 | MEDIO-ALTO | StatefulAgent:1026-1033 |
| 8 | Coverage | `coverage_boost_weight` | [0, 500] | 25 | 100 | MEDIO | StatefulAgent:1272-1277 |
| 9 | Timing | `throttle_ms` | [100, 400] | 25 | 200 | MEDIO | StatefulAgent:1319-1338 |
| 10 | Timing | `throttle_for_activity_transition` | [200, 800] | 50 | 500 | MEDIO | StatefulAgent:1334-1335 |

Os params de timing (9-10) nao mudam qual acao eh selecionada, mas mudam quantas
acoes cabem no timeout — com timeout fixo, menor throttle = mais acoes = mais
coverage. Esse efeito eh especialmente relevante se reduzirmos o timeout de calibracao
para 300s (ver secao 3.8).

**REMOVER (4 params — fixar em valores empiricos):**

| Parametro | Fixar em | Motivo |
|-----------|----------|--------|
| `max_extra_priority_aliased_actions` | 5 | Baixo impacto, so apps com UI repetitiva (listas/grids). |
| `max_states_per_activity` | 15 | Limite de memoria, raramente bottleneck. |
| `do_fuzzing` + `fuzzing_rate` | false/0 | Impacto marginal. Top 10 da v1: todos com fuzzing=false. |
| `do_back_to_trivial_activity` | false | Heuristica de fallback, raramente ativada. |
| `trivial_activity_rank_threshold` | 3 | So multi-activity apps, default razoavel. |

**Organizacao dos 10 params por grupo funcional:**
- **MOP guidance (4)**: como guiar em direcao a operacoes monitoradas
- **Exploration (3)**: quao agressivamente explorar vs exploitar
- **Coverage (1)**: como priorizar widgets nao testados
- **Timing (2)**: quantas acoes cabem no timeout

### 3.2 Mais APKs: 30 → 100

- Selecao **estratificada aleatoria** dos 149 APKs viaveis (method >= 5% em alguma tool)
- **SEM** selecao por gap — representar a populacao real, nao os "mais improvaveis"
- 49 APKs restantes servem como **holdout** para medir generalizacao
- Usar `scripts/select_dataset.py` adaptado com seed=42
- Distribuicao por categoria e size_bucket similar ao dataset completo

**Por que 100?** Eh 67% dos 149 APKs viaveis — representativo o suficiente para
generalizar, com holdout grande o bastante (49) para validacao estatistica.

### 3.3 Repeticoes: 1 → 2

- Cada APK roda **2 vezes** por trial (200 tasks por trial)
- Score = media por APK (sobre as 2 reps), depois trimmed mean no vetor de medias
- SNR melhora ~**2.6x** vs v1 (sqrt(160/24) com trimmed mean)
- 3 reps seria ideal mas duplicaria o custo computacional; 2 eh o sweet spot

### 3.4 Trials: 130 → 80

- 10 params × 8x = 80 trials (regra 5-10× para convergencia do TPE)
- `n_startup_trials` = 16 (2 rounds de 8 trials random)
- TPE efetivo: 64 trials guiados (80% eficiencia)
- Convergencia esperada mais rapida com menos dimensoes que a v1 (10 vs 14)

### 3.5 Codebase: baseline (MadEvolve concluido — NO-GO)

**RESOLVIDO (2026-04-13)**: O MadEvolve concluiu com NO-GO para merge de ambas as
ilhas. O experimento final (600s × 169 APKs × 2-3 reps, 2197 tasks, 35h) mostrou que:

- Ambas as ilhas **regrediram** vs baseline: island0 −0.90pp method, −1.74pp MOP;
  island1 −1.05pp method, −1.80pp MOP
- A vantagem de violacoes do island0 (expressiva a 300s) **desapareceu** a 600s
- Causa raiz: mutacoes otimizadas para timeouts curtos comprimem exploracao local,
  impedindo descoberta de areas distantes em runs longos

**JAR a calibrar**: baseline `ape-rv.jar` do commit `5bd97f7` (master).
Nao precisa rebuild — eh o JAR ja em uso em producao.

Ref: `data/results/_analysis/final_experiment_report.md`

### 3.7 Alternativa: timeout de 300s (5 min) na calibracao

Dados comparativos reais entre 180s e 600s (`baseline_180s` vs `exp2`, mesmos 169 APKs):

| Timeout | Method% | MOP% | Score | Fonte |
|---------|---------|------|-------|-------|
| 180s (3 min) | 24.40 | 33.99 | 29.20 | baseline_180s (real, 3 reps, 169 APKs) |
| 300s (5 min) | ~25.5-26.5 | ~34.9-35.6 | ~30.2-31.1 | estimado (interpolacao) |
| 600s (10 min) | 28.35 | 37.02 | 32.69 | exp2 (real, 2 reps, 169 APKs) |

**Delta 180s → 600s**: +3.95pp method, +3.03pp MOP. Mas com diminishing returns — a
maioria da exploracao acontece nos primeiros minutos. Dos 169 APKs, 58 (34%) **nao
ganham nada** com mais tempo (apps simples ou que crasham cedo).

**Impacto no custo** (80 trials, 100 APKs, 2 reps, 2 CPUs/container):

| Timeout | Custo spot | Wall clock (4 VMs) | Reducao vs 600s |
|---------|-----------|--------------------|-----------------| 
| 300s (5 min) | **~$44** | **2.2 dias** | -44% custo, -44% tempo |
| 600s (10 min) | ~$79 | 3.9 dias | referencia |

**Argumento a favor de 300s**: o objetivo da calibracao eh encontrar a **ordenacao
relativa** entre configuracoes de params, nao o score absoluto. Params que exploram
melhor em 300s provavelmente exploram melhor em 600s tambem. Os throttle params se
tornam ainda mais relevantes com timeout curto (cada ms de delay importa mais).

**Argumento contra**: se os params de timing interagem de forma nao-linear com o
timeout (ex: throttle baixo ajuda muito a 300s mas pouco a 600s), a calibracao a
300s pode favorecer throttle muito baixo que nao generaliza para 600s.

**Decisao (atualizada 2026-04-13)**: usar **300s** (5 min) para a calibracao.
Justificativa: melhor custo-beneficio ($44 vs $79), o objetivo eh a ordenacao relativa
entre configuracoes (nao score absoluto), e a validacao final (Fase C) roda a 600s
de qualquer forma. O risco de nao-generalidade dos params de timing eh mitigado pela
validacao.

### 3.8 Funcao objetivo (sem mudanca)

```
score = 0.50 × mop_coverage + 0.50 × method_coverage
```

Mesma do v1 — 50/50 MOP + method, trimmed mean 10%. Mas aplicada sobre medias por APK
(quando ha multiplas reps), nao sobre pontos individuais.

---

## 4. Infraestrutura GCP

### 4.1 Restricao: emulador x86, precisa KVM

O Dockerfile usa `ARCHITECTURE=x86` (`docker/android/Dockerfile:8`):
- **t2a (ARM) NAO funciona** — emulador x86 em ARM requer QEMU, inviavel
- Precisa de VMs x86 com nested virtualization: **n2d** (AMD EPYC, melhor preco)
- APKs + dados de static analysis precisam ser uploaded para as VMs

### 4.2 CPUs por container

O emulador usa `EMU_CORES=2`. O APE-RV roda via `app_process` DENTRO do emulador
(compartilha os 2 cores). O Python rv-platform eh leve (mostly waiting).
O compose atual usa `--cpus 4` e `--memory 10g`.

| CPUs/container | Pro | Contra | Custo relativo |
|----------------|-----|--------|---------------|
| **4 (atual)** | Confortavel, emulador rapido | Caro, menos containers/VM | 100% |
| **3** | Bom headroom para host | 25% menos containers que 4 | 75% |
| **2** | Minimo custo, maximo containers/VM | Zero headroom, risco de lentidao | 50% |

**Nota (2026-04-13)**: 2 CPUs eh provavelmente insuficiente — o emulador usa EMU_CORES=2,
nao sobra headroom para o host OS, Docker, e rv-platform. O compose de producao local
usa 4 CPUs. O smoke test (Fase 0) testara **3 e 4 CPUs** para determinar o minimo viavel.

**Decisao**: testar 3 e 4 CPUs no smoke test (Fase 0) antes de comprometer.

### 4.3 Precos n2d-standard (Iowa/us-central1) — dados reais

| Tipo | vCPUs | RAM | Default/hr |
|------|-------|-----|------------|
| n2d-standard-4 | 4 | 16GB | $0.169 |
| n2d-standard-8 | 8 | 32GB | $0.338 |
| n2d-standard-16 | 16 | 64GB | $0.676 |
| n2d-standard-32 | 32 | 128GB | $1.352 |
| n2d-standard-48 | 48 | 192GB | $2.028 |

Spot: tipicamente 60-70% off default (verificar disponibilidade na regiao).

### 4.4 Cenarios de custo

Cada trial = 100 APKs × 2 reps = 200 tasks × ~680s (600s timeout + 80s boot/cleanup).

**O custo total de compute eh fixo para um dado CPUs/container — nao depende de
quantas VMs.** Mais VMs = menor wall clock, mesmo custo total. Menos VMs = mais
lento mas mais barato em gerenciamento.

**Com timeout de 600s (10 min, default):**

| CPUs/cont | Total vCPU-hours | Custo default | Custo spot (~$0.013/vCPU/hr) |
|-----------|-----------------|--------------|------------------------------|
| 2 | ~6,044 | ~$254 | **~$79** |
| 3 | ~9,067 | ~$381 | **~$118** |
| 4 | ~12,089 | ~$508 | **~$157** |

**Com timeout de 300s (5 min, alternativa):**

| CPUs/cont | Total vCPU-hours | Custo default | Custo spot |
|-----------|-----------------|--------------|-----------|
| 2 | ~3,378 | ~$142 | **~$44** |
| 3 | ~5,067 | ~$213 | **~$66** |
| 4 | ~6,756 | ~$284 | **~$88** |

**Cenarios com wall clock (VMs spot, 4 VMs n2d-standard-16):**

| CPUs/cont | Timeout | Cont/VM | h/trial | Wall clock | Custo spot |
|-----------|---------|---------|---------|------------|-----------|
| 2 | 600s | 8 | 4.7h | **94h (4d)** | ~$79 |
| 2 | 300s | 8 | 2.6h | **53h (2.2d)** | ~$44 |
| 3 | 600s | 5 | 7.5h | **150h (6d)** | ~$118 |
| 3 | 300s | 5 | 4.2h | **84h (3.5d)** | ~$66 |
| 4 | 600s | 4 | 9.4h | **189h (8d)** | ~$157 |
| 4 | 300s | 4 | 5.3h | **106h (4.4d)** | ~$88 |

### 4.5 Recomendacao

**Default (600s)**: 2 CPUs se funcionar (smoke test), **$79 spot**, 4 VMs, 4 dias.
**Budget reduzido (300s)**: 2 CPUs, **$44 spot**, 4 VMs, 2.2 dias.

### 4.6 Opcoes de budget reduzido (se sair do bolso)

Se o budget for mais restrito, ha varias alavancas:

| Ajuste | Impacto no custo | Impacto na qualidade |
|--------|-----------------|---------------------|
| Timeout 300s (vs 600s) | **-44%** | Baixo — ordenacao relativa se mantem |
| 60 trials (vs 80) | -25% | Menor — 6×/param ainda bom para 10 params |
| 80 APKs (vs 100) | -20% | Moderado — menos representativo |
| 1 rep (vs 2) | -50% | **Alto** — volta ao problema do v1 |
| 1 VM (vs 4) | Mesmo custo, 4× mais lento | Zero — so wall clock |

**Cenarios de budget:**

| Cenario | Trials | APKs | Reps | Timeout | CPUs | Custo spot | Wall (4 VMs) |
|---------|--------|------|------|---------|------|-----------|-------------|
| **Minimo** | 60 | 80 | 2 | 300s | 2 | **~$25** | ~1.4d |
| Economico | 80 | 100 | 2 | 300s | 2 | **~$44** | ~2.2d |
| **Recomendado** | 80 | 100 | 2 | 600s | 2 | **~$79** | ~3.9d |
| Full dataset 300s | 80 | 169 | 2 | 300s | 2 | **~$74** | ~3.7d |
| Full dataset 600s | 80 | 169 | 2 | 600s | 2 | **~$133** | ~6.7d |
| Confortavel | 80 | 100 | 2 | 600s | 3 | **~$118** | ~6.3d |

**Observacao sobre 169 APKs**: calibrar com todos os 169 APKs elimina o risco de
overfitting ao subset (causa #1 da falha da v1). Com timeout de 300s, o custo eh
praticamente igual ao de 100 APKs a 600s (~$74 vs ~$79). Sem holdout para validacao
interna, mas o experimento final usara um **dataset independente** (novo conjunto de
APKs nao usado na calibracao), que eh uma validacao mais forte que holdout interno.

**Abaixo de 2 reps nao vale a pena** — reproduz os problemas de ruido da v1.
O timeout de 300s eh a melhor alavanca custo-beneficio.

### 4.7 Custom VM Image — setup uma vez, reusar sempre

A imagem Docker `phtcosta/rvandroid:0.8.0` eh grande (~5-8 GB com layers). Buildar ou
pullar em cada VM desperdicaria horas de setup. Estrategia: criar uma **custom VM image**
(snapshot) com TUDO pre-instalado, e instanciar VMs de calibracao a partir dela.

**O que fica na custom image (imutavel):**
- Ubuntu 22.04 + Docker + docker-compose
- Imagem Docker `phtcosta/rvandroid:0.8.0` pre-pulled (cached no Docker local)
- APKs (567 MB): `/opt/calibration/data/apks/` (inclui SA JSONs `.apk.json`)
- system-broadcast.json: `/opt/calibration/data/system-broadcast.json`
- Scripts de calibracao: `/opt/calibration/scripts/`
- Python 3.12 + uv + optuna + psycopg2 (para PostgreSQL distribuido)

**O que eh montado via volume a cada run (mutavel):**
- `ape-rv.jar` — muda entre MadEvolve mutantes, upload de ~15 MB
- Resultados — diretorio de output por trial

Padrao identico ao `docker-compose.exp6-component-triggering.yml` (validado em prod):
```yaml
volumes:
  - /opt/calibration/data/apks:/opt/rvsec/rv-android/apks:ro
  - /opt/calibration/data/filter.txt:/opt/rvsec/rv-android/filters/filter.txt:ro
  - /opt/calibration/results/trial_N:/opt/rvsec/rv-android/results
  # JAR e broadcast montados via volume (unica coisa que muda entre runs)
  - /opt/calibration/ape-rv.jar:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar:ro
  - /opt/calibration/data/system-broadcast.json:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/system-broadcast.json:ro
```

**Criacao da custom image (uma vez, ~$0.50):**

```bash
# 1. Criar VM de setup (n2d para nested virt, disco 50GB)
gcloud compute instances create cal-setup \
  --project=rvandroid \
  --zone=us-central1-a \
  --machine-type=n2d-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --enable-nested-virtualization

# 2. Instalar Docker + dependencias na VM
gcloud compute ssh cal-setup --zone=us-central1-a --command="
  sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 python3-pip &&
  sudo usermod -aG docker \$USER &&
  sudo systemctl enable docker
"

# 3. Pull da imagem Docker (demora ~10-15 min)
gcloud compute ssh cal-setup --zone=us-central1-a --command="
  sudo docker pull phtcosta/rvandroid:0.8.0
"

# 4. Upload APKs, SA JSONs, filter files, scripts, system-broadcast.json
gcloud compute scp --recurse ./data/apks cal-setup:/opt/calibration/data/apks/
gcloud compute scp ./scripts/calibration_orchestrator.py cal-setup:/opt/calibration/scripts/
gcloud compute scp ./scripts/aperv_parameter_space.py cal-setup:/opt/calibration/scripts/
gcloud compute scp ./scripts/aperv_objective.py cal-setup:/opt/calibration/scripts/
# system-broadcast.json do repo do APE
SB_PATH=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/data
gcloud compute scp $SB_PATH/system-broadcast.json cal-setup:/opt/calibration/data/

# 5. Instalar Python deps para o orchestrator
gcloud compute ssh cal-setup --zone=us-central1-a --command="
  pip install optuna psycopg2-binary pandas scipy pyyaml
"

# 6. Parar a VM e criar custom image
gcloud compute instances stop cal-setup --zone=us-central1-a
gcloud compute images create rvandroid-cal-v2 \
  --project=rvandroid \
  --source-disk=cal-setup \
  --source-disk-zone=us-central1-a \
  --description='APE-RV calibration v2: Docker+rvandroid:0.8.0+APKs+SA+scripts'

# 7. Deletar VM de setup (imagem ja criada)
gcloud compute instances delete cal-setup --zone=us-central1-a --quiet
```

**Instanciar VMs de calibracao (instantaneo):**

```bash
# Criar N VMs spot a partir da custom image — boot em ~30s, zero setup
for i in 0 1 2 3; do
  gcloud compute instances create cal-vm-$i \
    --project=rvandroid \
    --zone=us-central1-a \
    --machine-type=n2d-standard-16 \
    --image=rvandroid-cal-v2 \
    --provisioning-model=SPOT \
    --enable-nested-virtualization
done

# Upload apenas o JAR (~15 MB) para cada VM
for i in 0 1 2 3; do
  gcloud compute scp /path/to/ape-rv.jar cal-vm-$i:/opt/calibration/ape-rv.jar
done

# Monitorar
gcloud compute ssh cal-vm-0 --command="tail -50 /opt/calibration/orchestrator.log"

# Coletar resultados
gcloud compute scp --recurse cal-vm-0:/opt/calibration/results/ ./results/cal_v2/vm0/

# Destruir tudo (para de cobrar)
for i in 0 1 2 3; do
  gcloud compute instances delete cal-vm-$i --zone=us-central1-a --quiet
done
```

**Pre-requisito**: `! gcloud auth login` + `gcloud config set project rvandroid`.

### 4.8 Arquitetura de execucao

#### Como o Optuna distribui nativamente

O Optuna suporta paralelismo multi-maquina nativamente: N processos independentes
conectam ao **mesmo banco de dados** (PostgreSQL/MySQL) e ao **mesmo study_name**.
Cada processo faz `study.ask()` para obter params, executa trials localmente, e
`study.tell()` para reportar o score. O TPE usa TODOS os resultados de TODOS os
workers para sugerir os proximos params — knowledge compartilhado sem orquestracao.

**SQLite NAO funciona** para multi-VM (file-level locking). Precisa de PostgreSQL.

Ref: [Optuna Easy Parallelization](https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/004_distributed.html),
[Distributed Optuna com Neon Postgres](https://neon.com/guides/optuna-hyperprameter-kubernetes)

#### Arquitetura proposta (multi-VM)

```
                    ┌─────────────────┐
                    │  PostgreSQL DB   │
                    │  (Cloud SQL ou   │
                    │   numa das VMs)  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │    VM-0     │   │    VM-1     │   │    VM-2     │  ...
    │ orchestrator│   │ orchestrator│   │ orchestrator│
    │ + N contrs  │   │ + N contrs  │   │ + N contrs  │
    └─────────────┘   └─────────────┘   └─────────────┘
```

Cada VM roda **seu proprio orchestrator** apontando para o mesmo PostgreSQL:

```python
# Em cada VM (mesmo codigo, mesmo study_name):
storage = "postgresql://optuna:pass@DB_IP:5432/optuna"
study = optuna.load_study(study_name="aperv_cal_v2", storage=storage)

while study.trials_dataframe().shape[0] < n_trials:
    trial = study.ask()
    params = suggest_params_v2(trial)
    # Gera docker-compose, roda containers LOCAIS nesta VM, coleta score
    score = run_trial_locally(params)
    study.tell(trial, score)
```

**Vantagens**:
- Cada VM eh autonoma — se uma cair, as outras continuam
- O TPE aprende com TODOS os trials de TODAS as VMs (knowledge compartilhado)
- Zero orquestracao central: nao precisa de SSH entre VMs, nem orchestrator local
- Escala linear: adicionar/remover VMs a qualquer momento

**Mudanca no orchestrator**: trocar SQLite por `RDBStorage` (PostgreSQL URL via
`--storage` flag). O resto do codigo (ask/tell, docker-compose, scoring) fica igual.

**PostgreSQL — Cloud SQL (recomendado)**:

Instancia `db-f1-micro` (1 shared vCPU, 614MB RAM, 10GB SSD):
- ~$9-10/mes se rodar 24/7, billing per-second
- Para uso temporario (~4-8 dias de calibracao): **criar, usar, deletar → ~$2-3 total**
- O Optuna gera ~1MB de dados para 80 trials — storage minimo basta
- Managed: backups automaticos, zero manutencao, acessivel de todas as VMs
- Instancia parada: compute para de cobrar, storage continua (~$0.22/GB/mes)

Criacao via `gcloud`:
```bash
gcloud sql instances create optuna-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --storage-type=SSD \
  --authorized-networks=0.0.0.0/0  # ou restringir aos IPs das VMs

gcloud sql databases create optuna --instance=optuna-db
gcloud sql users create optuna --instance=optuna-db --password=<senha>
```

Connection string para o orchestrator:
```
postgresql://optuna:<senha>@<CLOUD_SQL_IP>:5432/optuna
```

Ref: [Cloud SQL Pricing](https://cloud.google.com/sql/pricing),
[Stop/Start billing](https://docs.cloud.google.com/sql/docs/postgres/start-stop-restart-instance)

**Alternativa gratis**: instalar PostgreSQL numa das VMs (VM-0), as outras conectam
via IP interno. Custo zero extra, mas se VM-0 cair (spot preemption), perde o DB.

#### Opcao single-VM (fallback)

Se o budget nao permitir multi-VM ou PostgreSQL:
- 1 VM n2d-standard-32, orchestrator com SQLite local, 8-16 containers
- 1 trial por vez (80 rounds sequenciais)
- Mais lento mas zero complexidade de distribuicao

### 4.9 Analise de Risco GCP (adicionada 2026-04-14)

Tentativa de validar infraestrutura GCP hoje identificou dois riscos materiais que
podem comprometer a calibracao se nao forem mitigados.

#### 4.9.1 Risco 1: Nested virtualization N2D bugada

**Resultado do teste real (2026-04-14)**:

Criada VM `n2d-standard-16` em `us-central1-a` com `--enable-nested-virtualization`:
- cpuPlatform: AMD Milan ✅
- advancedMachineFeatures.enableNestedVirtualization: true ✅
- **MAS**: CPU flags sem `svm`, `modprobe kvm_amd` falha com "Operation not supported"
- `/dev/kvm` nao existe — emulador Android x86 nao pode rodar
- Stop+start nao resolveu (mesma CPU platform, mesmo bug)
- Log: `kvm_amd: SVM not supported by CPU 3`

**Causa provavel** (fontes: Google issue tracker #172861437, r/googlecloud, StackOverflow 2024-2025):
- GCP as vezes provisiona N2D em hosts sem SVM exposto, mesmo com flag enabled
- Comunidade reporta N2D nested virt como instavel desde 2022
- N1 com Haswell+ eh a familia mais consistentemente reportada como funcionando

**Solucoes testadas sem sucesso**: stop/start, zona alternativa

**Solucoes a tentar**:
1. N2 (Intel Cascade Lake) com `--min-cpu-platform="Intel Haswell"`
2. N1 com Haswell explicito
3. Custom image com licenca `enable-vmx` (pouco documentado, pode forcar exposicao de SVM/VMX)

#### 4.9.2 Risco 2: Stockout de recursos em horario de pico

**Resultado do teste real (2026-04-14, ~14h BRT / ~13h US Central)**:

Tentativas de criar N1/N2 com nested virt em multiplas zonas:

| Zona | Machine type | Resultado |
|------|--------------|-----------|
| us-central1-a/b/c/f | n1-standard-4 + nested virt | stockout / resource_availability |
| us-east1-b/c/d | n1-standard-4 + nested virt | resource_availability |
| us-west1-a/b | n1-standard-4 + nested virt | resource_availability |
| us-central1-a | n1-standard-2 (sem nested virt) | resource_availability |
| us-central1-a | n2-standard-4 + nested virt | resource_availability |
| us-central1-a | **e2-small (controle)** | **OK** |

**Diagnostico**: Problema nao eh da conta/projeto (e2 funcionou). Eh stockout real
do GCP para familias N1/N2 em horario de pico US nas zonas testadas. Afeta tambem
VMs **sem** nested virt, sugerindo alta demanda regional por essas familias.

**Impacto durante calibracao**: Se spot VM for preemptada e nao houver capacidade
para recriar em lote, o orchestrator trava ate vagar recurso.

**Mitigacao**:
1. Tentar em horarios off-peak (madrugada BRT)
2. Usar regioes europeias/asiaticas com menos demanda US (europe-west1, asia-east1)
3. Usar on-demand em vez de spot (menos restritivo para criacao)

#### 4.9.3 Risco 3: Preempcao de spot VMs durante a calibracao

Dados oficiais do GCP (https://cloud.google.com/compute/docs/instances/spot):
- Spot VMs podem ser paradas **a qualquer momento** com 30s de aviso
- Spot VMs sao **forcadamente terminadas apos 24h** (limite duro)
- Taxa tipica de preempcao em us-central1: 5-15%/dia em horario normal, ate 30% em pico

**Calculo para nossa calibracao (4 VMs spot × 3.8 dias)**:

| Metrica | Valor esperado |
|---------|----------------|
| Probabilidade de pelo menos 1 preempcao no periodo | ~95% |
| Numero esperado de preempcoes | 2-5 no total |
| **Recriacoes forcadas pela regra 24h** | **4 VMs × 4 ciclos = 16 recriacoes minimas** |
| Tempo perdido por preempcao (trial em andamento) | ~1-4h de um trial |
| Intervencao humana necessaria | Recriar VMs + relancar orchestrator |

**Mitigacao parcial na arquitetura**:
- Orchestrator com `--resume` recupera trials marcados RUNNING no PostgreSQL
- Outras VMs continuam trabalhando durante uma preempcao isolada
- Progresso perdido por preempcao: so o trial que estava na VM parada

**Mitigacao NAO resolvida pela arquitetura**:
- Limite forcado de 24h obriga recriacao de TODAS as 4 VMs a cada dia
- Se stockout coincidir com necessidade de recriacao, calibracao trava

#### 4.9.4 Comparacao de opcoes com riscos reais

| Config | Custo | Wall clock | Risco de parar | Intervencao estimada |
|--------|:-----:|:----------:|:--------------:|:-------------------:|
| **Spot GCP (plano original)** | ~$66 | 3.8d + preempcoes | **Alto**: 24h forced + ~10%/dia | Recriar VMs 16+ vezes |
| **On-demand GCP** | ~$200 | 3.8d | Muito baixo | Quase zero |
| **Local (64 CPUs)** | **$0** | 5-6d | Zero | Zero |
| **AWS c5.metal spot** | ~$125 | 2-3d | Medio | Recriar 1-2 vezes |

**Premissas**:
- Tempo por trial: 200 tasks × 380s = 21h (300s timeout + overhead)
- 4 VMs com 5 containers (3 CPUs) = 20 trials paralelos
- 80 trials / 20 = 4 rounds ≈ 84h wall clock ≈ 3.5-3.8d
- +8.6% overhead medido no smoke local para 3 CPUs = ~4 dias

#### 4.9.5 Recomendacao com riscos conhecidos

**Rodar calibracao LOCAL** eh a opcao mais segura dado os riscos acima:
- Zero custo vs ~$66-200 GCP
- Zero risco de preempcao vs 95% probabilidade em spot
- Zero risco de stockout vs observado hoje
- Zero necessidade de intervencao vs 16+ recriacoes no spot
- 5-6 dias vs 3.8-4d GCP (trade-off aceitavel vs risco)

**Custo de oportunidade**: maquina local bloqueada por ~6 dias para outros trabalhos.

**GCP ainda faz sentido se**:
1. Bloqueio da maquina local for inviavel
2. On-demand for aprovado (~$200) — elimina risco de preempcao
3. Horario/regiao alternativa resolver stockout antes de lancar

---

## 5. Pre-requisito: APERV_PROPERTY_MAPPING

Os params `mop_weight_wtg` e `coverage_boost_weight` existem no Config.java do APE-RV
mas **NAO estao** no `APERV_PROPERTY_MAPPING` do aperv-tool. Sem este mapeamento, o
orchestrator nao consegue passar esses params via `ape.properties` para o emulador.

**Arquivo**: `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` (linhas 88-90)

```python
# Adicionar APOS mop_weight_activity (linha 90):
    "mop_weight_wtg": "ape.mopWeightWtg",
    "coverage_boost_weight": "ape.coverageBoostWeight",
```

**Verificacao**: `ape.mopWeightWtg` confirmado em Config.java:149 (default 200).
`ape.coverageBoostWeight` confirmado em Config.java:146 (default 100).

---

## 6. Implementacao

### 6.1 Arquivos a modificar

| Arquivo | Mudanca |
|---------|---------|
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | Adicionar 2 mappings ao APERV_PROPERTY_MAPPING |
| `scripts/aperv_parameter_space.py` | +MACRO_PARAMETERS_V2 (10 params) + FIXED_PARAMS_V2 (6 fixos) + suggest/get_default v2 |
| `scripts/aperv_objective.py` | Suportar multi-rep (groupby APK → mean → trimmed mean) |
| `scripts/calibration_orchestrator.py` | +`--reps`, `--param-version`, `--storage`, `--jar-path`, `--broadcast-path`; compose com RV_REPETITIONS/RV_JCA_SPEC |

**Ja prontos (nao precisam de trabalho):**

| Arquivo | Status |
|---------|--------|
| `scripts/select_dataset.py` | Ja existe e foi executado |
| `data/selection/calibration_set_v2.txt` | 100 APKs (seed=42, estratificado) |
| `data/selection/holdout_set_v2.txt` | 67 APKs (complemento) |
| `data/selection/selection_summary.txt` | Metadata da selecao |

### 6.2 Detalhes

#### `aperv_parameter_space.py`

```python
MACRO_PARAMETERS_V2 = [
    # 4 MOP weights (core guidance)
    ParameterDef("mop_weight_direct", "int", 100, 1000, 500, step=50),
    ParameterDef("mop_weight_transitive", "int", 50, 600, 300, step=50),
    ParameterDef("mop_weight_activity", "int", 0, 300, 100, step=25),
    ParameterDef("mop_weight_wtg", "int", 0, 600, 200, step=50),
    # Exploration
    ParameterDef("default_epsilon", "float", 0.01, 0.20, 0.05),
    ParameterDef("graph_stable_restart_threshold", "int", 30, 300, 100, step=10),
    ParameterDef("state_stable_restart_threshold", "int", 20, 150, 50, step=10),
    # Coverage
    ParameterDef("coverage_boost_weight", "int", 0, 500, 100, step=25),
    # Timing
    ParameterDef("throttle_ms", "int", 100, 400, 200, step=25),
    ParameterDef("throttle_for_activity_transition", "int", 200, 800, 500, step=50),
]

FIXED_PARAMS_V2 = {
    "max_extra_priority_aliased_actions": 5,
    "max_states_per_activity": 15,
    "do_fuzzing": "false",
    "fuzzing_rate": 0.0,  # explicito: do_fuzzing=false pode nao zerar no Java
    "do_back_to_trivial_activity": "false",
    "trivial_activity_rank_threshold": 3,
}
```

#### `aperv_objective.py`

```python
# Mudanca: agrupar por APK antes de trimmed mean
apk_means = df.groupby("apk")[["cov_method", "cov_rv_method"]].mean()
avg_method = trim_mean(apk_means["cov_method"].values, TRIM_PROPORTION)
avg_mop = trim_mean(apk_means["cov_rv_method"].values, TRIM_PROPORTION)
```

#### `calibration_orchestrator.py`

Novos CLI flags (todos com defaults backward-compatible):

| Flag | Type | Default | Proposito |
|------|------|---------|-----------|
| `--param-version` | v1/v2 | v1 | Seleciona MACRO_PARAMETERS vs V2 |
| `--reps` | int | 1 | Repeticoes por APK por trial → `RV_REPETITIONS` no compose |
| `--storage` | str | None (SQLite) | URL Optuna storage (PostgreSQL para multi-VM) |
| `--jar-path` | str | None | Path do ape-rv.jar para volume mount (GCP) |
| `--broadcast-path` | str | None | Path do system-broadcast.json para volume mount |

Mudancas no compose gerado:
- Adiciona `RV_REPETITIONS: str(reps)` e `RV_JCA_SPEC: "true"` ao environment
- Quando `--jar-path` fornecido: monta JAR como volume read-only
- Quando `--broadcast-path` fornecido: monta system-broadcast.json como volume read-only

Mudancas no main loop:
- Quando `--param-version v2`: importa `suggest_params_v2` e `FIXED_PARAMS_V2`
- Merge FIXED_PARAMS_V2 em cada trial automaticamente
- `--storage URL`: usa PostgreSQL em vez de SQLite local
- `compute_round_timeout()`: multiplica por `reps`

#### `select_dataset_v2.py`

- Input: 149 APKs viaveis + metadata (`apks_complete.csv`)
- Estratificacao: `category × size_bucket`
- Output: 100 APKs (cal) + 49 APKs (holdout)
- Seed: 42 para reprodutibilidade
- Validacao: chi-squared de distribuicao cal vs populacao total

---

## 7. Execucao

### Fase 0: Custom image + Smoke test de CPUs (~$1-3)

**Objetivo**: (1) criar a custom VM image com tudo pre-instalado, (2) validar que o
emulador funciona em n2d com nested virt, (3) determinar o minimo de CPUs por container
que nao degrada coverage.

#### Passo 0.1 — Criar custom image (~30 min)

Seguir procedimento da secao 4.7. Resultado: imagem `rvandroid-cal-v2` no projeto GCP.
Custo: ~$0.10 (n2d-standard-4 por ~30 min).

#### Passo 0.2 — Criar VM de smoke test

```bash
gcloud compute instances create cal-smoke \
  --project=rvandroid \
  --zone=us-central1-a \
  --machine-type=n2d-standard-16 \
  --image=rvandroid-cal-v2 \
  --enable-nested-virtualization
# n2d-standard-16: 16 vCPUs, 64GB RAM — comporta ate 8 containers de 2 CPUs
# On-demand (nao spot) para evitar preemption durante o teste
```

Upload do JAR a testar:
```bash
gcloud compute scp /path/to/ape-rv.jar cal-smoke:/opt/calibration/ape-rv.jar
```

#### Passo 0.3 — Preparar 3 APKs de teste

Selecionar 3 APKs com coverage conhecida (do baseline_v2), representando:
- 1 APK simples (method > 40%, poucas activities)
- 1 APK medio (method 15-25%, varias activities)
- 1 APK complexo (method 5-10%, auth wall ou crash frequente)

Criar `/opt/calibration/data/apks/smoke_test.txt` com os 3 nomes.

#### Passo 0.4 — Rodar 3 cenarios sequencialmente

Cada cenario: 1 container, 3 APKs, 1 rep, 300s timeout, `aperv:sata_mop` com defaults.

```bash
# --- Cenario A: 4 CPUs (referencia, igual ao local) ---
cat > /opt/calibration/smoke-4cpu.yml << 'YAML'
services:
  smoke_4cpu:
    image: phtcosta/rvandroid:0.8.0
    environment:
      RV_TOOLS: "aperv:sata_mop"
      RV_TIMEOUTS: "300"
      RV_REPETITIONS: "1"
      RV_NO_WINDOW: "true"
      RV_JCA_SPEC: "true"
      RV_SKIP_MONITORS: "true"
      RV_SKIP_INSTRUMENT: "true"
      RV_SKIP_STATIC_ANALYSIS: "true"
      RV_APKS_DIR: "/opt/rvsec/rv-android/apks"
      RV_APKS_FILTER: "/opt/rvsec/rv-android/filters/filter.txt"
      RV_EXPERIMENT_NAME: smoke_4cpu
    volumes:
      - /opt/calibration/data/apks:/opt/rvsec/rv-android/apks:ro
      - /opt/calibration/data/apks/smoke_test.txt:/opt/rvsec/rv-android/filters/filter.txt:ro
      - /opt/calibration/results/smoke_4cpu:/opt/rvsec/rv-android/results
      - /opt/calibration/ape-rv.jar:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar:ro
      - /opt/calibration/data/system-broadcast.json:/opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/system-broadcast.json:ro
    devices:
      - /dev/kvm:/dev/kvm
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: "10g"
YAML
docker compose -f /opt/calibration/smoke-4cpu.yml up
# Esperar ~20 min (3 APKs × 300s + boot/cleanup)

# --- Cenario B: 3 CPUs ---
# Mesmo YAML, mas cpus: "3", memory: "8g", nome smoke_3cpu
docker compose -f /opt/calibration/smoke-3cpu.yml up

# --- Cenario C: 2 CPUs ---
# Mesmo YAML, mas cpus: "2", memory: "6g", nome smoke_2cpu
docker compose -f /opt/calibration/smoke-2cpu.yml up
```

Tempo total: ~1h (3 cenarios × ~20 min cada).

#### Passo 0.5 — Teste de paralelismo

Apos determinar o minimo CPUs (ex: 2), testar N containers em paralelo:

```bash
# 4 containers simultaneos com 2 CPUs cada (usa 8 dos 16 vCPUs da VM)
# Cada container roda os mesmos 3 APKs — comparar coverage entre eles
# e com o cenario single-container
```

Se os 4 containers completam sem crash e coverage similar: paralelismo OK.

#### Passo 0.6 — Comparar resultados

Extrair `summary.csv` de cada cenario e comparar:

| Metrica | 4 CPUs | 3 CPUs | 2 CPUs | Paralelo (2 CPUs × 4) |
|---------|--------|--------|--------|----------------------|
| method_coverage (APK 1) | ? | ? | ? | ? |
| method_coverage (APK 2) | ? | ? | ? | ? |
| method_coverage (APK 3) | ? | ? | ? | ? |
| Tempo total | ? | ? | ? | ? |
| Crashes / timeouts | ? | ? | ? | ? |

**Criterio de decisao**: usar o menor CPUs onde coverage nao degrada mais que ~2pp
vs 4 CPUs E nao ha crashes. Se 2 CPUs funciona: **$79 spot**. Se precisa 3: **$118**.

#### Passo 0.7 — Cleanup

```bash
gcloud compute instances delete cal-smoke --zone=us-central1-a --quiet
# Manter a custom image (rvandroid-cal-v2) — sera usada na calibracao
```

Custo total do smoke test: ~$1-2 (n2d-standard-16 on-demand por ~1.5h ≈ $1.00).

### Fase A: Setup dos scripts (~0.5 dia)

1. Implementar mudancas nos scripts (aperv_parameter_space, objective, orchestrator)
2. Adicionar 2 mappings ao APERV_PROPERTY_MAPPING
3. Selecionar 100 APKs via select_dataset_v2.py
4. Testar scoring local: 1 trial com 3 APKs para verificar multi-rep groupby
5. Atualizar custom image se necessario (`gcloud compute images create` nova versao)

### Fase B: Calibracao (~2-8 dias dependendo de timeout, CPUs e VMs)

1. Criar Cloud SQL PostgreSQL (secao 4.8):
   ```bash
   gcloud sql instances create optuna-db --project=rvandroid ...
   ```

2. Criar N VMs spot a partir da custom image:
   ```bash
   for i in 0 1 2 3; do
     gcloud compute instances create cal-vm-$i \
       --project=rvandroid --zone=us-central1-a \
       --machine-type=n2d-standard-16 \
       --image=rvandroid-cal-v2 \
       --provisioning-model=SPOT \
       --enable-nested-virtualization
   done
   ```

3. Upload do JAR (unico arquivo mutavel, ~15 MB):
   ```bash
   for i in 0 1 2 3; do
     gcloud compute scp /path/to/ape-rv.jar cal-vm-$i:/opt/calibration/ape-rv.jar
   done
   ```

4. Lancar orchestrator em cada VM (mesmo study, PostgreSQL compartilhado):
   ```bash
   for i in 0 1 2 3; do
     gcloud compute ssh cal-vm-$i --command="
       cd /opt/calibration && nohup python scripts/calibration_orchestrator.py \
         --tool aperv:sata_mop \
         --phase macro --param-version v2 \
         --n-trials 80 --n-containers 8 \
         --reps 2 \
         --data-dir /opt/calibration/data/apks \
         --filter-file /opt/calibration/data/apks/aperv_cal_v2_100.txt \
         --output-dir /opt/calibration/results \
         --storage postgresql://optuna:SENHA@CLOUD_SQL_IP:5432/optuna \
         --timeout 600 --cpus 2 --memory 6g --seed 42 \
         > orchestrator.log 2>&1 &
     "
   done
   ```

5. Monitorar convergencia via SSH:
   ```bash
   gcloud compute ssh cal-vm-0 --command="tail -20 /opt/calibration/orchestrator.log"
   ```
   Se best score estabilizar por 3+ rounds, early stop.

### Fase C: Validacao (~12-18h, LOCAL)

A validacao final roda na maquina local (64 CPUs, 125 GiB RAM), nao no GCP.
Mesma infraestrutura e docker-compose usados no experimento final MadEvolve.

1. Coletar resultados de todas as VMs GCP:
   ```bash
   for i in 0 1 2 3; do
     gcloud compute scp --recurse cal-vm-$i:/opt/calibration/results/ ./results/cal_v2/vm$i/
   done
   ```

2. Destruir VMs de calibracao + Cloud SQL:
   ```bash
   for i in 0 1 2 3; do
     gcloud compute instances delete cal-vm-$i --zone=us-central1-a --quiet
   done
   gcloud sql instances delete optuna-db --quiet
   ```

3. Rodar params otimos LOCALMENTE em TODOS 169 APKs × 3 reps × 600s (507 tasks):
   - 12 containers × 4 CPUs × 9 GiB (padrao experimento final)
   - ~17 APKs por container (round-robin em 12 batches, identico ao MadEvolve final)
   - Wall clock estimado: ~8-10h

4. Comparar com baselines:
   - exp2: sata_mop_v1 (defaults, 32.69 score)
   - exp4: sata_mop_cal (calibrado v1, 31.76 score)
   - exp6: sata_mop_comp (code changes, 33.78 score)
   - **experimento final**: baseline sata_mop (28.19% method, 37.70% MOP)

5. Testes estatisticos: Wilcoxon signed-rank (pareado por APK)
6. Validacao holdout: score nos 67 APKs separados para medir generalizacao

### Fase D: Integracao

- Se melhorou: atualizar defaults no aperv-tool variants
- Aplicar params otimos ao melhor mutante do MadEvolve → efeito combinado
- Documentar resultados

---

## 8. Verificacao

### 8.1 Pre-calibracao (local)
1. **Scripts v2 funcionais**: `--param-version v2` gera compose com 10 params + FIXED_PARAMS_V2
2. **Scoring multi-rep**: groupby APK + trimmed mean produz score correto com 2 reps
3. **Property mappings**: `mop_weight_wtg` e `coverage_boost_weight` chegam ao Java

### 8.2 Smoke test CPUs (local)
4. **CPUs**: Coverage com 3 CPUs comparavel a 4 CPUs (delta < 2pp)
5. **Paralelismo estavel**: N containers simultaneos completam sem crash

### 8.3 Calibracao GCP
6. **Custom image funcional**: VM criada a partir de `rvandroid-cal-v2` boota, Docker funciona, `/dev/kvm` disponivel
7. **Convergencia**: Plot score vs trial — melhoria nas primeiras 30-40 trials
8. **Generalizacao**: Score holdout (67 APKs) ≈ score calibracao (100 APKs)

### 8.4 Validacao final (Fase C)
9. **Comparacao justa**: 600s timeout, 169 APKs, mesmas condicoes que exp2/4/6
10. **Melhoria vs defaults**: Score nos 169 APKs > 32.69 (sata_mop_v1 defaults)

---

## 9. Decisoes — resolvidas e pendentes

### 9.1 Decisoes resolvidas (2026-04-13)

| Decisao | Resolucao |
|---------|-----------|
| MadEvolve terminou? | **Sim — NO-GO**. Baseline (`5bd97f7`) mantido. Ref: `data/results/_analysis/final_experiment_report.md` |
| Qual JAR calibrar? | **Baseline `ape-rv.jar`** (master, sem rebuild necessario) |
| Budget/config | **Economico 300s**: 80 trials × 100 APKs × 2 reps × 300s = **~$44 spot** |
| Timeout | **300s** (calibracao). Validacao final (Fase C) a 600s |
| Spot vs on-demand | **Spot** (3x mais barato, risco aceitavel com orchestrator resiliente) |

### 9.2 Decisoes pendentes

| Decisao | Depende de | Impacto |
|---------|-----------|---------|
| CPUs por container (3 ou 4) | Smoke test local + GCP Fase 0 | Custo: ~$44 (2 CPUs) vs ~$66 (3 CPUs) |
| Quantidade de VMs | Urgencia vs custo | Wall clock: 2.2d (4 VMs) vs 4.4d (2 VMs) |

### 9.3 Configuracao selecionada

| Parametro | Valor |
|-----------|-------|
| Trials | 80 |
| APKs | 100 (cal) + 67 (holdout) = 167 viaveis |
| Reps | 2 |
| Timeout | **300s** (calibracao), 600s (validacao Fase C local) |
| CPUs/container | **A determinar** (smoke test: 3 ou 4) |
| JAR | baseline `5bd97f7` (master) |
| Storage | PostgreSQL (Cloud SQL, multi-VM) |
| Custo estimado | **~$66-88 spot** (3-4 CPUs) + ~$3 Cloud SQL |
| Wall clock | **~3.5-4.4 dias** (4 VMs, 3-4 CPUs) |
| Dataset calibracao | `data/selection/calibration_set_v2.txt` (100 APKs) |
| Dataset holdout | `data/selection/holdout_set_v2.txt` (67 APKs) |
| Validacao final | **Local** (64 CPUs, 12 containers, 169 APKs × 3 reps × 600s) |
