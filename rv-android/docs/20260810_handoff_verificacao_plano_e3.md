# Handoff — verificação rigorosa do plano de prontidão do Estudo 03

> **Este arquivo é o prompt de retomada.** Cole-o (ou aponte para ele) no início da nova
> sessão. Não edite este arquivo para reportar progresso — progresso se reporta na conversa.

---

## 0. Sua tarefa nesta sessão

**Verificar rigorosamente a consistência do plano de prontidão do Estudo 03.**

Documento sob verificação:
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260810_plano_prontidao_estudo03.md`

Você **não vai executar** nenhuma fase do plano. Nada de campanha de análise estática, nada de
instrumentação, nada de build do reator, nada de emulador. Esta sessão é de **auditoria do
plano**: encontrar inconsistências internas, afirmações não sustentadas pela evidência, lacunas
operacionais que impediriam a execução, e comandos que não rodariam como escritos.

Postura exigida: **adversarial e verificadora**. Toda afirmação do plano que cite `arquivo:linha`
ou um número medido deve ser reconferida abrindo o arquivo ou refazendo a medição. Handoff,
relatório e aritmética **não são verificação** — abrir o fonte e citar `arquivo:linha` é.

---

## 1. O que estamos fazendo (contexto)

A tese tem três estudos. **E1**: RV é viável em bibliotecas Java. **E2** (publicado, repo
`../ase-journal`): RV em Android comparando 8 ferramentas em 11 configurações sobre 163 APKs;
concluiu que o gargalo é a cobertura do código que toca a API JCA diretamente (média 8,04 %,
pico 10,63 %). **E3** (este): customiza o APE — melhor ferramenta do E2 — para guiar a
exploração por operações monitoradas (MOP), e mede se a guia resolve o gargalo.

**Defesa no fim de setembro de 2026. Hoje é 2026-08-10. O experimento do E3 ainda não rodou.**

### O beco de onde estamos saindo

Entre 2026-08-06 e 2026-08-09 o projeto criou um conjunto de specs adaptado ao Android
(`jca_android`, changes gh100 e gh101) e o submeteu a uma auditoria adversarial de sete fases
(`audit/20260808_validacao_jca_android/`, 270 arquivos, 558 claims). Veredito:
**NOT READY, 22/22 specs REPROVADAS**.

**Decisão do pesquisador, já tomada e não reabrível:** o Estudo 03 usa o conjunto **`jca`**, o
mesmo do E2. `jca_android` não será corrigido nem usado.

### Escopo desta linha de trabalho

O plano cobre **prontidão**: deixar os artefatos prontos para executar. **Não** cobre a execução
do experimento, seus parâmetros, nem a escrita da tese. Se a verificação tocar nesses temas,
registre como observação e siga — não expanda o escopo.

---

## 2. O que já foi feito (sessão anterior)

Sete frentes de investigação read-only, mais medições diretas em disco. Resultado consolidado no
plano. Os pontos que custaram mais para descobrir:

1. **O funil foi reconstituído**: `3941 → … → 219 executados → 164 em escopo → 163 analisados`.
   O "165" que circulava é o arm alternativo *"M neutralizado (+flavor)"*, descartado.
2. **A chave de pacote está homogênea**: medido que 134 dos 164 já usam a chave `Mneut` correta
   e os 30 divergentes são exatamente os do `30_apks.csv`.
3. **As divergências dos 30 e dos 55 têm naturezas opostas**: os 30 são *prefix-related*
   (detector errou a profundidade, `Mneut` corrige); 27 dos 55 são **disjuntos** (forks/renames,
   onde `Mneut` é a chave errada e o detector é o certo).
4. **O eixo dominante de heterogeneidade é o WTG, não a chave**: 38 dos 163 têm
   `transitions: []` por timeout, marcados `complete: true`.
5. **Os 38 são irrecuperáveis**: o Estágio B já foi executado (3600 s/8w/14 g) com rendimento
   nulo; o WTG é *timeout-bound* por laço quadrático.
6. **O estrato acionável do braço MOP é 10/163**, com causa raiz medida: `_build_wtg` só aceita
   arestas de evento `click`, e o GATOR não extrai cliques em UI moderna.
7. **A gh100 contamina o braço `jca`** (o E2 rodou com `dexlib2`, e a gh100 reparou o weaver
   `dexlib2`), na direção de mais violações.

### Decisões congeladas

São 13, listadas na §2 do plano. As que mais restringem a verificação:

- Specs `jca`; corpus **163**; branch **`modules`** (sem branch nova).
- **Manter** o reparo do weaver (`48b57fc5`); **reverter** o `ExecutionContext.java`
  (de `233df18a`); **manter** `Property.java`.
- Análise estática e instrumentação **no host**, sem Docker.
- Reanalisar **os 30** com WTG; **não** reanalisar os 38.
- Reinstrumentar **todos os 163**; diretório de entrega **novo e auto-contido, sem hardlink**.
- Sem pin de repositório Maven (local: `/home/pedro/desenvolvimento/repository`).
- **Piloto de instrumentação de 10 APKs antes do lote.**

Não reabra decisão congelada. Se encontrar evidência que a contradiga, reporte a evidência e
deixe a decisão para o pesquisador.

---

## 3. Próximos passos — o roteiro desta sessão

### 3.1 Verificação de sustentação factual

Para cada afirmação da §3 do plano ("Fatos medidos"), refaça a medição de forma independente e
confirme ou refute. Em particular:

| # | Afirmação a verificar | Como |
|---|---|---|
| V1 | 134/164 já com chave correta; os 30 divergentes == `30_apks.csv` | Reimplemente a regra de neutralização a partir de `ase-journal/docs/20260730_relatorio_remocao_package_detector.md:202-207` e compare com `[RvsecAnalysisClient] Filter package:` dos logs `rvsec-dataset-sa/logs/*.log` |
| V2 | 27 dos 55 são disjuntos | Mesma extração, classificando a relação de prefixo |
| V3 | 117 `ok` / 38 `truncated` / 1 `genuine_empty` nos 163 | Cruze `len(transitions)` dos JSON com `timed_out` de `rvsec-dataset-sa/_progress/*.json`. **Atenção**: o runner fixa `returncode = -1` no timeout (`rvsec-dataset/src/rvsec_dataset/static_analysis/runner.py:229-231`); `-50`/`206` **não** aparecem ali |
| V4 | Estrato = 10/163, e 4/40 no subset40 | Rode `derive_mop_artifact.derive(document, source_file, source_digest)` — a assinatura recebe **dict**, não caminho (`derive_mop_artifact.py:204`). Os três sinais estão em `artifact["stats"]["flagged"]`, `["wtgEdges"]` e `len(artifact["mopActivities"])` |
| V5 | `_build_wtg` só aceita `click` | `derive_mop_artifact.py:931-990` |
| V6 | `fossify.calendar` tem 63 transições, todas implícitas, sem timeout | Conte os `type` dos eventos em `rvsec-dataset/static_analysis/org.fossify.calendar_20.apk.json` e cheque `_progress` |
| V7 | Sentinela `complete: true` é incondicional | `JsonReportWriter.java:111` no módulo `rvsec-gator/client/.../json/`. Confirme em disco com `com.swordfish.lemuroid_252.apk.json` |
| V8 | Fonte do GATOR inalterada desde 2026-06-17 | `git log --since=2026-06-01 --name-only` sobre `rvsec/rvsec-android/rvsec-gator/` no repo raiz `rvsec` |
| V9 | GATOR resolve `android.jar` por `targetSdk`, não por ordem lexicográfica | `lib/gator/gator:87-97` |
| V10 | Os 133 JSON são idênticos entre `rvsec-dataset/static_analysis/` e o diretório operante | **Esta foi medida por subagente e não foi reconferida byte a byte. Verifique por sha256.** |
| V11 | Teto de ganho da rodada dos 30 é ~2 APKs no estrato | Reproduza a tabela dos 7 candidatos (`flagged>0 ∧ mopActivities>0` sob a chave correta) e o estado do WTG deles em junho |
| V12 | 9 eventos restaurados / 12 de 96 wrappers pela gh100 | `openspec/changes/gh100-weaver-emission-fidelity/evidence/green_deltas.md` |

### 3.2 Verificação de executabilidade

O plano tem comandos concretos. Verifique se rodariam como escritos, **sem executá-los**:

- As três edições em `scripts/gh91_sa_rerun.py` (`:83`, `:90`, `:309`) — abra o arquivo e
  confirme que os números de linha e o conteúdo batem hoje.
- `gh91_campaign.py --max-rounds 2` — confirme a ladder em `:66-67` e o dispatcher em
  `gh91_sa_rerun.py:463-475`.
- A invocação de `rv-experiment run` da Fase B — confirme que **todas** as flags existem em
  `modules/rv-experiment/src/rv_experiment/__main__.py` e que a combinação
  `--skip-execution` + `--instrument-apks` + `--generate-monitors` + `--skip-static` é aceita
  pela validação de `ExperimentConfig.validate()`.
- Confirme que `dexlib2` precisa mesmo ser forçado (default do CLI).

### 3.3 Lacunas conhecidas do plano — resolva ou nomeie

O plano tem buracos que a sessão anterior não fechou. Trate cada um:

| # | Lacuna | O que fazer |
|---|---|---|
| L1 | O plano cita "as quatro variáveis de caminho do lado da instrumentação" mas **não as enumera** | Encontre os nomes exatos. Ponto de partida: `rvsec-dataset/openspec/changes/rerun-corpus-jca-android/tasks.md:61-62` |
| L2 | O `--apks-filter <lista dos 163>` **não existe como arquivo** | Determine onde gerá-lo e a partir de qual fonte (`ase-journal/dataset/dataset.csv`, `funnel_stage == 'selected'`) |
| L3 | Não há estimativa de **disco** para `E3_jca_dexlib2_163/` | Meça o tamanho médio dos APKs instrumentados existentes e projete |
| L4 | O plano diz "reverter o `ExecutionContext.java` para o estado anterior a `233df18a`" mas **não fixa o SHA do estado-alvo** | Determine o commit exato e registre o diff esperado |
| L5 | Não há estimativa de tempo para a **Fase B** (piloto + lote dos 163) | Procure timings de campanhas de instrumentação anteriores |
| L6 | A inércia comportamental dos jars do GATOR é **inferida do git log**, não provada byte a byte | Nomeie como limitação, ou proponha como provar |
| L7 | O plano afirma que Fases A e B são paralelizáveis, com base em "o instrumentador `dexlib2` não consome o `.apk.json`" | Confirme no código (`modules/rv-instrumentation-dexlib2/`), não só na proposta do gh91 |
| L8 | Não há procedimento de **rollback** se a Fase B falhar no meio | Proponha |

### 3.4 Verificação de coerência interna

- As 13 decisões da §2 são mutuamente consistentes?
- Alguma fase depende de artefato que outra fase produz depois?
- Os gates 0/A/B/D são verificáveis com o que as fases produzem?
- As 12 pendências da §7 são realmente "declarar, não corrigir", ou alguma bloqueia a execução?

### 3.5 Entrega

Um relatório na conversa com: (i) afirmações **confirmadas**, (ii) afirmações **refutadas ou não
sustentadas** com a evidência, (iii) lacunas resolvidas e as que permanecem, (iv) uma lista
priorizada de correções ao plano. **Não edite o plano sem autorização** — proponha as correções e
espere.

---

## 4. Aprendizados da sessão anterior (leia antes de começar)

Cada um destes custou tempo. Não repita.

1. **Existem duas rodadas de análise estática, não uma.** Junho (Phase-7) rodou **com WTG** mas
   com a chave errada nos 30; julho (gh91) rodou **com a chave certa** mas com `--skip-wtg`.
   Nenhuma das duas tem as duas coisas. Dizer "os 30 já têm WTG" sem essa qualificação é
   enganoso.
2. **A regra de neutralização tem 11 tokens**, não 3. `{debug, dev, beta, staging, qa, nightly,
   alpha, snapshot, current, head, indev}`. Reproduzi-la com menos gera falsos positivos — a
   primeira medição deu 36 divergências em vez de 30 por causa disso.
3. **`derive()` recebe um dict**, não um caminho de arquivo.
4. **O marcador de timeout é `timed_out: true`**, não `returncode ∈ {-50, 206}`.
5. **`complete: true` não significa WTG completo.** É emitido incondicionalmente.
6. **Os jars locais não entram no experimento se ele rodar em Docker** — a imagem clona do
   GitHub e reconstrói tudo (`docker/rvandroid/Dockerfile:10-15`). Mas **a decisão é rodar SA e
   instrumentação no host**, então o que vale é o repositório Maven local.
7. **O repositório Maven local é `/home/pedro/desenvolvimento/repository`**, definido em
   `~/.m2/settings.xml:9`. Não é `~/.m2/repository`.
8. **O `rvsec-core.jar` é dexado dentro do APK na instrumentação**
   (`rv_instrumentation_core/instrumenter.py:98-105`), vindo de
   `mvn dependency:copy-dependencies` contra o repositório local. Por isso o revert do
   `ExecutionContext` só precisa estar lá no momento da instrumentação.
9. **`mvn install` de raiz falha sem `-DskipMopAgent`.**
10. **Não sugerir atalhos que reaproveitem artefatos parciais.** O pesquisador recusou
    explicitamente um "join" entre o WTG de junho e a reachability de julho. Integridade acima
    de tempo.
11. **Não assumir premissas que o pesquisador não confirmou.** A sessão anterior recomendou uma
    opção assumindo que a comparabilidade com o E2 estava abandonada — não estava.

---

## 5. Regras de trabalho — seguir rigorosamente

Além do `CLAUDE.md` da raiz (`rvsec/CLAUDE.md`) e do módulo
(`rvsec/rv-android/CLAUDE.md`), que são autoritativos:

- **Workflow**: `docs/WORKFLOW.md`. Para qualquer coisa rastreada em `openspec/changes/gh<N>-*/`,
  invocar as skills OpenSpec via a ferramenta `Skill`. **Nunca** criar ou reescrever artefato
  OpenSpec com `Write`/`Edit` direto.
- **Emulador — NÃO TOCAR.** Nunca iniciar, parar ou gerenciar emulador manualmente, em nenhum
  contexto. O rv-platform é dono do ciclo de vida inteiro.
- **Não mexer no gator.** `rvsec-gator` só muda por erro grosseiro; melhorias de substrato vão
  por offline ou pelo consumidor.
- **Commits**: nunca adicionar `Co-Authored-By` nem qualquer trailer de coautoria.
- **Português**: sempre com acentuação correta, mesmo que o pesquisador escreva sem acentos.
- **Testes**: `uv run pytest --import-mode=importlib -o "addopts="` — sem essas flags a
  coleta quebra.
- **P1–P4** (simplicidade, documentação narrativa, sem retrocompatibilidade, comentários do
  estado atual) governam todo código, comentário e documento.
- **Background**: processos longos vão em background rastreado pelo harness, nunca
  `nohup`/`setsid`.
- **Não editar handoffs e prompts do pesquisador.** Progresso se reporta na conversa.
- **`experimento-cal` é histórico** — não editar nem adaptar.

---

## 6. Arquivos relacionados

### O plano e este handoff
| arquivo | papel |
|---|---|
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` | **o documento sob verificação** |
| `rv-android/docs/20260810_handoff_verificacao_plano_e3.md` | este arquivo |

### Corpus e funil
| arquivo | papel |
|---|---|
| `ase-journal/dataset/dataset.csv` | fonte autoritativa, 3941 × 89 colunas, `funnel_stage` |
| `ase-journal/data-analysis/stats/selection_funnel_stats.txt` | funil gerado por script |
| `ase-journal/docs/20260730_relatorio_remocao_package_detector.md` | regra de neutralização (`:202-207`), arms 164/165/88/185 (`:196-199`) |
| `rv-android/30_apks.csv` | os 30 a reanalisar |
| `experimento-20260706/filters/experiment_apks.txt` | os 219 executados |

### Análise estática
| arquivo | papel |
|---|---|
| `rvsec-dataset/static_analysis/` | 345 JSON da Phase-7, com WTG, chave antiga nos 30 |
| `rvsec-dataset-sa/logs/`, `_progress/` | argv na linha 1; `timed_out`, `returncode`, `seconds` |
| `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/` | 30 JSON com chave certa e sem WTG; `REGISTRO.md`, `record/` |
| `rv-android/scripts/gh91_sa_rerun.py`, `gh91_campaign.py` | driver e campanha |
| `rv-android/openspec/changes/archive/2026-07-31-gh91-sa-rerun-manifest-key/` | a change da rodada anterior |
| `rv-android/docs/20260731_gh91_handoff_grupo5.md` | handoff, com a assinatura do `--skip-wtg` |
| `rv-android/docs/20260617_sweep_gh66_validacao_wtg.md` | prova do teto do WTG (`:38`, `:128`) |
| `rvsec-dataset/docs/20260628_phase7-*.md` | recuperação e triagem da Phase-7 |
| `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java` | cliente GATOR |
| `rv-android/lib/gator/gator` | launcher |

### Instrumentação e substrato
| arquivo | papel |
|---|---|
| `modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py` | classpath de runtime, `copy-dependencies` |
| `modules/rv-instrumentation-dexlib2/` | variante DEX-native |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | CLI, flags |
| `modules/rv-experiment/src/rv_experiment/config.py` | mapeamento do spec set (`:686-712`), SA sem `mop_dir` (`:942-951`) |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` | **alvo do revert** |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java` | **não reverter** |
| `openspec/changes/gh100-weaver-emission-fidelity/` | reparo do weaver + evidência |
| `openspec/changes/gh101-jca-spec-conformance/` | specs `jca_android` (aberta) |

### Artefato MOP e braços
| arquivo | papel |
|---|---|
| `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py` | derivação; `_build_wtg` em `:931-990`; portão em `:249` |
| `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` | variantes (`:309`, `:385`, `:423`, `:441`) |
| `modules/rv-tools/src/rv_tools/builtin/ape/` | APE original (jar upstream) |
| `modules/rv-tools/src/rv_tools/builtin/droidbot/tool.py` | variantes (`:111-156`) |
| `rv-android/docs/20260806_cmp163.md`, `data/results/cmp163_consolidado/` | campanha com 3 dos 5 braços sobre os 163 |

### Auditoria e arquitetura
| arquivo | papel |
|---|---|
| `rv-android/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` | veredito, §7 as 10 decisões, §10 decisão final |
| `rv-android/audit/20260808_validacao_jca_android/set/set_cons_fen_registry.csv` | 119 fenômenos com proveniência |
| `rv-android/docs/architecture/rv-android.md`, `subsystem-rv-experiment.md` | pipeline fim a fim |
| `rvsec-dataset/openspec/changes/rerun-corpus-jca-android/` | plano abandonado, útil como referência de protocolo |

---

## 7. Comandos úteis

```bash
# Raízes
RVA=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
W=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
DS=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET
export RVSEC_HOME=$W/rvsec

# Chave efetivamente usada numa análise da Phase-7
grep "Filter package" $W/rvsec-dataset-sa/logs/<apk>.apk.log

# argv exato da Phase-7 (linha 1 de cada log)
head -1 $W/rvsec-dataset-sa/logs/<apk>.apk.log

# Estado de timeout
python3 -c "import json;print(json.load(open('$W/rvsec-dataset-sa/_progress/<n>.json')))"

# Transições e tipos de evento de um APK
python3 - <<'PY'
import json, collections
j=json.load(open("<caminho>.apk.json"))
print("transitions:", len(j["transitions"]))
print(collections.Counter(e.get("type") for t in j["transitions"] for e in t.get("events",[])))
PY

# Três sinais do artefato MOP
python3 - <<'PY'
import sys, json
sys.path.insert(0,"modules/aperv-tool/src")
from aperv_tool.tools.aperv import derive_mop_artifact as D
a=D.derive(json.load(open("<caminho>.apk.json")), "x", "")
print(a["stats"]["flagged"], a["stats"]["wtgEdges"], len(a["mopActivities"]))
PY

# Commits publicados
cd $W/rvsec && git merge-base --is-ancestor <sha> origin/modules && echo PUBLICADO

# Testes (flags obrigatórias)
uv run pytest --import-mode=importlib -o "addopts=" modules/<mod>/tests/
```

**Nunca** rode `rv-experiment run` à mão para "só conferir" — ele sobe emulador.

---

## 8. O que NÃO fazer nesta sessão

- Não executar nenhuma fase do plano.
- Não editar o plano sem autorização; proponha correções.
- Não reabrir decisão congelada da §2 do plano.
- Não sobrescrever `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`, `rvsec-dataset/static_analysis/`,
  `rvsec-dataset/instrumented_apks/`, `APKS_INSTRUMENTED_*`, nem as colunas `sa_*` de
  `ase-journal/dataset/dataset.csv`.
- Não expandir para execução do experimento nem para escrita da tese.
- Não criar branch.
