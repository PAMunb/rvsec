---
name: rv-experiment-compare
description: >-
  Criar, rodar, acompanhar e analisar uma comparação multi-tool no rv-platform (N tools × M APKs ×
  R reps em K containers Docker, com SGLang opcional para braços LLM, resume e consolidação offline +
  Wilcoxon). Use para experimentos comparativos como APE × APE-RV (docs/20260619_comparacao_aperv.md).
  Do NOT use para um experimento single-tool simples (use `rv-experiment run` direto) nem para
  pré-processamento/instrumentação (use o pipeline do rv-experiment).
argument-hint: [name]
allowed-tools: Bash, Read, Write, Edit
---

# Comparação multi-tool: $ARGUMENTS

Lifecycle completo de uma comparação no rv-platform, em 4 fases. **Híbrido**: gera as partes
mecânicas (filtros, compose, plano), guia as fases interativas (run, monitor) e gera a análise final.
O **plano nasce sempre junto** com o compose e os filtros (padrão `docs/20260619_comparacao_aperv.md`),
para nenhuma corrida ficar solta.

Scripts da skill (caminhos relativos à raiz `rv-android/`):
- `.claude/skills/rv-experiment-compare/scripts/gen_compare.py`
- `.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh`
- `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py`

Convenções: `<name>` é o prefixo do experimento → containers `<name>_NN`, filtros
`data/<name>_filters/batch_NN.txt`, resultados `data/results/<name>_NN/<name>_NN/`, meta
`data/results/<name>_compare_meta.json`, compose `docker/docker-compose.<name>.yml`,
plano `docs/<YYYYMMDD>_<name>.md`, consolidação `data/results/<name>_consolidado/`.

---

## Contexto — rv-experiment / rv-platform (o que a comparação dirige)

A comparação **não** é um runner próprio: ela orquestra **N invocações** do `rv-experiment`, uma por
container, cada uma rodando uma fatia de APKs. Entender o pipeline evita configurar errado.

**`rv-experiment`** (orquestração) executa 3 estágios:
1. **Pré-processamento** — geração de monitores (`rv-monitor-generator`, JavaMOP/RV-Monitor),
   instrumentação do APK (`rv-instrumentation*`) e análise estática (`rv-static-analysis`, GATOR).
   **Na comparação tudo isso é PULADO** (ver Skips) — o dataset já vem instrumentado + `.apk.json`.
2. **Execução** — delega ao `rv-platform`.
3. **Pós-processamento** — agrega resultados (CSVs por container; mas a fonte da verdade da
   consolidação são os logcats, por causa do gh58 — ver Fase 4).

**`rv-platform`** (motor de execução) roda cada task via `TaskExecutor`, com componentes em ciclo
initialize/execute/cleanup: **emulador** (ciclo todo gerenciado pelo platform — nunca mexer na mão),
**static analysis** (copia o `<apk>.json` co-localizado para o results-dir, mesmo com `--skip-static`),
**coverage** (`rv-coverage`, lê os marcadores `RVSEC-COV`/`RVSEC` do logcat), **logcat**, e
**execução da ferramenta** (`rv-tools` + plugins: `aperv-tool` = APE/APE-RV via `ape-rv.jar`,
`rvagent-tool` = rv-agent/LLM). Uma task = `(apk, tool, variant, rep, timeout)`; os N braços são
**interleaved** por APK no mesmo experimento.

**Imagem Docker:** `phtcosta/rvandroid:<tag>` (default `0.9.3`). Cadeia de build (Dockerfiles em
`docker/<layer>/Dockerfile`, todas publicadas na mesma tag — ver `docker/README.md` para a tabela
completa e `docker/build_all.sh` para o build encadeado):

| Layer | Dockerfile | Imagem | Conteúdo relevante |
|-------|-----------|--------|---------------------|
| 1 | `docker/base/Dockerfile` | `rvsec_base` | Ubuntu 22.04, Java 8, Python 3.10, uv |
| 2 | `docker/android/Dockerfile` | `rvsec_android` | SDK/emulador API 30 `x86_64`, GATOR, KVM |
| 3 | `docker/tools/Dockerfile` | `rvandroid_tools` | clona `honeynet/droidbot`; base para APE/FastBot |
| 4 | `docker/rvandroid/Dockerfile` | `rvandroid` (produção) | clona `PAMunb/rvsec` branch `modules` (`ARG RVSEC_BRANCH`) + `mvn install` + `uv sync`; **builda `ape-rv.jar` a partir do source** (ver abaixo); `LABEL rvsec.branch` |

⚠️ O estágio 4 faz `git clone` do branch `rvsec` → **os commits relevantes precisam estar pushed antes
do build**. Braços LLM exigem `lmsysorg/sglang:v0.5.6.post2` + GPU + modelo no `HF_CACHE`.

### `ape-rv.jar` — build-from-source sem pin de SHA (gh71 D3)

`docker/rvandroid/Dockerfile` clona `https://github.com/phtcosta/ape.git` (repo APE-RV, separado do
`rvsec`) **na branch default, sem `ARG`/SHA fixo** — decisão deliberada (ver comentário no Dockerfile,
gh71 D3): o jar comitado historicamente ficava desatualizado (ex.: lia a chave legada `reachesMop` em
vez de `reachesTarget`, causando 0 boost de MOP em 147k avaliações). Builda com
`mvn -f /tmp/ape/pom.xml package -DskipTests` e copia para
`modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar`.

**Implicação**: o commit exato do `ape` embutido numa tag de imagem é **o que era HEAD do branch
default no instante do `docker build`**, não é rastreável via `docker inspect` diretamente. Para
auditar qual commit foi usado:

```bash
# 1. Timestamp de build da imagem (== timestamp do `mvn package`, pois o Dockerfile builda e
#    copia o jar no mesmo RUN — o mtime do jar dentro do container bate com o Created da imagem)
docker inspect phtcosta/rvandroid:<tag> --format '{{.Created}}'

# 2. No repo local do ape (mesmo remote do Dockerfile), achar o commit HEAD nesse instante
cd <path-para-o-repo-ape-local>
git log --since="<Created menos alguns min>" --until="<Created>" --oneline

# 3. Comparar HEAD local atual vs esse commit — se o diff for só docs/openspec (propostas ainda
#    não implementadas), o jar da imagem está funcionalmente ao dia; se houver diff de código-fonte
#    Java, a imagem está desatualizada e precisa rebuild antes de rodar a comparação.
git diff --stat <commit-do-build>..HEAD -- . ':!docs' ':!openspec'
```

Rode esse check **antes de qualquer comparação que dependa do comportamento do APE-RV** (ex.: braços
`aperv:sata`/`aperv:sata_mop`) — sobretudo se houve trabalho recente no repo `ape` (ex.: mudanças em
`mop-guidance`/priorização MOP), pois um jar desatualizado na imagem invalida silenciosamente H1/H2 do
plano da comparação sem erro visível em runtime.

## Conceitos críticos: skips, timeouts e resume

### Skips de pré-processamento (sempre ligados nesta skill)
São 3 flags independentes (env no compose / flags `--skip-*` no CLI):
- `RV_SKIP_MONITORS=true` — não (re)gera os monitores JavaMOP/RV-Monitor.
- `RV_SKIP_INSTRUMENT=true` — não instrumenta o APK (usa o APK como está).
- `RV_SKIP_STATIC_ANALYSIS=true` — não roda o GATOR.

Por que pular: o dataset já é **dexlib2-instrumentado** e traz o `<apk>.json` (análise estática GATOR)
**co-localizado**. **Gotcha**: com os skips, `--apks-dir`/dataset DEVE apontar para os APKs **já
instrumentados** — apontar para originais zera a cobertura. O `<apk>.json` co-localizado é copiado para
o results-dir mesmo com `--skip-static`, então os braços MOP recebem o dado estático normalmente.

### Timeouts (são TRÊS, não confundir)
- **Timeout de task** (`RV_TIMEOUTS` / `--timeout`, ex. **300 s**) — wall-clock de cada task de
  exploração. Estourá-lo é **saída NORMAL** de ferramenta de exploração (não é erro). É o que define o
  orçamento de exploração e domina o wall-clock total.
- **Timeout da análise estática** (GATOR) — **independente**, só relevante se NÃO pular static
  (aqui pulamos). APKs patológicos podem precisar de muito mais memória/tempo (campanhas anteriores:
  60 g no FixpointSolver, ~1800–3600 s) — por isso o dataset já vem com o `.apk.json` pré-computado.
- **`llm_timeout_ms`** (ex. **15000**, só braço LLM) — timeout por chamada ao SGLang; ao estourar, o
  APE-RV **segue sem LLM naquele passo** (degradação graciosa → comportamento tende a `sata_mop`),
  então o wall-clock da task NÃO estoura. Referência empírica: ~1,1 s/chamada, 0 timeouts numa GPU.

### Resume (a skill depende dele)
- **Gatilho**: `RV_EXPERIMENT_NAME=<name>_NN`. Se já existe `results/<name>_NN/tasks.json`, entra em
  **resume implícito**. No Docker, basta `docker restart <name>_NN` (o entrypoint re-invoca
  `rv-experiment run` com o mesmo `--name`; o volume de results persiste o `tasks.json`).
- **Regra de identidade** `(apk,tool,variant,rep,timeout)`: **COMPLETED → pulada**;
  **FAILED/ERROR → re-executada do zero**; nunca-executada → executada.
- **Em resume os 3 skips são forçados a `True`** (não re-instrumenta/re-gera/re-roda GATOR).
- `tasks.json` é escrito atômico por-task (tmp→fsync→rename); cada container resume **independente**.
- Efeito colateral: cada re-execução cria novo UUID → `tasks.json` acumula duplicatas → por isso
  **dedup por identidade** na contagem e na consolidação (nunca `task_id`, nunca grep cru).

### Diagnósticos de execução — `RV_LOGCAT_DIAGNOSTICS` + `app_events.csv` (gh72, opt-in)

Por padrão o pipeline captura **só** `RVSEC`/`RVSEC-COV` (`adb logcat -s RVSEC:V RVSEC-COV:V`): o `-s`
**silencia crashes/VerifyError/ANR na origem**, então um APK que morre cedo aparece como "ferramenta de
baixa cobertura" sem registro do porquê (confounder invisível — ~8,8% dos runs abrem buffer de crash
sem conteúdo na corrida APE×APE-RV).

A flag **opt-in** `RV_LOGCAT_DIAGNOSTICS` (CLI `--logcat-diagnostics/--no-logcat-diagnostics`, default
`false`) torna isso observável:
- **Ligada** (gerador `--logcat-diagnostics`): o filtro adiciona `AndroidRuntime:E art:E dalvikvm:E
  ActivityManager:W` **além** de `RVSEC:V RVSEC-COV:V`, e o `rv-platform` grava um CSV dedicado
  `app_events.csv` (1 linha por evento: `category` ∈ {crash, verify_error, anr}, `exception_class`,
  `method`, `source`, `message`, `process`, `pid`, `fatal`, `n_frames`, `stack_head`). O trace completo
  fica **só** no `.logcat` (a fonte da verdade); o CSV traz só o `stack_head`.
- **Desligada** (default): comando `adb` e `.logcat` **byte-idênticos** ao baseline — nada muda.

**Isolamento (importante para a comparação):** os eventos diagnósticos vão para uma coleção separada e
**não entram em nenhuma métrica** — `cov_*`, `mop_*`, `total_errors`/`unique_errors` ficam idênticos com
a flag on ou off (a captura é **aditiva**). Logo, ligar diagnostics **não invalida** a comparação
pareada nas métricas primárias; só afeta reprodutibilidade byte-a-byte e volume de logcat
(desprezível). `app_events.csv` sobrevive ao resume (reconstruído do `.logcat`, como `errors.csv`).

**Quando ligar (D9 — ato deliberado por campanha, nunca na âncora compartilhada por padrão):**
- **Validação de instrumentação** (ex.: dexlib2 × ajc, onde VerifyError/crash **é** o objeto de estudo)
  → **ligar** (`--logcat-diagnostics`). Substitui o grep offline manual de `FATAL EXCEPTION`/`VerifyError`.
- **Comparação de ferramentas** (ex.: APE × APE-RV, cobertura/MOP) → **manter OFF** por padrão; ligar só
  se você quiser **quantificar o crash como confounder** (decisão explícita, registrar no plano §riscos).

> ⚠️ Tags do device, não do app: as tags emitidas pelo APK instrumentado (`RVSEC*`) **não mudam** — só a
> captura no device. `art`/`dalvikvm` podem emitir em `W` em vez de `E` em alguns runtimes; se um run de
> validação mostrar VerifyError de carga perdido, ampliar para `art:W` (risco conhecido do plano gh72).

---

## Fase 1 — Setup (gera artefatos)

Definir com o usuário: dataset, tools, timeout, reps, containers, spec-set, e se há braço LLM
(→ `--with-sglang`). Então:

```bash
python3 .claude/skills/rv-experiment-compare/scripts/gen_compare.py \
  --name <name> --dataset <dir-com-apks> \
  --tools "<RV_TOOLS>" \
  --timeout 300 --reps 3 --containers 6 --spec-set jca \
  [--with-sglang] [--filter-abi] [--logcat-diagnostics]
```

Produz: filtros round-robin, `docker-compose.<name>.yml` (SGLang só se `--with-sglang`),
`docs/<date>_<name>.md` (plano), e o meta JSON. **Revisar o plano** e preencher as seções de
hipóteses/expectativas/riscos específicos antes de rodar.

- `--filter-abi`: filtra APKs por ABI compatível com a AVD (x86_64 / arm64-v8a / sem-nativo). Use se
  o dataset não estiver pré-filtrado (memória: ~20% de perda histórica por arch incompatível).
- `--logcat-diagnostics` (gh72): liga a captura **opt-in** de eventos diagnósticos do app
  (crashes/VerifyError/ANR) → emite `RV_LOGCAT_DIAGNOSTICS: "true"` no compose e gera `app_events.csv`.
  **Default OFF** — sem a flag o comando `adb logcat` e os logcats são **byte-idênticos** ao baseline
  RVSEC/RVSEC-COV (não muda nenhum baseline de comparação). Ver "Diagnósticos de execução" abaixo.
- O compose é gerado programaticamente (N containers + SGLang condicional); o plano vem de
  `templates/plan.md.tmpl`.

## Fase 2 — Run (guiado)

1. **Conflito de `sglang-server`**: se um compose anterior (ex.: smoke) deixou o `sglang-server` de pé,
   `docker compose -f <compose-anterior> down` antes — senão o `up -d` colide por `container_name`.
2. **Smoke/preflight (gate)**: rodar uma fração (1-16 APKs, 1 rep, timeout curto) e validar os gates
   do plano §7 (todas COMPLETED; cobertura > 0; braços MOP ≠ sem-MOP; braço LLM bate no SGLang;
   0 VerifyError). Só liberar a corrida completa após passar.
3. **Launch**:
   ```bash
   docker compose -f docker/docker-compose.<name>.yml up -d
   ```
   Com `--with-sglang`, o `up -d` espera o SGLang ficar `healthy` (~3-4 min de warmup) antes dos
   containers. **NUNCA** gerenciar emuladores na mão — o platform cuida do ciclo (regra do CLAUDE.md).

## Fase 3 — Monitor (guiado + script)

```bash
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh <name>          # status + auto-resume
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh <name> --no-resume   # só reporta
```

Mostra, por container, `COMPLETED / total` (**identidades distintas**) e dá **auto-resume**
(`docker restart`) de container não-running antes de terminar ou travado (Up sem progresso desde a
última checada). Rodar on-demand; para acompanhamento longo, agendar checagens periódicas.

> ⚠️ **Contagem correta**: o script conta `result.state` deduplicado por
> `(apk,tool,variant,rep,timeout)`. **NUNCA** contar com `grep '"state": "COMPLETED"'` no tasks.json —
> isso conta **em dobro**, porque o estado COMPLETED também aparece em `result.state_transitions[]`
> (erro real cometido na corrida de 2026-06-19; números saíram 2× inflados).

> ⚠️ **Atraso aparente não é travamento**: o `tasks.json` só é gravado quando a task **fecha**, então
> o último `start_time` registrado é o da task que terminou — a seguinte já está em voo, invisível.
> O atraso normal chega a **~2 ciclos**; só suspeitar acima disso, e confirmar pelo `docker logs`
> (um container vivo está bootando emulador ou executando a ferramenta).

## Fase 4 — Resume final + Consolidar/Analisar (gera)

1. **Passada de resume final**: ao terminar, os containers Exitam com alguns FAILED transientes de
   `adb install` (~1-3%). Re-rodar `up -d` (ou deixar o `monitor_compare.sh` reiniciar) **uma vez** —
   o resume pula COMPLETED e re-executa FAILED. Conferir que as identidades distintas batem o total.
2. **NÃO dar `down`** antes de extrair os traces (artefatos efêmeros no device).
3. **Decidir admissibilidade por tarefa, ANTES de qualquer agregação** (lição da gh97). `COMPLETED`
   registra que a ferramenta retornou sem levantar exceção — **não** que o run fez o que devia. Um run
   cujo emulador morreu no meio, ou cuja ferramenta parou sozinha, é gravado `COMPLETED` com
   `error_message` vazio; numa campanha de 360 runs apareceram dois assim, aos 1284 s e 1012 s de um
   orçamento de 1800 s, e todos os portões de validade da época passaram neles. Os seis critérios,
   aplicados **cegos ao braço e à direção do efeito**:
   - **C1** estado `COMPLETED` com `error_message` vazio;
   - **C2** `execution_time_seconds >= timeout` (menos uma folga de teardown; a exploração é limitada
     por orçamento **por construção**, então tempo decorrido é o discriminador — o código de saída
     não serve, porque emulador morto e crash da aplicação são indistinguíveis por ele);
   - **C3** o traço carrega pelo menos um passo além do cabeçalho do run;
   - **C4** pelo menos uma assinatura `RVSEC-COV` distinta no logcat;
   - **C5** `cov_method > 0` e `cov_act > 0`;
   - **C6** o número de identidades admissíveis é igual ao previsto pelo manifesto da campanha.

   Uma tarefa inadmissível volta para a fila reescrevendo o estado para `ERROR` **depois** de
   preservar os artefatos — é o que faz o resume, que já recupera falha barulhenta, recuperar também
   a silenciosa.

   **A regra de contagem é a mesma de sempre e vale aqui em dobro**: conte por identidade
   `(apk_name, tool_config.name, tool_config.variant, repetition, timeout)`, **nunca por registro**.
   O resume **acrescenta** em vez de sobrescrever, então uma identidade recuperada guarda dois
   registros (o `ERROR` e o `COMPLETED`): 360 identidades com 9 recuperações moram em 369 registros.
   Referência de implementação: `experimento-rearch-aperv/scripts/verify.py` (Gate 6) e
   `repair_tasks.py`.
4. **Consolidar + Wilcoxon**:
   ```bash
   python3 .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py <name>
   # se faltar scipy no python do sistema:
   uv run python .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py <name>
   ```
   Gera em `data/results/<name>_consolidado/`: `per_task.csv`, `per_apk_paired.csv`
   (média das reps), `per_tool_summary.csv`, `wilcoxon.csv` (**todos os pares × todas as métricas**).

---

## Gotchas fixos (lições de campo — não re-aprender)

- **Contagem**: `result.state` dedup por identidade; nunca grep cru (double-count via
  `state_transitions`) nem `task_id` (resume infla com novos UUIDs).
- **gh58**: consolidar dos **logcats**. A cobertura por-método pode zerar no CSV de tasks resumidas
  se o `<apk>.json` não resolver; o dado co-localizado evita isso (validar reconstrução
  "(with per-method coverage)" nos logs do `result_processor`).
- **Métricas MOP**: `cov_mop = methods_mop_reachable_coverage`; `mop_unique =
  coverage_metrics.total_errors` (= violações distintas por `Spec,classe,método,tipo`); `mop_total` =
  linhas `RVSEC : <Spec>,...` no logcat.
- **Diagnósticos (gh72)**: só existem se a campanha rodou com `--logcat-diagnostics`. Ficam em
  `app_events.csv` (por container), **fora** de toda métrica — não entram no `consolidate_compare.py`
  (que cobre cobertura/MOP). Para analisá-los, ler os `app_events.csv` por container e filtrar offline
  por `process == <pacote do APK da task>` (atribuição é pelo bloco `Process:`/`ANR in`, não por PID).
  Reprocessar logcats **antigos** (pré-gh72) **não** recupera crashes — eles nunca foram capturados.
- **Resume final** recupera FAILED transientes; **não `down`** até extrair traces.
- **`FLAG_SECURE`**: apps com janela segura bloqueiam screenshot → o braço LLM degrada para SATA puro
  (0 chamadas LLM). É degradação correta, não bug — marcar/excluir essas identidades na comparação
  `*_llm` vs `*_mop`.
- **ABI**: filtrar APKs pela arch da AVD (`--filter-abi`) antes de estratificar.
- **Latência LLM (referência)**: ~1,1 s/ação mediana, 0 timeouts numa GPU; o gargalo do braço LLM é
  **custo de oportunidade** (menos ações no mesmo wall-clock), não timeout — ver
  `docs/20260619_debug_aperv_cobertura.md`.

## Referências

- Comparação/plano de referência: `docs/20260619_comparacao_aperv.md`
- Memo de diagnóstico (latência, proporção de ações, Wilcoxon): `docs/20260619_debug_aperv_cobertura.md`
- Mecânica de resume / skip-flags: `docs/WORKFLOW.md`, `rv-platform/CLAUDE.md`
- Diagnósticos de execução (flag + `app_events.csv`, decisões D1–D9): `docs/20260621_plano_logcat_tags_expandidas.md`
  e a change `openspec/changes/gh72-logcat-diagnostic-events/`
