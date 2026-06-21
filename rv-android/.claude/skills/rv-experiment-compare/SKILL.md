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

**Imagem Docker:** `phtcosta/rvandroid:<tag>` (default `0.9.1`). Cadeia de build (todas na mesma tag):
`rvsec_base` → `rvsec_android` (SDK/emulador API 30 x86_64, GATOR, KVM) → `rvandroid_tools`
(droidbot/ape/fastbot) → `rvandroid` (clone `PAMunb/rvsec` branch `modules` + `mvn install` + `uv sync`).
⚠️ O estágio final faz `git clone` do branch → **os commits relevantes precisam estar pushed antes do
build**. Braços LLM exigem `lmsysorg/sglang:v0.5.6.post2` + GPU + modelo no `HF_CACHE`.

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

---

## Fase 1 — Setup (gera artefatos)

Definir com o usuário: dataset, tools, timeout, reps, containers, spec-set, e se há braço LLM
(→ `--with-sglang`). Então:

```bash
python3 .claude/skills/rv-experiment-compare/scripts/gen_compare.py \
  --name <name> --dataset <dir-com-apks> \
  --tools "<RV_TOOLS>" \
  --timeout 300 --reps 3 --containers 6 --spec-set jca [--with-sglang] [--filter-abi]
```

Produz: filtros round-robin, `docker-compose.<name>.yml` (SGLang só se `--with-sglang`),
`docs/<date>_<name>.md` (plano), e o meta JSON. **Revisar o plano** e preencher as seções de
hipóteses/expectativas/riscos específicos antes de rodar.

- `--filter-abi`: filtra APKs por ABI compatível com a AVD (x86_64 / arm64-v8a / sem-nativo). Use se
  o dataset não estiver pré-filtrado (memória: ~20% de perda histórica por arch incompatível).
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

## Fase 4 — Resume final + Consolidar/Analisar (gera)

1. **Passada de resume final**: ao terminar, os containers Exitam com alguns FAILED transientes de
   `adb install` (~1-3%). Re-rodar `up -d` (ou deixar o `monitor_compare.sh` reiniciar) **uma vez** —
   o resume pula COMPLETED e re-executa FAILED. Conferir que as identidades distintas batem o total.
2. **NÃO dar `down`** antes de extrair os traces (artefatos efêmeros no device).
3. **Consolidar + Wilcoxon**:
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
