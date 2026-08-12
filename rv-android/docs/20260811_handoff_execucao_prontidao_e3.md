# Handoff — execução do plano de prontidão do Estudo 03

> **Este arquivo é o prompt de retomada.** Cole-o (ou aponte para ele) no início da nova
> sessão. Não edite este arquivo para reportar progresso — progresso se reporta na conversa.

---

## 0. Sua tarefa nesta sessão

**Executar o plano de prontidão do Estudo 03**, fase a fase, respeitando os portões.

Documento diretor:
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260810_plano_prontidao_estudo03.md`

O plano já passou por uma auditoria adversarial completa (sessão de 2026-08-10/11) e **está
corrigido**. Não o reaudite do zero: os números dele foram medidos e reconferidos. Se encontrar
divergência nova, reporte com `arquivo:linha` antes de agir.

**Antes de começar, duas coisas dependem do pesquisador** (§ "Decisões pendentes" abaixo). Não
as decida sozinho, e não fique bloqueado por elas: a Fase 0 e a Fase A não dependem de nenhuma
das duas.

---

## 1. O que estamos fazendo (contexto)

A tese tem três estudos. **E1**: RV é viável em bibliotecas Java. **E2** (publicado, repo
`../ase-journal`): RV em Android comparando 8 ferramentas em 11 configurações sobre 163 APKs;
concluiu que o gargalo é a cobertura do código que toca a API JCA diretamente (média 8,04 %,
pico 10,63 %). **E3** (este): customiza o APE — melhor ferramenta do E2 — para guiar a
exploração por operações monitoradas (MOP), e mede se a guia resolve o gargalo.

**Defesa no fim de setembro de 2026. Hoje é 2026-08-11. O experimento do E3 ainda não rodou.**

O escopo desta linha de trabalho é **prontidão**: deixar os artefatos prontos para executar.
**Não** cobre a execução do experimento, seus parâmetros, nem a escrita da tese. Se o trabalho
tocar nesses temas, registre como observação e siga — não expanda o escopo.

---

## 2. O que já foi feito

### 2.1 Antes (2026-08-06 a 2026-08-09)

Criou-se um conjunto de specs adaptado ao Android (`jca_android`, changes gh100 e gh101) e
submeteu-se a uma auditoria adversarial de sete fases
(`audit/20260808_validacao_jca_android/`, 270 arquivos, 558 claims). Veredito:
**NOT READY, 22/22 specs REPROVADAS**.

**Decisão do pesquisador, tomada e não reabrível:** o Estudo 03 usa o conjunto **`jca`**, o mesmo
do E2. `jca_android` não será corrigido nem usado.

### 2.2 Sessão de 2026-08-10 — o plano

Sete frentes de investigação read-only produziram o plano de prontidão, com 13 decisões
congeladas, 4 fases (0/A/B/C/D) e 12 pendências declaradas.

### 2.3 Sessão de 2026-08-10/11 — auditoria e correção do plano

Verificação adversarial das 12 afirmações do plano (V1–V12), da executabilidade dos comandos e
de 8 lacunas (L1–L8). **Nenhuma fase foi executada.** Resultado: 9 afirmações confirmadas por
medição independente, 3 refutadas ou mal-fundamentadas, 1 bloqueador de execução encontrado,
6 lacunas fechadas e 2 nomeadas como limitação. **Todas as correções já foram aplicadas ao
plano** — o documento que você vai executar é a versão corrigida.

O que a auditoria mudou, em uma linha cada:

| Achado | Consequência no plano |
|---|---|
| Truncados são **45** nos 163 / **36** nos 133, não 38 (a tabela antiga somava 186 para um corpus de 163) | §3.4 e Fase C passo 14 refeitos |
| **Bloqueador**: `gh91_campaign.py` decide "pronto" por `has_sentinel()`, e um WTG estourado deixa em disco a escrita pré-WTG **já com o sentinela** | Fase A ganhou uma **quarta edição** obrigatória |
| Não existe guard de ~32 MB no dispositivo (`MopData.java:202` é a porta de `formatVersion`) | Removido do Gate D — como estava, reprovaria o `redreader`, o nº 1 do estrato |
| Fase B custa ~600 s/APK em laço **sequencial** → ~27 h; a campanha de referência usou 8 containers | §5 invertida: o caminho crítico é a B, quem espera é a A |
| As 5 variáveis de ambiente do preflight só existem no `rvsec-dataset`; o `rv-experiment` não as lê | Preflight da Fase B reescrito para a rota real |
| Marginais do §3.6 dependiam da fonte do JSON (operante × Phase-7); "os três" é invariante | Tabela agora declara as duas fontes |
| Leitura do `green_deltas.md` invertia os wrappers (96→84 é **deduplicação**) e generalizava os 9 eventos | Consequência de D3 reescrita |
| §3.3 tinha os rótulos de direção invertidos (25 = detector **raso** demais) | Corrigido, com o exemplo trocado |

---

## 3. Fatos já medidos — **não remeça**

Tudo abaixo foi verificado em disco nesta sessão. Reusar, não recalcular.

### 3.1 Corpus e chave

- `dataset.csv`: 3941 linhas × 89 colunas; `selected` = **163**, `filtered_denominator_scope` =
  55, `filtered_zero_coverage` = 1.
- Regra de neutralização (11 tokens, mínimo 2 segmentos): **134/164** já com a chave correta; os
  **30** divergentes são **exatamente** o `30_apks.csv`, sem sobra nem falta.
- Direção das divergências: **25** = detector foi **raso** demais (`detected_prefix_of_Mneut`),
  **5** = **fundo** demais. Nos 55: 15 iguais, 13 rasos, **27 disjuntos**.
- APKs de entrada: `RV_ANDROID_NOVO_DATASET/APKS/` tem os 163; **tamanho idêntico em 163/163** a
  `rvsec-dataset/head_apks/`, e sha256 idêntico em amostra de 10.

### 3.2 WTG

| | 163 (Phase-7) | 133 não-30 |
|---|---:|---:|
| `ok` (`transitions > 0`) | 117 | **96** |
| `truncated` (`== 0` + `timed_out`) | **45** | **36** |
| `genuine_empty` (`eu.faircode.email_2322`) | 1 | 1 |

Corroboração: os 348 `_progress` têm **82** `timed_out: true`, e são **exatamente** os 82 logs
sem a linha `...... target level:` (o buffer de stdout do launcher morre com o `kill`). Desses
82, 45 estão nos 163. Nos 55: mais 15 truncados.

Dos 30, **9** estouraram timeout na Phase-7: `app.pachli_50`, `ch.rmy.android.http_shortcuts`,
`com.darkrockstudios.app.securecamera_31`, `com.github.livingwithhippos.unchained_60`,
`com.jerboa_87`, `de.markusfisch.android.binaryeye_174`, `it.niedermann.owncloud.notes`,
`org.glpi.inventory.agent_39469`, `swati4star.createpdf_110`.

### 3.3 Estrato MOP

"Os três sinais" (`flagged>0 ∧ wtgEdges>0 ∧ mopActivities>0`): **4/40** no subset40, **10/163**,
**13/219** — invariante entre as duas fontes de JSON. As marginais **não** são invariantes:
30/41/34 no diretório operante, **34/48/37** na Phase-7.

Os 10 do estrato: `redreader_117`, `ewesticker`, `vscan_24`, `packagemanager_79`,
`passportreader_22`, `flyingcarpet_21`, `dsub2000_217`, `keepalive_133`, `cry.otp_31`,
`sexytopo_93`.

Dos 30, **7** têm `flagged>0 ∧ mopActivities>0` sob a chave correta: `binaryeye`,
`fossify.calendar`, `fossify.math`, `fossify.musicplayer`, `fossify.notes`, `wikipedia`,
`glpi.agent`. **Cinco deles já rodaram o WTG até o fim em junho e deram zero arestas de clique**
(só implícitos); **dois** estouraram timeout (`binaryeye`, `glpi.agent`). Teto de ganho: **2
APKs** — o estrato iria de 10 para no máximo 12.

### 3.4 Substrato

- Último commit em `rvsec-gator/*/src/main`: **`4280f3bd` (2026-06-17)**, antes da Phase-7
  (2026-06-26). Depois só POMs (bumps 0.9.1→0.9.2→0.9.3, jacoco) e comentários.
- Alvo do revert do `ExecutionContext.java`: **`efdd0541fbb43bf8c896a159c6bb3abbc479252e`**
  (`233df18a^`). O `ExecutionContextTest.java` **entrou junto com `233df18a`** e afirma
  identidade — sai no mesmo commit.
- Repositório Maven local: `/home/pedro/desenvolvimento/repository` (`~/.m2/settings.xml:9`). O
  `rvsec-core-0.9.3-SNAPSHOT.jar` de lá é de **2026-08-08 10:35**, isto é pós-`233df18a`.
- Os 133 JSON não-30 são **byte-idênticos por sha256** entre `rvsec-dataset/static_analysis/` e
  `APKS_INSTRUMENTED_..._selected163/`. Os 30 diferem (são os do gh91).
- Hardlink confirmado: `_selected163` e o diretório de 219 compartilham inode (20/20 na amostra,
  `st_nlink = 3`).

### 3.5 Custos

- Fase B: **485–681 s por APK** (~600 s), laço **sequencial** → **~27 h** para 163 no host.
- Disco do diretório de entrega: **~4,3 GiB** (3,81 GiB de APK tecido + 0,47 GiB de JSON). Havia
  1,8 TiB livres.
- Maior JSON dos 163: `redreader_117` com **48,3 MiB**; o artefato derivado dele tem **0,25 MiB**.

---

## 4. Próximos passos — o roteiro desta sessão

Siga o plano. O que segue é o que a auditoria acrescentou e que **não** está óbvio no documento.

### 4.1 Fase 0 — congelar o substrato

1. Revert do `ExecutionContext.java` para `efdd0541` + remoção do `ExecutionContextTest.java`,
   **um commit, um estado consistente** (P3).
2. `mvn clean install -DskipTests -DskipMopAgent` na raiz `rvsec` — o `-DskipMopAgent` é
   obrigatório.
3. Arquivo de proveniência com commit + sha256 dos 5 jars + dos 23 `.mop`.

**Gate 0:** `rvsec-core` novo no repositório local com mtime posterior ao build, e o
`ExecutionContext.class` sem `IdentityHashMap`/`newSetFromMap`.

### 4.2 Fase A — análise estática dos 30

**As quatro edições, nesta ordem.** As três primeiras estão verificadas linha a linha e batem
com o arquivo de hoje. A quarta é a que a auditoria descobriu:

| arquivo:linha | mudança |
|---|---|
| `gh91_sa_rerun.py:83` | `APKS_CSV` → `RV_ANDROID / "30_apks.csv"` (a change foi arquivada; hoje morre em `:240-241`) |
| `gh91_sa_rerun.py:90` | `OUT_DIR` → `DATASET_ROOT / "SA_RERUN_gh91_wtg"` (propaga sozinho para `REGISTRO`, `_campaign_state.json` e `_superseded/`, que derivam de `drv.OUT_DIR` em `gh91_campaign.py:86-88`) |
| `gh91_sa_rerun.py:309` | remover `"-clientParam", "skipWtg=true",` |
| **`gh91_campaign.py:99`** | **a predicação de completude deixa de ser só `has_sentinel()`** |

**Por que a quarta é obrigatória.** `pending_for_round` (`:264`), `classify` (`:130-131`) e
`retryable` (`:243`) decidem tudo por `has_sentinel()`. Mas `JsonReportWriter.java:111` emite
`"complete": true` **incondicionalmente**, inclusive na escrita pré-WTG que
`RvsecAnalysisClient.java:169-170` faz **antes** de `WTGBuilder.build()` (`:189`). Logo um APK
que estourar o WTG no round 1 conta como COMPLETE e **nunca sobe para o round 2 (120 g/7200 s)**.
Isso era invisível na gh91 porque `skipWtg=true` fazia o cliente retornar logo após a escrita
pré-WTG (`:180-184`) — ali sentinela e completo eram a mesma coisa. **Remover o `skipWtg` é o
que ativa o defeito**, e 9 dos 30 são candidatos diretos.

Correção mínima: exigir também `timed_out is False` no `_progress` (ou `transitions` não
vazias). Provar a mudança com um teste que reproduza um JSON pré-WTG com sentinela.

**Gate barato antes da campanha** — `--only net.osmtracker_73.apk --jvm-memory 32g --timeout
3600`. Esperar `Filter package: net.osmtracker` e **`transitions ≥ 287`** com eventos de `click`.
**Não** esperar igualdade com os 287 de junho nem os 72,5 s: junho rodou com
`net.osmtracker.activity` (140 application classes) e a rodada nova usa `net.osmtracker`
(232 classes, medido pela gh91). O universo é maior.

**Campanha** em background rastreado pelo harness (nunca `nohup`/`setsid`):
`uv run python scripts/gh91_campaign.py --max-rounds 2`. Ladder em `gh91_campaign.py:66-67`
(round 1 = 32 g/3600 s, round 2 = 120 g/7200 s, budget 100 GiB). Orçamento esperado 8–14 h.

**Gate A:** 30/30 JSON escritos; cada um classificado `ok`/`truncated`/`genuine_empty`; nenhum
`transitions == 0` sem classificação; e — novidade — **nenhum APK marcado COMPLETE com
`timed_out: true`**.

### 4.3 Fase B — instrumentação dos 163

- **É o caminho crítico** (~27 h serial). Comece por ela se as duas forem rodar em paralelo; quem
  espera em caso de contenção é a Fase A.
- Preflight próprio da rota `rv-experiment` (as 5 variáveis do `rvsec-dataset` **não se
  aplicam**): `RVSEC_HOME`, jar do `rvsec-core` novo e sem `IdentityHashMap`, `--output-dir`
  inexistente, arquivo do `--apks-filter` com 163 linhas casando com `APKS/`, variante
  `dexlib2`. Cada asserção com exit ≠ 0 e **probada negativamente**.
- **Gerar a lista dos 163**: `dataset.csv` com `funnel_stage == 'selected'`, um nome por linha,
  LF, sem espaço à direita — o parsing é `read_text().strip().splitlines()` com casamento por
  basename (`config.py:584-586`), e um `\r` faz o APK sumir em silêncio.
- `dexlib2` **tem de ser forçado** (o default do CLI é `ajc`).
- Piloto de 10 e lote dos 163, ambos com `--skip-execution` (decisão do pesquisador de
  2026-08-11).

**Gate B:** 163/163 tecidos; `instrument_results.json` sem falha silenciosa rebaixada; nenhum
`VerifyError` no piloto de validação — ver P14 abaixo.

### 4.4 Fases C e D

Montar `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/` auto-contido, **sem hardlink**; 163 APK +
163 `.apk.json` co-locados (133 da Phase-7 + 30 da Fase A); `wtg_status` fechando em
**96/36/1 + 30**; manifesto sha256; portão de artefatos, proveniência e não-destruição.

**Não** cheque teto de 32 MB — ele não existe.

---

## 5. Decisões pendentes do pesquisador

Não decida por conta própria. Nenhuma bloqueia a Fase 0 nem a Fase A.

1. **P14 — validação em emulador do piloto.** Com `--skip-execution` em toda a Fase B, o comando
   do piloto prova a metade de instrumentação do critério, mas não instala, não lança e não
   verifica `RVSEC-COV` no logcat. Falta definir como fechar essa metade do Gate B.
2. **As ~27 h da Fase B.** A única alavanca é paralelizar a instrumentação em containers, o que
   D6 hoje proíbe. Reabrir D6 é decisão do pesquisador.

---

## 6. Aprendizados — não repita

1. **Existem duas rodadas de análise estática, não uma.** Junho (Phase-7) rodou **com WTG** mas
   com a chave errada nos 30; julho (gh91) rodou **com a chave certa** mas com `--skip-wtg`.
   Nenhuma das duas tem as duas coisas.
2. **A regra de neutralização tem 11 tokens**, não 3: `{debug, dev, beta, staging, qa, nightly,
   alpha, snapshot, current, head, indev}`, preservando no mínimo 2 segmentos.
3. **`derive()` recebe um dict**, não um caminho. O encoder chama-se `serialize_canonical`, não
   `encode_artifact`.
4. **O marcador de timeout é `timed_out: true`** no `_progress`; o runner fixa `returncode = -1`
   (`runner.py:231-233`). `-50`/`206` não aparecem ali.
5. **`complete: true` não significa WTG completo.** É emitido incondicionalmente
   (`JsonReportWriter.java:111`). Este é o eixo do bloqueador da Fase A.
6. **Um log sem `...... target level:` é um log que foi morto.** O `print()` do launcher fica no
   buffer e some com o `kill`. Serve como detector independente de timeout.
7. **A subida da chave amplia o universo.** `Mneut` mais curto que a chave do detector = mais
   application classes = mais tempo e mais transições. Não compare contagens entre rodadas com
   chaves diferentes.
8. **O repositório Maven local é `/home/pedro/desenvolvimento/repository`**, não `~/.m2/repository`.
9. **O `rvsec-core.jar` é dexado dentro do APK na instrumentação**, vindo de
   `mvn dependency:copy-dependencies` (`instrumenter.py:114-123`) contra o repositório local. Por
   isso o revert só precisa estar lá no momento da instrumentação.
10. **`mvn install` de raiz falha sem `-DskipMopAgent`.**
11. **Os jars locais não entram no experimento se ele rodar em Docker** — a imagem clona do
    GitHub e reconstrói (`docker/rvandroid/Dockerfile:10-15`). Como SA e instrumentação rodam no
    host, o que vale é o repositório Maven local.
12. **Não sugerir atalhos que reaproveitem artefatos parciais.** O pesquisador recusou
    explicitamente um "join" entre o WTG de junho e a reachability de julho. Integridade acima de
    tempo.
13. **Não assumir premissas que o pesquisador não confirmou.** Quando o comando ou o critério for
    ambíguo, pergunte antes de escrever.
14. **Handoff, relatório e aritmética não são verificação.** Abrir o fonte e citar `arquivo:linha`
    é.

---

## 7. Regras de trabalho — seguir rigorosamente

Além do `CLAUDE.md` da raiz (`rvsec/CLAUDE.md`) e do módulo (`rvsec/rv-android/CLAUDE.md`), que
são autoritativos:

- **Workflow**: `docs/WORKFLOW.md`. Para qualquer coisa rastreada em `openspec/changes/gh<N>-*/`,
  invocar as skills OpenSpec via a ferramenta `Skill`. **Nunca** criar ou reescrever artefato
  OpenSpec com `Write`/`Edit` direto.
- **Emulador — NÃO TOCAR.** Nunca iniciar, parar ou gerenciar emulador manualmente, em nenhum
  contexto. O rv-platform é dono do ciclo de vida inteiro.
- **Não mexer no gator.** `rvsec-gator` só muda por erro grosseiro; melhorias de substrato vão
  por offline ou pelo consumidor.
- **Commits**: nunca adicionar `Co-Authored-By` nem qualquer trailer de coautoria.
- **Português**: sempre com acentuação correta, mesmo que o pesquisador escreva sem acentos.
- **Testes**: `uv run pytest --import-mode=importlib -o "addopts="` — sem essas flags a coleta
  quebra.
- **P1–P4** (simplicidade, documentação narrativa, sem retrocompatibilidade, comentários do
  estado atual) governam todo código, comentário e documento.
- **Background**: processos longos vão em background rastreado pelo harness, nunca
  `nohup`/`setsid`.
- **Não editar handoffs e prompts do pesquisador.** Progresso se reporta na conversa.
- **`experimento-cal` é histórico** — não editar nem adaptar.

---

## 8. Arquivos relacionados

### Plano e handoffs
| arquivo | papel |
|---|---|
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` | **o plano a executar** (versão corrigida) |
| `rv-android/docs/20260811_handoff_execucao_prontidao_e3.md` | este arquivo |
| `rv-android/docs/20260810_handoff_verificacao_plano_e3.md` | o handoff da sessão de auditoria |

### Corpus e funil
| arquivo | papel |
|---|---|
| `ase-journal/dataset/dataset.csv` | fonte autoritativa, 3941 × 89, `funnel_stage` |
| `ase-journal/data-analysis/stats/selection_funnel_stats.txt` | funil gerado por script |
| `ase-journal/docs/20260730_relatorio_remocao_package_detector.md` | regra de neutralização (`:202-207`), arms (`:196-199`) |
| `rv-android/30_apks.csv` | os 30, com coluna `relation` |
| `rv-android/calibracao/subset40.txt` | o subset40 da gh97 |

### Análise estática
| arquivo | papel |
|---|---|
| `rvsec-dataset/static_analysis/` | 345 JSON da Phase-7, com WTG, chave antiga nos 30 |
| `rvsec-dataset-sa/logs/`, `_progress/` | argv na linha 1; `timed_out`, `returncode`, `seconds` |
| `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/` | 30 JSON com chave certa e sem WTG; `REGISTRO.md`, `record/` — **entregável assinado, não sobrescrever** |
| `rv-android/scripts/gh91_sa_rerun.py`, `gh91_campaign.py`, `gh91_gate.py`, `gh91_record.py` | driver, campanha, portão, registro |
| `rv-android/docs/20260731_gh91_handoff_grupo5.md` | handoff da rodada anterior (`:126` tem a afirmação refutada sobre o sentinela) |
| `rv-android/docs/20260617_sweep_gh66_validacao_wtg.md` | teto do WTG (`:38` é **baseline pré-gh66**; `:128` sobre `--succ-depth`) |
| `rvsec/rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java` | cliente GATOR (`:107`, `:169-170`, `:180-184`, `:189`) |
| `.../clients/json/JsonReportWriter.java` | sentinela em `:111` |
| `rv-android/lib/gator/gator` | launcher (`:71`, `:92`, `:113`, `:119`, `:142-153`) |

### Instrumentação e substrato
| arquivo | papel |
|---|---|
| `modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py` | `copy-dependencies` em `:114-123` |
| `modules/rv-instrumentation-dexlib2/` | variante DEX-native; **zero referências ao `.apk.json`** |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | CLI (`:440`, `:459`, `:465`, `:472`, `:482`, `:502`, `:527`) |
| `modules/rv-experiment/src/rv_experiment/config.py` | `validate()` `:376-451`; `apks_filter` `:584-586`; SA sem `mop_dir` `:942-951` |
| `modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py` | `--skip-execution` pula a Fase 2 em `:189-197` |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py` | laço sequencial de instrumentação (`:282`, `:323`, `:417`, `:485`) |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` | **alvo do revert** (`efdd0541`) |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java` | **não reverter** |
| `openspec/changes/gh100-weaver-emission-fidelity/evidence/green_deltas.md` | censo do reparo (`:53-56`, `:69`, `:86-90`, `:92-98`) |

### Artefato MOP e ferramentas
| arquivo | papel |
|---|---|
| `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py` | `derive` `:204`, portão do sentinela `:249`, `_build_wtg` `:931-990`, `CLICK_EVENT_TYPE` `:106` |
| `ape-rearch/src/main/java/com/android/commands/monkey/ape/utils/MopData.java` | `:202` é a porta de `formatVersion`; `readFile` `:707-712` |
| `rv-android/docs/20260806_cmp163.md` | campanha com 3 dos 5 braços sobre os 163 (`:80-87`) |

### Auditoria
| arquivo | papel |
|---|---|
| `rv-android/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md` | veredito, §7 as 10 decisões |
| `rvsec-dataset/openspec/changes/rerun-corpus-jca-android/` | plano abandonado; útil como referência de protocolo, **mas suas variáveis de ambiente não valem para a rota `rv-experiment`** |

---

## 9. Comandos úteis

```bash
# Raízes
RVA=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
W=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
DS=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET
export RVSEC_HOME=$W/rvsec

# Fase 0 — revert e build
cd $W/rvsec
git checkout efdd0541 -- rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java
git rm rvsec/rvsec-core/src/test/java/br/unb/cic/mop/ExecutionContextTest.java
mvn clean install -DskipTests -DskipMopAgent

# Gate 0
unzip -p /home/pedro/desenvolvimento/repository/br/unb/cic/rvsec-core/0.9.3-SNAPSHOT/rvsec-core-0.9.3-SNAPSHOT.jar \
    br/unb/cic/mop/ExecutionContext.class | strings | grep -E "IdentityHashMap|newSetFromMap" && echo FALHOU || echo OK

# Fase A — conferir antes de rodar
cd $RVA
uv run python scripts/gh91_sa_rerun.py --plan
uv run python scripts/gh91_sa_rerun.py --dry-run | head -20   # NÃO pode conter skipWtg=true

# Classificação pós-rodada (o sentinela sozinho não serve)
uv run python - <<'PY'
import json, glob, os
D="/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
for f in sorted(glob.glob(D+"/_progress/*.json")):
    p=json.load(open(f)); j=p.get("json_path")
    n=len(json.load(open(j)).get("transitions",[])) if j and os.path.exists(j) else -1
    flag="SILENT-EMPTY" if (n==0 and p.get("timed_out")) else ""
    print(f"{p['apk']:48} tr={n:<6} {p['sa_status']:12} to={p.get('timed_out')} rc={p['returncode']} {flag}")
PY

# Gerar a lista dos 163
python3 - <<'PY'
import csv
W="/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
sel=[r["apk"] for r in csv.DictReader(open(f"{W}/ase-journal/dataset/dataset.csv"))
     if r["funnel_stage"]=="selected"]
open("/tmp/e3_163.txt","w").write("\n".join(sorted(sel))+"\n")
print(len(sel))
PY

# Três sinais do artefato MOP
python3 - <<'PY'
import sys, json
sys.path.insert(0,"modules/aperv-tool/src")
from aperv_tool.tools.aperv import derive_mop_artifact as D
a=D.derive(json.load(open("<caminho>.apk.json")), "x", "")
print(a["stats"]["flagged"], a["stats"]["wtgEdges"], len(a["mopActivities"]))
PY

# Chave e argv de uma análise da Phase-7
grep "Filter package" $W/rvsec-dataset-sa/logs/<apk>.apk.log
head -1 $W/rvsec-dataset-sa/logs/<apk>.apk.log

# Commits publicados
cd $W/rvsec && git merge-base --is-ancestor <sha> origin/modules && echo PUBLICADO

# Testes (flags obrigatórias)
uv run pytest --import-mode=importlib -o "addopts=" modules/<mod>/tests/
```

**Nunca** rode `rv-experiment run` à mão para "só conferir" sem `--skip-execution` — ele sobe
emulador.

---

## 10. O que NÃO fazer nesta sessão

- Não reabrir decisão congelada da §2 do plano (specs `jca`, corpus 163, branch `modules`, host
  sem Docker, reanalisar só os 30, reinstrumentar os 163, diretório novo sem hardlink).
- Não decidir sozinho as duas pendências da §5 deste handoff.
- Não sobrescrever `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`, `rvsec-dataset/static_analysis/`,
  `rvsec-dataset/instrumented_apks/`, `APKS_INSTRUMENTED_*`, nem as colunas `sa_*` de
  `ase-journal/dataset/dataset.csv`.
- Não reaproveitar `instrumented_apks/` parcial: um APK meio-tecido é indistinguível de um
  completo para o `get_instrumented_apks()` (INV-EXP-16). Rollback é recomeço.
- Não expandir para a execução do experimento nem para a escrita da tese.
- Não criar branch.
