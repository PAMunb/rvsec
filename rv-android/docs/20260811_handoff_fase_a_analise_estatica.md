# Handoff — executar a Fase A: análise estática dos 30 com WTG

> **Este arquivo é o prompt de retomada.** Cole-o (ou aponte para ele) no início da nova
> sessão. Não edite este arquivo para reportar progresso — progresso se reporta na conversa.

---

## 0. Sua tarefa nesta sessão

**Rodar a análise estática dos 30 APKs (Fase A do plano de prontidão do Estudo 03) até o
Gate A fechar.** Nada além disso. A Fase B (instrumentação dos 163) **não** entra nesta
sessão — o pesquisador interrompeu o piloto dela de propósito e mandou fazer a análise
estática primeiro.

Documentos diretores, nesta ordem de autoridade:

| arquivo | papel |
|---|---|
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` | **o plano**; a Fase A é a §4 "Fase A", passos 4–8 |
| `rv-android/docs/20260811_handoff_execucao_prontidao_e3.md` | o handoff da sessão anterior; §4.2 é a Fase A, §6 são os aprendizados |
| este arquivo | o que mudou desde então, e o que ainda falta decidir |

O plano já passou por auditoria adversarial e **está corrigido**. Não o reaudite. Se encontrar
divergência nova, reporte com `arquivo:linha` antes de agir.

---

## 1. Contexto em quatro linhas

A tese tem três estudos. **E3** (este) customiza o APE para guiar a exploração por operações
monitoradas (MOP) e mede se a guia resolve o gargalo de cobertura que o E2 identificou.
**Defesa no fim de setembro de 2026. Hoje é 2026-08-11. O experimento ainda não rodou.**

O escopo desta linha de trabalho é **prontidão**: deixar os artefatos prontos para executar.
**Não** cobre a execução do experimento, seus parâmetros, nem a escrita da tese.

**Por que os 30.** Existem duas rodadas de análise estática e nenhuma serve: junho (Phase-7)
rodou **com WTG** mas com a chave de pacote errada nesses 30; julho (gh91) rodou **com a chave
certa** mas com `--skip-wtg`. A Fase A é a primeira rodada com as duas coisas. Ela se justifica
por **integridade do corpus**, não por ganho de estrato — o teto de ganho medido é 2 APKs.

---

## 2. O que já foi feito (sessão de 2026-08-11, manhã)

### 2.1 Fase 0 — CONCLUÍDA, Gate 0 passou

Commit **`e204e2a48aafba3e78b1e03ebc20a2bb8c7f6e6d`** na branch `modules`:
*revert(e3): the predicate store goes back to equality, and its test goes with it*.
Reverte `ExecutionContext.java` para `efdd0541` e remove o `ExecutionContextTest.java` que
entrou junto com `233df18a` — um commit, um estado consistente. `Property.java` e o reparo do
weaver (`48b57fc5`) permanecem.

`mvn clean install -DskipTests -DskipMopAgent` na raiz `rvsec`: **BUILD SUCCESS em 78 s** (não
os ~30 min que o plano orçava). Gate 0 verificado: o `ExecutionContext.class` dentro do
`rvsec-core-0.9.3-SNAPSHOT.jar` do repositório local **não** contém `IdentityHashMap` nem
`newSetFromMap`, contém `java/util/HashSet`, e o jar tem mtime 2026-08-11 10:14:56, posterior
ao início do build.

Proveniência escrita em `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/PROVENIENCIA.md`: commit,
sha256 de 7 jars e dos 23 `.mop`. Confirmado por medição independente que os 23 `.mop` são
**byte-idênticos a `7e7acb69`** (diff vazio) — o conjunto `jca` está congelado.

### 2.2 Fase A — preparada, gate barato passou, campanha NÃO lançada

**As quatro edições estão aplicadas**, e uma quinta, consequente, no portão:

| arquivo | mudança |
|---|---|
| `scripts/gh91_sa_rerun.py` | `APKS_CSV` → `RV_ANDROID / "30_apks.csv"` (a change foi arquivada) |
| `scripts/gh91_sa_rerun.py` | `OUT_DIR` → `DATASET_ROOT / "SA_RERUN_gh91_wtg"` |
| `scripts/gh91_sa_rerun.py` | removido `"-clientParam", "skipWtg=true",` |
| `scripts/gh91_campaign.py` | **`has_sentinel()` deixa de ser o critério de "pronto"**: nasce `is_complete(out_dir, apk)`, que exige sentinela **e** `timed_out is False` no `_progress`. Substituída nos 4 sítios (`retryable`, `pending_for_round`, `on_done`, `final_report`) |
| `scripts/gh91_gate.py` | a asserção 3.2 passa a usar `is_complete`; nasce a **3.7**, que classifica cada APK em `ok` / `truncated` / `genuine_empty` — é o que a Fase C copia para a coluna `wtg_status` |

Comentários e docstrings que passaram a mentir com a saída do `skipWtg` foram corrigidos nos
três scripts (P4).

**Teste novo:** `tests/parity/test_gh91_completeness.py`, **9 casos, todos verdes**. Reproduz em
disco o JSON pré-WTG com sentinela + `_progress` com `timed_out: true` e prova que
(i) `has_sentinel` diz sim, (ii) `is_complete` diz não, (iii) `pending_for_round` **promove** o
APK para a rodada 2.

**Prova negativa executada na máquina.** Com a predicação antiga restaurada por monkeypatch,
`pending_for_round(..., round 2)` devolve **vazio** para um APK com `timed_out: true`; com a
correção, devolve o APK. O bloqueador era real e está fechado.

**Gate barato — PASSOU.** `net.osmtracker_73.apk` a 32 g/3600 s, **72,3 s**, `returncode 0`,
`timed_out: false`:

| critério | medido |
|---|---|
| `Filter package:` no log | `net.osmtracker` (a chave `Mneut`, correta) |
| classes em `reachability` | **232** — bate com as 232 que a gh91 mediu sob essa chave |
| `transitions` | **287** |
| eventos | `click` **161**, `long_click` 6, `item_click` 4, o resto implícitos |
| `derive_mop_artifact.derive()` | `wtgEdges = 97`, `mopActivities = 1`, `flagged = 0` |

Os 287 e os 161 cliques e as 97 arestas reproduzem **exatamente** os números que o plano §3.6
mediu sobre o JSON da Phase-7.

> **Observação em aberto, não resolvida:** a Phase-7 rodou este APK sob `net.osmtracker.activity`
> (140 application classes) e a rodada nova sob `net.osmtracker` (232 classes) — o universo de
> classes **mudou**, mas a contagem de transições ficou idêntica (287) e o tempo praticamente
> idêntico (72,5 s → 72,3 s). Isso sugere que o WTG **não depende de `codePackage`**, que só
> filtraria a seção `reachability`. Não confirmei no fonte. Se for verdade, não invalida a
> rodada (a `reachability` é o que estava errado nos 30 e é o que muda), mas **vale verificar
> em `RvsecAnalysisClient.java` / `WTGBuilder` antes de escrever qualquer conclusão sobre o
> WTG dos 30**. Não gaste a janela nisso agora; anote se aparecer.

**Estado do diretório de saída** — `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg/`:
```
net.osmtracker_73.apk.json          (287 transições, complete, 1 dos 30 pronto)
logs/net.osmtracker_73.apk.log
_progress/net.osmtracker_73.apk.json
```
A campanha **vai pular esse APK sozinha** (`is_complete` → True), então a rodada 1 tem **26**
pendentes, não 27.

### 2.3 O que foi feito e depois desfeito

Um piloto de instrumentação de 10 APKs (Fase B) chegou a ser lançado e foi **interrompido pelo
pesquisador aos ~2 minutos**. O diretório parcial `RV_ANDROID_NOVO_DATASET/E3_piloto10/` foi
**removido** — não existe resíduo. Nenhum processo ficou vivo.

Sobraram desse preparo, e continuam válidos para a Fase B **quando ela chegar**:
- `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/apks_163.txt` — a lista dos 163, gerada de
  `dataset.csv` (`funnel_stage == 'selected'`), LF, sem espaço à direita, 163 linhas únicas.
- `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/apks_piloto10.txt` — 5 maiores + 5 menores.
- `scripts/e3_preflight_instrument.py` — preflight da Fase B com exit ≠ 0, **provado
  negativamente em 4 cenários** (RVSEC_HOME errado, output-dir existente, cardinalidade errada,
  CR no arquivo). Todos mordem.

**Nada disso é para rodar nesta sessão.**

---

## 3. Estado do git — LEIA ANTES DE QUALQUER COISA

Um commit foi feito (`e204e2a4`, a Fase 0). **As edições da Fase A estão na árvore de trabalho,
não commitadas**, por decisão de não commitar sem revisão do pesquisador:

```
 M rv-android/scripts/gh91_campaign.py       (+95/-?)
 M rv-android/scripts/gh91_gate.py           (+42/-?)
 M rv-android/scripts/gh91_sa_rerun.py       (+55/-?)
?? rv-android/tests/parity/test_gh91_completeness.py
?? rv-android/scripts/e3_preflight_instrument.py
```

`rv-android/scripts/validate_instrument_jca190.py` também aparece como `M`, mas **já estava
sujo antes desta sessão** — não é trabalho desta linha, não o toque.

**Confirme que essas edições ainda estão lá** antes de rodar qualquer coisa:
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
grep -n "is_complete" scripts/gh91_campaign.py | head        # deve haver 5+ ocorrências
grep -c "skipWtg" scripts/gh91_sa_rerun.py                    # deve ser 0
uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh91_completeness.py -q
```
Se o `grep` do `skipWtg` não der 0, as edições se perderam — **pare e reporte**, não refaça de
memória.

Commitar essas edições é uma boa ideia (P3: um commit, um estado consistente) — **pergunte ao
pesquisador antes**.

---

## 4. A DECISÃO QUE BLOQUEIA O LANÇAMENTO

**A campanha se recusa a começar.** `gh91_campaign.py:504` compara o pico de budget
(`ROUND_BUDGET_GIB` = **100 g**) com a RAM disponível (**98–99 GiB** nesta máquina) e aborta:

```
REFUSING: budget 100g exceeds free RAM 98.7g. Lower --budget-gib or override with --force.
```

A demanda **real** da rodada 1 é 3 × 32 g = **96 g**, e `--jvm-memory` é `-Xmx` puro sem
`-Xms` — teto preguiçoso, não reserva. As duas saídas são:

1. **`--force`** — a campanha tem o flag (`:452`). Mantém o budget em 100 g; a folga real
   existe porque nunca se pede mais que 96 g.
2. **Baixar `ROUND_BUDGET_GIB` para 96 g** em `gh91_campaign.py:78`. Não força nada, mas é
   editar constante de política.

**O pesquisador ficou de decidir e não decidiu.** Pergunte antes de lançar. Não escolha
sozinho.

Nota: `--budget-gib` existe no **driver** (`gh91_sa_rerun.py`), mas **não** na campanha — a
campanha lê a constante. Não adianta procurar o flag.

---

## 5. As rodadas, para você saber o que está olhando

Uma "rodada" **não é um lote de trabalho — é uma configuração de capacidade**
(`ROUND_CONFIG`, `gh91_campaign.py:77`). Quem vai para qual rodada é decidido pelo tier que a
Phase-7 mediu (`home_round`, `:210`, corte em 32 GiB).

| rodada | memória | timeout | budget | concorrentes | APKs do tier próprio |
|---|---|---|---|---|---|
| 1 | 32 g | 3600 s | 100 g | **3** | 27 (**26** pendentes: osmtracker já está pronto) |
| 2 | 120 g | 7200 s | 100 g | **1** | 3 — `org.wikipedia_50595`, `app.pachli_50`, `com.jerboa_87` |

**Não existe contagem de workers.** O `ThreadPoolExecutor` é criado com `max_workers = total`
(`gh91_sa_rerun.py:494`); quem limita é a memória: `_admits` (`:461-473`) admite job enquanto
`Σ --jvm-memory ≤ budget`. Daí 3 × 32 g na rodada 1. Na rodada 2 um job de 120 g excede o
budget inteiro e só roda numa máquina vazia — exceção de projeto R4, não empacotamento. A ordem
é *cheapest-first* pelo tempo da Phase-7 (`:489`).

**CPU não é o gargalo.** 64 núcleos, e o launcher não fixa thread nenhuma. Cada job é uma JVM
com Soot/spark essencialmente serial + GC. Três jobs ≈ 3 núcleos úteis. Quem limita é RAM.

A rodada 1 **sobe o orçamento de 11 APKs** que a Phase-7 rodou a 12 g/1800 s: todos passam a
32 g/3600 s.

**Quatro APKs da rodada 1 devem falhar por desenho** — `unchained`, `http_shortcuts`,
`securecamera`, `owncloud.notes` já estouraram exatamente 3600 s na Phase-7 e a rodada 1 lhes
dá os mesmos 3600 s. Quem os salva é a promoção para 7200 s. **É exatamente por isso que a
quarta edição era obrigatória**: sem ela, um APK morto dentro do WTG fica em disco com o
sentinela e nunca sobe.

**Tempo esperado:** o `--plan` projeta ~4,5 h a rodada 1 e ~3,1 h a rodada 2 com os tempos da
Phase-7; o plano orça **8–14 h** no total, com promoções.

---

## 6. Roteiro desta sessão

1. **Conferir a árvore** (§3). Se as edições sumiram, pare e reporte.
2. **Resolver a decisão do §4** com o pesquisador. Não lance antes.
3. **Conferir antes de rodar** — barato e obrigatório:
   ```bash
   cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
   export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
   uv run python scripts/gh91_campaign.py --plan
   uv run python scripts/gh91_sa_rerun.py --dry-run | head -20     # NÃO pode conter skipWtg
   ```
   Não exportar `JAVA_HOME` para 21 — Java 25 é o default da máquina e o build passou nele.
   `ANDROID_SDK_HOME` não precisa: `_gator_env()` cai para `ANDROID_HOME`.
4. **Lançar a campanha em background rastreado pelo harness** (nunca `nohup`/`setsid`):
   ```bash
   uv run python scripts/gh91_campaign.py --max-rounds 2        # + --force, se for a decisão
   ```
5. **Acompanhar** sem tocar no processo:
   ```bash
   tail -f /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg/REGISTRO.md
   ```
6. **Verificação pós-rodada — obrigatória, não opcional.** O sentinela sozinho não distingue
   WTG vazio de WTG truncado. Cruzar com `_progress` (snippet no §8).
7. **Gate A** — rodar o portão mecanizado, que agora tem a 3.2 forte e a 3.7:
   ```bash
   uv run python scripts/gh91_gate.py
   ```
   **Gate A fecha quando:** 30/30 JSON escritos; 3.1 cardinalidade PASS; 3.2 (sentinela **e**
   sem timeout) PASS; 3.3a/3.3b (chave aplicada) PASS; 3.4 (APK certo) PASS; 3.5 (superfície
   MOP, HARD STOP) PASS; e a 3.7 classificando os 30 em `ok`/`truncated`/`genuine_empty` sem
   nenhum `unclassified`. **Nenhum APK pode estar COMPLETE com `timed_out: true`** — se estiver,
   a 3.2 falha e o portão reprova.
8. **Reportar o resultado na conversa** e limpar os temp dirs vazados (§9, risco conhecido).

---

## 7. Arquivos relacionados

### Scripts (o que você vai rodar)
| arquivo | papel |
|---|---|
| `rv-android/scripts/gh91_campaign.py` | campanha, rodadas, promoção, `REGISTRO.md`; `is_complete` em `:126` |
| `rv-android/scripts/gh91_sa_rerun.py` | driver de uma rodada; argv do GATOR em `build_argv`; dispatcher em `_admits`/`run_all` |
| `rv-android/scripts/gh91_gate.py` | portão mecanizado 3.1–3.7 |
| `rv-android/scripts/gh91_record.py` | gerador do `record/` da rodada **anterior** — **ainda diz "WTG is skipped"**; se for usá-lo, corrija antes |
| `rv-android/tests/parity/test_gh91_completeness.py` | os 9 testes da quarta edição |
| `rv-android/30_apks.csv` | os 30, com `Mneut`, `manifest_package` e `relation` |

### Saídas
| caminho | papel |
|---|---|
| `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg/` | **a saída desta rodada**; hoje só o osmtracker |
| `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/` | rodada anterior sem WTG — **entregável assinado, NÃO sobrescrever** |
| `rvsec-dataset/static_analysis/` | os 345 JSON da Phase-7, com WTG e chave antiga nos 30 — **não tocar** |
| `rvsec-dataset-sa/logs/`, `_progress/` | argv na linha 1; `timed_out`, `returncode`, `seconds` |
| `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/` | diretório de entrega; hoje só proveniência e as duas listas |

### Fonte Java (para verificar mecanismo, nunca para editar)
| arquivo | o que tem |
|---|---|
| `rvsec/rvsec-android/rvsec-gator/client/.../RvsecAnalysisClient.java` | `:107` a linha `Filter package:`; `:169-170` a escrita pré-WTG; `:180-184` o retorno sob `skipWtg`; `:189` o `WTGBuilder.build()` |
| `.../clients/json/JsonReportWriter.java` | `:111`, o sentinela emitido **incondicionalmente** |
| `rv-android/lib/gator/gator` | launcher; `:113` o `sys.exit(-50)` do timeout, `:119` o `remove_temp_dirs()` que ele pula |

### Plano e auditoria
| arquivo | papel |
|---|---|
| `rv-android/docs/20260810_plano_prontidao_estudo03.md` | o plano |
| `rv-android/docs/20260811_handoff_execucao_prontidao_e3.md` | handoff da sessão anterior |
| `rv-android/docs/20260731_gh91_handoff_grupo5.md` | rodada anterior; `:126` tem a afirmação **refutada** sobre o sentinela |
| `rv-android/docs/20260617_sweep_gh66_validacao_wtg.md` | teto do WTG; `:38` é baseline **pré**-gh66 |

---

## 8. Comandos úteis

```bash
# Raízes
RVA=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
W=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
DS=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET
export RVSEC_HOME=$W/rvsec

# Classificação pós-rodada (o sentinela sozinho não serve)
cd $RVA && uv run python - <<'PY'
import json, glob, os
D="/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91_wtg"
for f in sorted(glob.glob(D+"/_progress/*.json")):
    p=json.load(open(f)); j=p.get("json_path")
    n=len(json.load(open(j)).get("transitions",[])) if j and os.path.exists(j) else -1
    flag="SILENT-EMPTY" if (n==0 and p.get("timed_out")) else ""
    print(f"{p['apk']:48} tr={n:<6} {p['sa_status']:12} to={p.get('timed_out')} rc={p['returncode']} {flag}")
PY

# Três sinais do artefato MOP de um JSON
cd $RVA && uv run python - <<'PY'
import sys, json
sys.path.insert(0,"modules/aperv-tool/src")
from aperv_tool.tools.aperv import derive_mop_artifact as D
a=D.derive(json.load(open("<caminho>.apk.json")), "x", "")
print(a["stats"]["flagged"], a["stats"]["wtgEdges"], len(a["mopActivities"]))
PY

# Tipos de evento das transições de um JSON
python3 -c "
import json,collections,sys
j=json.load(open(sys.argv[1]))
print(collections.Counter(e['type'] for t in j['transitions'] for e in t['events']).most_common())
" <caminho>.apk.json

# Chave e argv de uma análise da Phase-7 (referência, read-only)
grep 'Filter package' $W/rvsec-dataset-sa/logs/<apk>.apk.log
head -1 $W/rvsec-dataset-sa/logs/<apk>.apk.log

# Testes (flags obrigatórias)
cd $RVA && uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh91_completeness.py

# Temp dirs vazados pelo timeout do GATOR
du -sh /tmp/* 2>/dev/null | sort -h | tail
```

---

## 9. Aprendizados — não repita

Os 14 do handoff anterior (`20260811_handoff_execucao_prontidao_e3.md` §6) continuam valendo.
Estes são **novos, medidos nesta sessão**:

1. **O `mvn install` de raiz sobrescreve os jars do GATOR em `lib/gator/`.** O hand-off
   `main.basedir` do reator republica `rvsec-gator.jar` e `rvsec-analysis-client.jar` a cada
   build, e os sha256 mudaram em relação aos que o plano registrou (`30160481…`, `207b61f7…`).
   Como `lib/gator/*.jar` é **gitignored**, os anteriores não são recuperáveis. As fontes do
   gator são **idênticas** desde `4280f3bd` (diff de `src/main` vazio; só POMs, docs e testes
   mudaram), então o comportamento não muda — mas o artefato de referência que a pendência
   **P13** propunha comparar byte a byte **foi perdido**. Está registrado na `PROVENIENCIA.md`.
2. **A campanha aborta se o budget exceder a RAM livre** (`gh91_campaign.py:504`). O flag é
   `--force`; `--budget-gib` só existe no driver.
3. **O build do reator leva ~78 s, não 30 min.**
4. **As Fases A e B não cabem juntas nesta máquina.** O paralelismo que o plano §5 assume não
   existe: a rodada 1 pede 96 g de 98–99 GiB disponíveis. Elas serão sequenciais.
5. **A instrumentação NÃO depende da análise estática.** Verificado no fonte: o instrumentador
   `dexlib2` não tem uma referência sequer a `.apk.json`, `static_analysis`, `code_package` ou
   `reachability` (`modules/rv-instrumentation-dexlib2/src/`, `-core/src/`, busca vazia); e no
   `pre_processor.py:101-117` a ordem é monitores → instrumentação → **análise estática por
   último**. A ordem "análise estática primeiro" é decisão do pesquisador, não dependência
   técnica — e ele a tomou.
6. **`complete: true` não significa WTG completo**, e agora há teste que prova a consequência:
   sem a correção, `pending_for_round` **não promove** o APK morto no WTG.
7. **O gate barato reproduz o plano exatamente** (287 transições, 161 cliques, 97 arestas) mas
   com **232 classes contra 140 da Phase-7** — ver a observação em aberto no §2.2 sobre o WTG
   possivelmente não depender de `codePackage`.
8. **Vazamento de temp dir.** No timeout, `sys.exit(-50)` (`lib/gator/gator:113`) pula
   `remove_temp_dirs()` (`:119`). Com 30 APKs × 2 rodadas isso soma GB em `/tmp`. Limpar
   depois da campanha.
9. **Resume mascara retry.** O resume do driver é por existência do JSON
   (`gh91_sa_rerun.py:614-620`); qualquer arquivo deixado para trás faz a rodada 2 pular
   exatamente o APK que falhou. A campanha resolve movendo para `_superseded/` antes do retry.
   Por isso o `OUT_DIR` é novo.
10. **Não sugerir atalhos que reaproveitem artefatos parciais.** O pesquisador já recusou
    explicitamente um "join" entre o WTG de junho e a reachability de julho. Integridade acima
    de tempo.
11. **Handoff, relatório e aritmética não são verificação.** Abrir o fonte e citar
    `arquivo:linha` é.

---

## 10. Regras de trabalho — seguir rigorosamente

Além do `CLAUDE.md` da raiz (`rvsec/CLAUDE.md`) e do módulo (`rvsec/rv-android/CLAUDE.md`), que
são autoritativos:

- **Workflow**: `docs/WORKFLOW.md`. Para qualquer coisa rastreada em `openspec/changes/gh<N>-*/`,
  invocar as skills OpenSpec via a ferramenta `Skill`. **Nunca** criar ou reescrever artefato
  OpenSpec com `Write`/`Edit` direto. *(A Fase A não é uma change OpenSpec — é execução do
  plano. Não abra change para ela.)*
- **Emulador — NÃO TOCAR.** Nunca iniciar, parar ou gerenciar emulador manualmente, em nenhum
  contexto. Nesta sessão nenhum emulador é necessário.
- **Não mexer no gator.** `rvsec-gator` só muda por erro grosseiro; melhorias de substrato vão
  por offline ou pelo consumidor. **Não reconstrua o reator** — isso sobrescreveria os jars de
  novo (aprendizado 1) e quebraria a proveniência já assinada.
- **Background**: processos longos vão em background rastreado pelo harness, nunca
  `nohup`/`setsid`.
- **Commits**: nunca adicionar `Co-Authored-By` nem qualquer trailer de coautoria.
- **Português**: sempre com acentuação correta, mesmo que o pesquisador escreva sem acentos.
- **Testes**: `uv run pytest --import-mode=importlib -o "addopts="` — sem essas flags a coleta
  quebra.
- **P1–P4** (simplicidade, documentação narrativa, sem retrocompatibilidade, comentários do
  estado atual) governam todo código, comentário e documento.
- **Não editar handoffs e prompts do pesquisador.** Progresso se reporta na conversa.
- **`experimento-cal` é histórico** — não editar nem adaptar.
- **Pergunte antes de decidir o que é do pesquisador.** Ele interrompeu o piloto da Fase B
  justamente porque uma ordem foi assumida sem perguntar.

---

## 11. O que NÃO fazer nesta sessão

- **Não rodar a Fase B.** Nada de `rv-experiment run`, nada de piloto, nada de instrumentação.
  O pesquisador parou isso explicitamente.
- **Não reconstruir o reator** (`mvn install`) — a Fase 0 está fechada e assinada.
- Não reabrir decisão congelada da §2 do plano (specs `jca`, corpus 163, branch `modules`, host
  sem Docker, reanalisar só os 30, diretório novo sem hardlink).
- Não sobrescrever `RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`, `rvsec-dataset/static_analysis/`,
  `rvsec-dataset/instrumented_apks/`, `APKS_INSTRUMENTED_*`, nem as colunas `sa_*` de
  `ase-journal/dataset/dataset.csv`.
- Não decidir sozinho o `--force` × budget 96 g (§4).
- Não expandir para a execução do experimento nem para a escrita da tese.
- Não criar branch.
