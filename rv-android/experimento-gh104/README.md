# `experimento-gh104` — a grade da `comp162` sobre as especificações novas

**O fator em estudo é o conjunto de specs, e só ele.** Esta campanha roda exatamente o
desenho da `experimento-comp162/` — mesma variante de instrumentação (`dexlib2`), mesmo
corpus de 162 aplicações, mesmos três braços, R=3, T=300 s, 8 containers — trocando as 23
especificações do `jca` pelas **24** do `jca_android` que as changes
`gh104-legible-violation-reports` e `gh105-predicate-wiring` produzem em conjunto. Tudo o que
difere, difere de propósito; qualquer outra diferença tiraria a atribuição.

> **Estado em 2026-08-24 (HEAD `6192b57a`).** A gh104 está 106/109 (abertas: 10.4, 10.5, 10.8), a
> gh105 72/74, e o conjunto sucessor existe em disco. Este arquivo dizia **21** specs até 24/08 —
> o número vinha de uma deleção que a **D-11** retirou; a gh105 depois somou `IvChainJunction.mop`.
> `23 + 1 = 24`. Ver `CONTEXTO.md` §3.1.

A pergunta é dupla: **o conjunto de violações mudou?** e **para as violações que os dois
lados enxergam, o relato ficou legível?** A segunda é a razão de a change existir — 79,91 %
das mensagens da `comp162` são o literal `unknown`, e mais 98 terminam em `but found .`,
sem valor observado.

Decisões fechadas, bloqueadores e caminhos com linha: **`CONTEXTO.md`** (leia inteiro antes
de tocar em qualquer coisa). O que muda na saída, com citação: `docs/gh104_mudancas_observaveis.md`.
Runbook dos estágios 0 e 1: `instrumentacao/README.md`. Este arquivo cobre os **estágios 2 e 3**.
O que mudou entre 18/08 e 24/08, com o comando que mede cada número:
`docs/20260824_reconciliacao.md`.

## O desenho

| | |
|---|---|
| Braços | `ape` · `aperv:mop_off_llm_off` · `aperv:mop_on_llm_off` |
| Corpus | os mesmos 162 nomes da `comp162`, reinstrumentados com as specs novas |
| Spec set | **`jca_android`** — o fator em estudo |
| Instrumentação | **`dexlib2`**, feita no estágio 1, no host |
| Repetições | 3 |
| Timeout | 300 s por task |
| Total | **1458 identidades**, 8 containers, ≈ 20 h |
| Imagem | `phtcosta/rvandroid:0.9.3-gh104` (a construir; `${RV_IMAGE}` sobrepõe) |
| Jar | `ape-rv.jar` local por bind-mount — o mesmo da `comp162` |
| SGLang | não — nenhum braço LLM |
| Referência | `experimento-comp162/consolidado/per_apk_admissivel.csv` |

## Três coisas que esta campanha faz e a `comp162` não fazia

**Os monitores são novos.** A `comp162` reusou um `monitors_master` pré-gerado; aqui as
specs mudaram, então o estágio 0 gera de novo — **uma vez, sequencial**. Geração
concorrente não é uma otimização arriscada, é um defeito: o JavaMOP estagia os `.rvm` num
diretório compartilhado e o gerador os **move** de lá, então N gerações se roubam, o
`ErrorHandler` engole a falha, e o lote sai **tecido sem monitores, reportando sucesso**.

**Os `.apk.json` são reusados da `comp162`** (decisão D-c). Isso mantém o denominador de
cobertura idêntico nos dois lados, que é a condição para a diferença pareada ser
atribuível. O preço, que precisa aparecer em **qualquer** leitura: `cov_mop` desta campanha
continua medindo o alcance das **23 specs do `jca`**, não das **24** novas. Não é "cobertura
das specs novas" — é a mesma régua da `comp162`, aplicada aos dois lados de propósito.

Desde o commit `86a8f178` (24/08) essa é uma **escolha de método**, não uma necessidade: a análise
estática passou a ler o conjunto que o experimento instrumenta, então medir a cobertura das 24
specs novas é possível. Custaria dois denominadores diferentes e uma diferença pareada não
atribuível. Se esse número for pedido depois, é uma terceira medição, não um substituto.

**Há um segundo portão.** O smoke da `comp162` perguntava se a configuração resolve; aqui
isso é necessário e não é suficiente. `gh104_gates.py` roda sobre os mesmos resultados e
pergunta se a promessa saiu no artefato.

## A partição é herdada e apenas podada

`filters/batch_00.txt` … `batch_07.txt` vêm **verbatim** de `experimento-comp162/filters/`,
com as aplicações que não sobreviveram ao estágio 1 removidas **no lugar** — sem renumerar,
sem refazer o round-robin.

O motivo é o pareamento. As duas campanhas rodam no mesmo host com oito containers
disputando CPU, e um container é sistematicamente mais lento que outro ao longo da corrida.
Preservar o índice de container por aplicação é o que faz esse efeito **cancelar** na
diferença pareada em vez de virar parte dela. Gerar round-robin sobre a lista de
sobreviventes faria o oposto: remover um elemento renumera tudo depois dele e desloca cerca
de metade do corpus — foi o custo que a emenda 01 da gh97 teve de assumir e registrar.

O preço da poda é que os lotes ficam desiguais e um container termina antes, mudando a
contenção do host ao longo do tempo. Custo de segunda ordem, aceito e **impresso** por
`make_campaign_filters.py` para ser visto, não descoberto depois.

> `filters/` guarda **dois** particionamentos diferentes. `s0.txt` … `s7.txt` são os shards
> da **instrumentação** (estágio 1), e existem só para dividir trabalho entre processos
> concorrentes no host. `batch_00.txt` … `batch_07.txt` são a partição da **campanha**.
> Confundir os dois quebra o pareamento sem dar erro.

---

## Runbook

### 0. Pré-requisitos que este diretório não resolve

Antes de qualquer coisa aqui, os estágios 0 e 1 têm de estar prontos e os bloqueadores B1,
B2 e B3 do `CONTEXTO.md` fechados: as specs novas implementadas, o reator Java reconstruído
e **instalado** no repositório local (`/home/pedro/desenvolvimento/repository`), e o push em
`origin/modules` feito — o `Dockerfile` **clona do GitHub**, não copia a árvore local.

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
git push origin modules
docker build --no-cache --build-arg RVSEC_BRANCH=modules \
  -t phtcosta/rvandroid:0.9.3-gh104 rv-android/docker/rvandroid
```

**`--no-cache` não é opcional**: o `RUN git clone` é uma camada como qualquer outra e, sem
invalidar o cache, a imagem sai sem nenhum commit novo. **Não usar `docker/rvandroid/build.sh`
como está**: ele marca `0.9.3` e `latest`, o que apagaria a imagem que reproduz a `comp162`
e tornaria a campanha de referência irreproduzível.

### 1. Preparação (offline, sem emulador)

```bash
cd experimento-gh104

# a partição da campanha: herda da comp162 e poda o que caiu no estágio 1
uv run python scripts/make_campaign_filters.py --check     # relata, não escreve
uv run python scripts/make_campaign_filters.py

# o manifesto, gerado de get_variants() — nunca transcrito à mão
uv run python scripts/make_manifest.py \
  --image-id "$(docker inspect -f '{{.Id}}' phtcosta/rvandroid:0.9.3-gh104)"

# o censo do substrato; tem de bater com o da comp162, porque os .apk.json são os dela
uv run python scripts/censo_substrato.py
diff censo_substrato.csv ../experimento-comp162/censo_substrato.csv   # esperado: vazio
```

**Depois do `make_manifest.py`, colar o `corpus_basis` impresso nos dois composes**, no
lugar de `SUBSTITUIR_APOS_MONTAR_CORPUS`. Ele tem duas partes, `<id>:<sha256>`, e o sha256
é o do conteúdo da lista de nomes: como os 162 nomes são os mesmos da `comp162`, as listas
podem ser byte-idênticas e **o digest sozinho não distingue as campanhas**. Quem distingue
é o identificador, `selected162gh104`.

### 2. Smoke — e são DOIS portões

```bash
docker compose -f docker-compose.smoke.yml up -d    # 2 apps x 3 braços x 1 rep x 120 s

uv run python scripts/smoke_gates.py                # portões de execução (7)
uv run python scripts/gh104_gates.py \
    --results-glob 'results_smoke/gh104smoke_*/gh104smoke_*' --label smoke-gh104

docker compose -f docker-compose.smoke.yml down     # aqui o down PODE
```

`smoke_gates.py` pergunta se a **configuração resolve**: identidades completas e limpas,
cobertura não nula, `RUN_START` com o preset e as features de cada braço, `corpus_basis`
batendo com o manifesto, `ape.mopDataPath` presente, zero `VerifyError`, guarda INV-APV-60
dentro da imagem. Ele também extrapola o ciclo por run a 300 s, que é o que calibra o
wall-clock da corrida completa.

`gh104_gates.py` pergunta se a **promessa da change saiu no artefato**: zero mensagens
`unknown`, zero terminando em `but found .`, `errors.csv` com 13 colunas, `unique_msg` com
sete partes, envelope v1 bem-formado, `__EVENTNAME` não vazado, `code`/`event` em
`UNSPECIFIED` e nunca vazios. Ele lê **duas populações** — o `errors.csv` e o `.logcat` cru
— porque o CSV é o fim de um transporte de dez etapas e uma divergência entre as duas é ela
mesma um defeito.

> **Reparado em 25/08 (F1).** O G5 validava o KIND do `code=` contra um conjunto congelado que
> **não incluía `NOBS`**, a família *not observed* da gh105 (INV-INS-143) — 30 dos 114 códigos do
> `codes.csv`, e o portão teria reprovado uma campanha correta. Agora o vocabulário vem do
> **`codes.csv` do conjunto sob medição**, via `--codes-csv`: passe sempre o caminho, porque sem
> ele o portão cai na lista congelada e não verifica se o código **existe** — só se o KIND é
> plausível. Com o catálogo, um envelope perfeito cujo código não está no `codes.csv` reprova
> como deriva de proveniência (o APK carrega monitores de outro conjunto).

Seis identidades bastam para **reprovar** um envelope malformado; não bastam para confirmar
cobertura. Rodar os dois portões aqui, e não depois de 20 h, é o ponto inteiro.

> Vale rodar antes o **gate 10.4 da própria change** (decisão D-e): 4 APKs × monkey × 180 s
> sobre `com.owncloud.android_48000100`, `eu.opencloud.android_9`,
> `de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700`. É o critério que a
> change define para si mesma, e é barato.

### 3. A campanha

```bash
docker compose up -d
bash scripts/monitor.sh                # ou: watch -n 300 bash scripts/monitor.sh
bash scripts/cycle.sh                  # monitor -> reparo -> resume -> admissibilidade
```

**Resume**: re-rodar o mesmo `docker compose up -d`. A identidade é
`(apk, tool, variant, repetition, timeout)`; o que já completou não é refeito, e tasks
`FAILED`/`ERROR` transientes são recuperadas.

**Contar por identidade, nunca por registro.** O resume **acrescenta** um registro em vez
de sobrescrever. E nunca `grep COMPLETED tasks.json`, que conta em dobro por causa de
`result.state_transitions[]`.

**Não dar `docker compose down` antes de consolidar.** O `app_events.csv` só materializa no
pós-processamento e os traços vivem no device, que é efêmero. Aqui isso é mais grave do que
de costume: se a imagem estiver defasada, o `errors.csv` sai com o esquema velho e **só o
logcat cru** carrega a evidência do envelope novo.

**`RV_NO_QUARANTINE` é uma armadilha.** Pelo `envvar=` do Click a variável está invertida:
defini-la **liga** a quarentena. Ela não aparece nos composes de propósito; a quarentena
fica no default ligado, como em todas as campanhas anteriores.

### 4. Consolidação, nesta ordem

```bash
uv run python scripts/consolidate.py    # tasks.json + logcats -> consolidado/*.csv
uv run python scripts/analise.py        # admissibilidade -> per_apk_admissivel.csv
uv run python scripts/gh104_gates.py \
    --results-glob 'results/gh104_*/gh104_*' --label campanha-gh104 \
    --codes-csv "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv" \
    --json consolidado/gh104_gates.json
uv run python scripts/msg_diff.py \
    --run-a ../experimento-comp162 --prefix-a comp162 \
    --run-b .                      --prefix-b gh104 \
    --label-a jca --label-b jca_android \
    --specs-a "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" \
    --specs-b "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android"
```

A ordem não é arbitrária. `consolidate.py` agrega **toda** task `COMPLETED`, que é o certo
para um consolidador e o errado para o veredito — `COMPLETED` registra que a ferramenta
retornou sem exceção, não que o run fez o que devia. `analise.py` aplica a admissibilidade
antes de somar qualquer coisa e é ele que escreve o CSV que entra na comparação pareada.
Os portões e o diff de mensagens vêm por último porque leem os dois artefatos.

**Ao ler qualquer diferença de contagem**: ela muda por várias forças simultâneas e **não
separáveis a posteriori**, e a lista mudou em 24/08 com a decisão **D-15** — o oráculo das listas
de valor deixou de ser a api30 gerada e passou a ser as 49 regras validadas por especialistas.
Empurram para **menos**: as quatro linhas de artefato de plataforma (TLS 8.648, AndroidKeyStore
2.005, X509 643, SHA256WITHRSA 4), os 17 acusadores órfãos que a gh105 calou, e a remoção do
`reset` do `MessageDigestSpec`. Empurram para **mais**: MD5/SHA-1 de volta (5.892 linhas), `SSL`
(103), `AES/ECB`, `NONEwithRSA`, a família `NOBS` inteira (30 códigos novos), o balde próprio do
`IvChainJunctionSpec`, a identidade de dedupe de 7 campos e os pointcuts `s1`/`s2` do
`SignatureSpec` revividos. A lista completa, com ponteiro, está em `CONTEXTO.md` §6.

A própria change exige que toda comparação **nomeie a qual dessas causas atribui a diferença**;
`msg_diff.py` é quem faz essa atribuição, com a dimensão de spec
(`inalterada`/`nova`/`removida`/`redefinida`) e uma quarta causa (`spec`) além de
`exploracao`/`instrumentacao`/`indeterminado`.

E dois defeitos **permanecem** e inflam a contagem na rota `dexlib2`: o **double-fire** de
`getInstance(String)` — todo `TrustManagerFactory.getInstance("PKIX")` e
`SecureRandom.getInstance("SHA1PRNG")` seguro acusa — e o **duplo report dos órfãos com
cláusula**. Ambos ficam medidos, não reparados. Não acontecem sob `ajc`.

---

## Os scripts

### Já existiam neste diretório

| Arquivo | Papel |
|---|---|
| `gh104_gates.py` | Os portões das mensagens novas, sobre `errors.csv` **e** logcat cru. Autocontido (só stdlib) de propósito: o leitor compartilhado do `aperv-tool` rejeita o corpus pré-gh104, e um verificador que não roda contra o corpus reprovado não verifica nada |
| `msg_diff.py` | Diff de violações **e mensagens** entre as duas eras, com dimensão de spec e atribuição de causa |

### Copiado byte-a-byte da `comp162` — e o diff tem de ser vazio

| Arquivo | Por quê |
|---|---|
| `admissibility.py` | **Verbatim.** Julgar os dois lados com o mesmo código é o que torna a exclusão **derivada e não escolhida**. Se a regra divergisse entre as campanhas, uma diferença de admissibilidade apareceria como diferença de spec |

```
$ diff experimento-comp162/scripts/admissibility.py experimento-gh104/scripts/admissibility.py
$ echo $?
0
```

**Verificado: o diff é vazio.** Este arquivo não deve ser editado nesta campanha por
nenhum motivo — nem para trocar o nome da campanha no docstring.

### Copiado da `comp162` e adaptado

O que mudou em cada um, e nada além disso:

| Arquivo | O que mudou |
|---|---|
| `consolidate.py` | Prefixo dos diretórios de resultado (`comp162_NN` → `gh104_NN`). Docstring: a advertência sobre as quatro forças que mexem em `mop_total`. **Colunas, agregação e identidade de dedupe inalteradas** |
| `analise.py` | `TASKS_GLOB` para `results/gh104_0*/`; referências à campanha de referência (agora a `comp162`); docstring declarando que `cov_mop` mede a régua antiga nos dois lados. Critérios, famílias H1–H4 e Holm-Bonferroni inalterados |
| `censo_substrato.py` | O `DATASET` literal virou resolução por `corpus.py`, com `--corpus` opcional — o corpus só existe depois do estágio 1. Docstring: o censo **tem de bater** com o da `comp162`, porque os `.apk.json` são os dela |
| `smoke_gates.py` | Containers `gh104smoke_NN`; `BIGGEST_BATCH_RUNS` lido de `filters/batch_*.txt` em vez de constante (a partição é podada, e uma constante desalinharia em silêncio); o rodapé aponta o segundo portão |
| `repair.py` | `BACKUP_DIR` → `backup/gh104-truncated`; tag da imagem no exemplo de uso. Lógica intacta |
| `monitor.sh` | Nomes dos containers; `EXPECTED` lido de `manifest.json` em vez de `1458` fixo, pelo mesmo motivo da poda |
| `cycle.sh` | `NAME=gh104` e o glob dos `tasks.json` |

### Novos nesta campanha

| Arquivo | Papel |
|---|---|
| `make_campaign_filters.py` | Deriva `batch_00..07.txt` herdando a partição da `comp162` e podando **no lugar**; escreve também `smoke_00.txt`/`smoke_01.txt`. Recusa-se a escrever se um sobrevivente ficar fora de todo lote, se um lote esvaziar, ou se não houver candidato a smoke com os três sinais |
| `make_manifest.py` | Gera `manifest.json` de `ApeRVTool.get_variants()`. Acrescenta ao esquema da `comp162`: `instrumentation_variant`, `monitors` (aqui **novos**, com digest por arquivo), `spec_set: jca_android`, `compared_against` apontando para a `comp162`, e tolerância a corpus/monitores ainda inexistentes. Imprime o `corpus_basis` para colar nos composes |
| `corpus.py` | O **único** lugar onde o corpus e os monitores são nomeados. Existe porque os dois caminhos só nascem nos estágios 0 e 1: repetir um caminho ainda desconhecido em quatro scripts seria quatro lugares para editar e três para esquecer — e o esquecido não falha, lê o corpus errado em silêncio |

`make_shards.py` e `preflight.py` pertencem ao **estágio 1**; ver `instrumentacao/README.md`.

## A regra de admissibilidade

Por identidade `(apk, braço, réplica)`, cegos ao braço e à direção do efeito: **C1**
`COMPLETED` com `error_message` vazio · **C2** `execution_time_seconds >= 255 s` (orçamento
menos a folga de teardown) · **C5** `cov_method > 0` e `cov_act > 0`.

**Réplica inadmissível é descartada; a célula fica com as que sobraram.** É para isso que
R=3 existe: uma falha transiente não diz nada sobre a aplicação. **A aplicação só sai
quando algum braço fica sem nenhuma réplica admissível** — a exclusão é por aplicação,
nunca por braço, porque o teste é pareado e remover um braço deixando os outros dois
desequilibra o par exatamente onde o dado é pior.

Quantas células ficaram com menos de três réplicas é **reportado**, não absorvido.

## Pendências — o que ainda é placeholder

| Onde | O quê | Quando resolve |
|---|---|---|
| `docker-compose.yml`, `docker-compose.smoke.yml` | `@corpus_basis=SUBSTITUIR_APOS_MONTAR_CORPUS` | depois do estágio 1, com o valor que `make_manifest.py` imprime |
| ambos os composes | o caminho do corpus montado (`APKS_INSTRUMENTED_jca_android_gh104_selected162`) — o diretório ainda não existe, e o sufixo `162` muda se o estágio 1 perder aplicações | fim do estágio 1 |
| `manifest.json` | `corpus.*` = `pendente-estagio-1`, `monitors.digest` = `null`, `image.id` = `null`, `predicted_identities` = `null` | rodar `make_manifest.py` de novo após cada estágio |
| `filters/batch_*.txt` | ainda não escritos — `make_campaign_filters.py` precisa do corpus para saber o que podar | fim do estágio 1 |
| `censo_substrato.csv` | idem | fim do estágio 1 |

**Não existe nesta campanha** um script de comparação pareada de **cobertura** contra a
`comp162` (o análogo do `compare_cmp163.py`). `msg_diff.py` cobre o lado das violações e
das mensagens, que é a pergunta da change; a leitura de cobertura entre campanhas, se for
necessária, ainda precisa ser escrita — e tem de consumir os dois
`consolidado/per_apk_admissivel.csv`, nunca os `per_apk_paired.csv` crus.

## Estado

Andaime do estágio 2 pronto e validado no que dá para validar sem corpus:

1. ✅ Composes escritos e validados (`docker compose config -q`, rc=0 nos dois).
2. ✅ `admissibility.py` copiado verbatim — `diff` vazio contra a `comp162`.
3. ✅ `make_campaign_filters.py` falha com mensagem clara enquanto o corpus não existir;
   a poda e a substituição de smoke foram exercitadas contra um corpus sintético.
4. ✅ `manifest.json` gerado de `get_variants()`, com as pendências marcadas.
5. ⏳ Estágios 0 e 1 (`instrumentacao/README.md`), imagem `0.9.3-gh104`, filtros, censo,
   smoke com os dois portões, campanha.
