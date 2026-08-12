# Handoff — executar a campanha `comp162`

Sessão nova. Este documento é o estado completo; não presuma nada além dele sem verificar no
código ou nos artefatos.

---

## 1. O objetivo

**Rodar a campanha de comparação `comp162`** — APE original × APE-RV com e sem guia MOP, sobre o
corpus recém-instrumentado do Estudo 03 — e depois consolidar, analisar e ler o resultado contra a
campanha anterior (`cmp163`).

**Isto NÃO é o experimento final do Estudo 03.** É um ensaio: o pesquisador quer ver como a
instrumentação nova se comporta antes que o experimento final dependa dela, e comparar
rigorosamente com a campanha anterior, que é a base. Não trate esta corrida como se fosse o final,
e não deixe o relatório sugerir isso.

O andaime inteiro está pronto e verificado. **O que falta é operar.**

---

## 2. O desenho, em números

| | |
|---|---|
| Braços | `ape` · `aperv:mop_off_llm_off` · `aperv:mop_on_llm_off` |
| Corpus | 162 APKs — `selected162.txt`, sha256 `3bbc5fa91ba2cf3cd59e040237501caa0718735647d2c6881e09581f1e972c85` |
| Repetições | **3** |
| Timeout | 300 s por task |
| Total | **1458 identidades**, 8 containers |
| Wall-clock projetado | **≈ 20 h** (container mais cheio: 21 APKs × 3 × 3 = 189 runs × 370 s) |
| Imagem | `phtcosta/rvandroid:0.9.3-comp162` — **ainda não construída** |
| Jar | `ape-rv.jar` local `a7eddf5a…` por bind-mount — o mesmo da `cmp163` e da perna B da gh97 |
| SGLang / GPU | **não** — nenhum braço LLM nesta grade |
| Diretório | `experimento-comp162/` |
| Plano | `docs/20260812_comp162.md` |

Alvo por container (o monitor já calcula sozinho lendo o filtro): `comp162_00` e `comp162_02` →
189 runs; os outros seis → 180 runs.

---

## 3. O que já foi feito (não refazer)

Tudo abaixo está no disco, verificado, e **nada foi commitado** — `experimento-comp162/` e
`docs/20260812_comp162.md` estão untracked; o `.gitignore` já recebeu as entradas de `results/` e
`results_smoke/` da campanha.

1. **Diretório `experimento-comp162/` montado** no molde do `experimento-rearch-aperv/`, com a
   configuração da `cmp163`.
2. **Filtros derivados e verificados** — `filters/batch_00..07.txt`, lotes
   `[21, 20, 21, 20, 20, 20, 20, 20]` = 162. Herdados dos filtros da `cmp163` menos
   `info.dvkr.screenstream_44000.apk`. Mais `filters/smoke_00.txt` e `smoke_01.txt`.
3. **Censo do substrato gerado** — `censo_substrato.csv`, 162 linhas, via `derive()`.
4. **Manifesto gerado** de `ApeRVTool.get_variants()` — `manifest.json`, 1458 identidades previstas,
   `image.id` **nulo** (a preencher após o build).
5. **Composes escritos e validados** (`docker compose config` passa nos dois).
6. **Onze scripts escritos**, e a cadeia de análise **verificada de ponta a ponta** contra os dados
   reais da `cmp163` (ver §7).
7. **Diretórios de saída criados** — `results/comp162_00..07/` e
   `results_smoke/comp162smoke_00..01/`, vazios.

---

## 4. Próximos passos, em ordem

### Passo 0 — confirmar que o push aconteceu

O `docker/rvandroid/Dockerfile` faz `git clone --branch ${RVSEC_BRANCH}` de
`https://github.com/PAMunb/rvsec.git`. **Ele clona o remoto, não copia a árvore local.** O
pesquisador disse que ia fazer um push; sem ele, a imagem sai sem os commits novos — inclusive sem
a guarda INV-APV-60, que é a razão do rebuild.

Confirme com o pesquisador, ou verifique que `origin/modules` contém `c1d28365`:

```bash
git fetch origin modules && git branch -r --contains c1d28365
```

Se não contiver, **pare e avise**. Não construa a imagem.

### Passo 1 — construir a imagem

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
docker build --no-cache --build-arg RVSEC_BRANCH=modules \
  -t phtcosta/rvandroid:0.9.3-comp162 docker/rvandroid
```

- **`--no-cache` não é opcional.** O `RUN git clone` é uma camada como outra qualquer; sem
  invalidar o cache o Docker reusa a camada da `0.9.3-rearch` e a imagem sai idêntica à antiga.
- **Não use `docker/rvandroid/build.sh`** — ele marca `0.9.3` e `latest`, que são a identidade da
  imagem da perna A do E3 e não podem ser sobrescritas.
- A base `phtcosta/rvandroid_tools:0.9.3` já existe localmente; só a camada 4 é reconstruída.
- É demorado (`mvn install` do reactor inteiro + `uv sync` + build do `ape`). Rode em background e
  **não fique em laço de espera** — veja §6.

### Passo 2 — fechar o manifesto com o ID da imagem

```bash
cd experimento-comp162
uv run python scripts/make_manifest.py \
  --image-id "$(docker inspect -f '{{.Id}}' phtcosta/rvandroid:0.9.3-comp162)"
```

Confirme na saída: `corpus_basis = selected162:3bbc5fa9…` e `identidades previstas = 1458`.

### Passo 3 — smoke, e os sete portões

```bash
docker compose -f docker-compose.smoke.yml up -d      # 2 apps, 1 rep, 120 s, 6 identidades
uv run python scripts/smoke_gates.py
```

**O critério de aceitação é o script, não o `up -d`.** Ele sai com código 1 em qualquer FAIL. Os
sete portões estão descritos em `docs/20260812_comp162.md` §7. O portão 7 é o novo: confere que a
guarda INV-APV-60 está **dentro da imagem** (`docker run --entrypoint grep`), que é a razão do
rebuild — se ele falhar, o Passo 1 não pegou os commits novos.

O smoke leva ~2 ciclos de emulador; consulte a saída **quando fizer sentido**, sem laço.

Só depois de **7/7 PASS**:

```bash
docker compose -f docker-compose.smoke.yml down       # aqui o `down` PODE — traços já lidos
```

### Passo 4 — a campanha

```bash
docker compose up -d
```

~20 h. Enquanto roda, consulte sob demanda (§6):

```bash
bash scripts/monitor.sh     # progresso por container, com alvo por lote
bash scripts/cycle.sh       # monitor + reparo + resume + admissibilidade
```

Ao fim, **uma passada de resume**: re-rodar `docker compose up -d`. Ele pula identidade
`COMPLETED` e re-executa `ERROR`/`FAILED`. Confirme que as identidades distintas batem 1458.

### Passo 5 — consolidar e analisar

**Não dê `down` antes de extrair os traços** — os artefatos vivem no device e são efêmeros.

```bash
uv run python scripts/consolidate.py       # DEMORA: lê ~1458 logcats (~7,5 GB). Rode em background.
uv run python scripts/analise.py
uv run python scripts/compare_cmp163.py
```

### Passo 6 — o relatório

Escreva `docs/20260813_resultados_comp162.md` (ou a data do dia) no molde de
`docs/20260807_resultados_cmp163.md`, que é o padrão desta linha de trabalho. Separe
explicitamente a **leitura confirmatória** (as quatro hipóteses declaradas no plano, e nada além) da
**investigação exploratória** (tudo que for concebido depois de o resultado existir).

---

## 5. Workflow — seguir rigorosamente

- **`CLAUDE.md` da raiz e do `rv-android` mandam.** Leia antes de agir.
- **NUNCA gerenciar emulador à mão.** Nada de `emulator`, `adb emu kill`, start/stop. O
  `rv-platform` cuida do ciclo inteiro. Regra permanente, sem exceção, em qualquer contexto.
- **Commits**: o pesquisador é o autor único — **nunca** adicionar `Co-Authored-By` nem qualquer
  trailer de coautoria. Não commitar nem fazer push sem pedido explícito.
- **Esta campanha não é uma change OpenSpec** e não precisa de uma. **Mas**: se em algum momento
  for preciso mexer em `modules/**`, aí o workflow do `docs/WORKFLOW.md` passa a valer e as skills
  OpenSpec são obrigatórias (invocar pela ferramenta `Skill`, nunca escrever os artefatos à mão).
- **Skill de apoio**: `/rv-experiment-compare` documenta o ciclo de 4 fases (setup, run, monitor,
  consolidação) e os gotchas de campo. Vale reler antes do Passo 3.
- **Português com acentuação correta** em toda documentação. O pesquisador escreve sem acento
  (teclado não-ABNT); a escrita do assistente é acentuada.
- **P1–P4** (`CLAUDE.md`): simplicidade, documentação narrativa que explica o *porquê*, sem
  retrocompatibilidade, comentários do estado atual (nada de "migrado de X").

---

## 6. NÃO criar monitoramento automático

**Instrução explícita do pesquisador.** Nada de cron, `/loop`, `Monitor` persistente, `watch` em
background, ou laço de polling para acompanhar a campanha.

Consulte o estado **sob demanda**, rodando `bash scripts/monitor.sh` quando houver motivo. Se
precisar esperar algo pontual terminar (o `docker build`, o `consolidate.py`), use um comando em
background que **sai sozinho quando a condição é satisfeita** — uma notificação, não um fluxo.

Nunca fabrique nem antecipe o resultado de algo que ainda está rodando.

---

## 7. O que já foi verificado, e como

A cadeia de análise **nunca rodou sobre dados da comp162** (não existem ainda), mas foi validada
contra os dados reais da `cmp163`: liguei `results/comp162_NN` aos containers da `cmp163` por
symlink e rodei `consolidate → analise → compare_cmp163` sobre aqueles 489 runs. O fixture foi
removido depois; `results/` está vazio.

**A cadeia reproduziu a tabela publicada da `cmp163` linha por linha:**

| | publicado (`docs/20260807_resultados_cmp163.md` §4.2) | reproduzido |
|---|---|---|
| Admissibilidade | n=160, exclui `app.pachli_50`, `org.wikipedia_50595`, `com.starry.myne_500` | idêntico, com os mesmos critérios por braço |
| H1 `cov_mop` | 34,27 / 31,58 · 79/49 · p=0,00097 | idêntico |
| H2 `cov_act` | 100,00 / 66,67 · 70/9 · p<0,00001 | idêntico |
| H3 `cov_method` | 32,53 / 33,43 · 65/78 · p=0,0144 | idêntico (0,01435) |
| H4 `cov_mop` | 34,27 / 31,48 · 81/47 · p=0,00002 | idêntico |
| substrato n=29 | `cov_act` p=0,0009 | idêntico (0,00093) |

O autoteste do `compare_cmp163.py` (fixture contra si mesmo) dá **0 vitórias, 0 derrotas, p=1,0**
nas 12 linhas.

Uma divergência **esperada**: o subgrupo "três sinais" sai n=11 em vez do n=10 publicado, porque o
censo novo põe o `binaryeye` no grupo (WTG recuperado). É o efeito que a §6.1 do plano vai medir.

---

## 8. Aprendizados — não re-aprender

### Da montagem desta campanha (três defeitos que só o ensaio pegou)

1. **O braço `ape` grava `variant='default'` no `tool_config`**, mas o consolidador colapsa o
   rótulo para `ape` seco — e o arquivo de logcat se chama `..__ape.logcat`, não
   `..__ape:default.logcat`. Um rótulo divergente fazia **todas** as aplicações caírem por "braço
   sem execução", e faria o `mop_total` do braço `ape` contar zero em silêncio. A regra vive em
   `scripts/admissibility.py::arm_label` e **em nenhum outro lugar** — os três consumidores a
   importam. Não reintroduza uma cópia.
2. **APK nos resultados e fora do censo** estourava `KeyError`. Agora é avisado em voz alta e fica
   fora dos estratos de substrato — nunca empurrado para o grupo "sem substrato", porque
   desconhecido não é zero.
3. **Arredondar o CSV que alimenta a estatística injeta ruído com sinal aleatório.** `round(x, 4)`
   dava erro de ~5e-05 por célula; comparar dados idênticos produzia 87×70 e p=0,25 onde o correto
   é empate exato. `per_apk_admissivel.csv` sai com precisão cheia; `per_apk_paired.csv` mantém 4
   casas porque é para leitura e não entra em teste.

### Decisões de desenho que têm razão de ser

4. **A partição é herdada da `cmp163`, não gerada por round-robin.** Assim cada aplicação roda no
   mesmo índice de container nas duas campanhas e efeito-de-container cancela na diferença pareada.
   Round-robin sobre a lista nova faria o oposto: remover um elemento renumera tudo depois dele e
   desloca metade do corpus.
5. **A regra de admissibilidade é a tolerante, por decisão do pesquisador.** Réplica inadmissível é
   **descartada**; a aplicação só sai quando **algum braço fica sem nenhuma réplica admissível**. É
   para isso que R=3 existe — na `cmp163`, nove das dez re-execuções foram `adb install` pegando o
   device offline, e uma regra estrita jogaria fora aplicação boa. **Não reintroduzir a regra
   estrita.** Células com menos de 3 réplicas são reportadas, não absorvidas.
6. **R=3 é a mudança de desenho.** Fecha a lacuna da §7 do relatório da `cmp163`: com R=1 não há
   medida de variância dentro da célula. A dispersão entre réplicas é resultado de primeira classe,
   não nota de rodapé.

### Sobre a leitura do resultado

7. **Três coisas diferem da `cmp163` simultaneamente** — binários reinstrumentados, imagem com a
   guarda INV-APV-60, e substrato com **10 WTGs recuperados** pela re-análise da gh91 (41 → 51 com
   WTG povoado). **Nenhuma diferença medida contra a `cmp163` é atribuível a uma causa isolada.**
   O `compare_cmp163.py` é descritivo e diz isso na própria saída. Há ainda a assimetria R=3 × R=1.
8. **O que NÃO difere**, e atenua: o braço `ape` roda **o mesmo binário** nas duas campanhas
   (`ape.jar` é comitado e não muda desde fevereiro), e a partição é herdada.
9. **P11 / substrato.** Dos 162: 41 têm WTG cru vazio (`transitions==0`) e **todos os 41 se
   declaram `complete=true`** — 40 truncados + 1 genuinamente vazio, separáveis só pelo `timed_out`
   do `_progress` no `rvsec-dataset-sa`. Mais relevante para ler a cobertura: **111 dos 162
   entregam grafo de clique vazio** (`wtg_edges==0`) ao braço guiado, depois da derivação. São
   coisas diferentes — a visão só-de-clique descarta janela sem widget e funde diálogo. Por isso a
   análise estratifica.
10. **Esta grade não separa a guia MOP do gatilho de atividade.** Os quatro deltas do reach package
    entram e saem juntos; separá-los exigiria um braço com `ACTIVITY_TRIGGER` ligado e pesos MOP
    zerados, que não existe aqui. Limitação herdada da `cmp163` §6 — registrar, não contornar.

### Operacionais

11. **Contar por IDENTIDADE** `(apk, tool, variant, rep, timeout)`, nunca por registro: o resume
    **acrescenta** em vez de sobrescrever. E **nunca** `grep '"state": "COMPLETED"' tasks.json` —
    conta em dobro por causa de `state_transitions`.
12. **Atraso aparente não é travamento.** O `tasks.json` só é gravado quando a task **fecha**, então
    a seguinte já está em voo e invisível. O atraso normal chega a ~2 ciclos (~12 min a 300 s). Só
    suspeitar acima disso, e confirmar com `docker logs`.
13. **Não dar `down` antes de extrair os traços.** Artefatos são efêmeros no device.
14. **`consolidate.py` demora minutos** — lê todos os logcats. Rode em background.
15. **O reparo só toca container que NÃO está rodando.** Reescrever o `tasks.json` de um container
    vivo perde a corrida com a escrita atômica dele. O `cycle.sh` já respeita isso.
16. **Com a guarda INV-APV-60 na imagem, zero reparos é o resultado esperado** — a ferramenta
    levanta exceção no ato do truncamento e o resume comum recupera. Se o `repair.py` encontrar
    trabalho, isso é informação, não rotina.

---

## 9. Arquivos

### Da campanha

| Caminho | Papel |
|---|---|
| `experimento-comp162/README.md` | O desenho e o procedimento |
| `experimento-comp162/manifest.json` | Braços, corpus, imagem, 1458 identidades previstas |
| `experimento-comp162/docker-compose.yml` | 8 containers |
| `experimento-comp162/docker-compose.smoke.yml` | 2 containers, 6 identidades a 120 s |
| `experimento-comp162/filters/` | A partição herdada + os dois filtros de smoke |
| `experimento-comp162/censo_substrato.csv` | Censo por APK, via `derive()` |
| `experimento-comp162/scripts/admissibility.py` | **A regra de admissibilidade, num lugar só** |
| `experimento-comp162/scripts/make_filters.py` | Deriva e verifica `filters/` (`--check` não escreve) |
| `experimento-comp162/scripts/censo_substrato.py` | Gera o censo |
| `experimento-comp162/scripts/make_manifest.py` | Gera o manifesto de `get_variants()` |
| `experimento-comp162/scripts/smoke_gates.py` | Os sete portões; sai 1 em FAIL |
| `experimento-comp162/scripts/monitor.sh` | Progresso por container |
| `experimento-comp162/scripts/repair.py` | Rede de segurança para run truncado |
| `experimento-comp162/scripts/cycle.sh` | monitor → reparo → resume → admissibilidade |
| `experimento-comp162/scripts/consolidate.py` | `tasks.json` + logcats → `consolidado/` |
| `experimento-comp162/scripts/analise.py` | Admissibilidade, dispersão, H1–H4 por estrato |
| `experimento-comp162/scripts/compare_cmp163.py` | Leitura pareada contra a campanha anterior |
| `docs/20260812_comp162.md` | **O plano** |

### De contexto (ler quando precisar, não tudo de saída)

| Caminho | Por quê |
|---|---|
| `docs/20260806_cmp163.md` | Plano da campanha de referência |
| `docs/20260807_resultados_cmp163.md` | Resultados dela — o padrão do relatório final |
| `docs/20260812_registro_execucao_prontidao_e3.md` §3 | Montagem do corpus dos 162 e o P11 |
| `docs/20260810_plano_prontidao_estudo03.md` | O plano de prontidão do Estudo 03 |
| `data/results/cmp163_consolidado/` | Os CSVs da campanha anterior (o comparador lê daqui) |
| `data/results/cmp163_substrato.csv` | Censo antigo (o comparador diffa contra o novo) |
| `modules/aperv-tool/CLAUDE.md` | Variantes e invariantes (INV-APV-*) |
| `experimento-rearch-aperv/README.md` | O molde do diretório e o precedente da gh97 |
| `.claude/skills/rv-experiment-compare/SKILL.md` | Ciclo de 4 fases e gotchas de campo |

### Dataset

`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`
— 162 `.apk` + 162 `.apk.json` co-locados + `selected162.txt`. 4,3 GB. Montado em 2026-08-12
(`c5ac22db`). Verificado: pareamento 1:1, lista idêntica ao conteúdo.

---

## 10. Estado do git

Nada commitado. Untracked: `experimento-comp162/`, `docs/20260812_comp162.md`, e este handoff. O
`.gitignore` foi editado (entradas de `/experimento-comp162/results/` e `results_smoke/`) — é a
única mudança em arquivo versionado.

Branch: `modules`. Não commitar nem fazer push sem pedido explícito do pesquisador.
