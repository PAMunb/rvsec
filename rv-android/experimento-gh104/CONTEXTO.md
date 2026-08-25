# Contexto — campanha `gh104` (specs novas, mensagens legíveis)

Este arquivo é a memória da preparação. Ele existe para que a corrida possa ser montada sem
depender de nenhuma sessão de chat: tudo que foi levantado sobre o pipeline, os bloqueadores e
os critérios de aceitação está aqui, com caminho e linha.

**Estado em 2026-08-24 (HEAD `6192b57a`): preparação. Nada foi executado — mas o mundo que este
plano descrevia mudou.** A change `gh104` está com **106 de 109** tarefas marcadas; as três abertas
são 10.4, 10.5 e 10.8, e as três dependem desta campanha ou do arquivamento que a segue. A `gh105`
está **72/74** (8.8 e 8.9 bloqueadas pelo arquivamento da `gh104`), a `gh106` **15/16**, a `gh100`
**57/57**. O conjunto sucessor `jca_android` **existe em disco, com 24 `.mop` e zero
`ExecutionContext`**.

> **O que mudou e por quê, com comando ao lado:** `docs/20260824_reconciliacao.md`.
>
> **Regra de carimbo.** Todo escalar deste arquivo foi medido em **2026-08-24**, no HEAD `6192b57a`
> do `rv-android` e no branch `modules` do reator, salvo onde outra data está escrita ao lado. Um
> número publicado sem data, sem commit e sem regra de contagem não é verificável — é a lição que a
> `gh106` transformou em código executável (`SubstrateTrajectory.COUNTING_RULE`, `StampedTable`), e
> ela vale aqui.

---

## 1. O que esta campanha é

Rodar de novo os dois estágios do Estudo 03 — **instrumentar com `dexlib2`** e depois **executar
a campanha** — mas com o conjunto de especificações **novo** que a change
`openspec/changes/gh104-legible-violation-reports/` produz, e então **verificar as mensagens de
violação e os erros novos** contra o que a change prometeu.

O fator em estudo é **o conjunto de specs**. Tudo o mais (variante de instrumentação, corpus,
imagem, orçamento de tempo, réplicas) deve ficar igual à campanha de referência, ou a diferença
deixa de ser atribuível.

**Campanha de referência (o lado "antes"):** `experimento-comp162/` — `dexlib2`, specs `jca`,
162 APKs, 3 braços, R=3, T=300 s, 8 containers, 1458 identidades.
Corpus: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`
(`corpus_basis = selected162:3bbc5fa91ba2cf3cd59e040237501caa0718735647d2c6881e09581f1e972c85`).

> `experimento-comp162-ajc/` é a campanha irmã tecida com AspectJ. **Não é a nossa base** — serve
> só como referência de método (os scripts `mop_diff.py`, `funil.py`, `covadjust.py` nasceram lá).

---

## 2. Os três estágios

A campanha de referência reusou monitores pré-gerados. **Aqui isso não é possível**: as specs
mudam, então os monitores têm de ser gerados de novo. Isso adiciona um estágio 0.

```
Estágio 0  gerar monitores das specs novas   →  monitors_master/  (UMA vez, sequencial)
Estágio 1  instrumentar os APKs (dexlib2)    →  corpus instrumentado + .apk.json co-locados
Estágio 2  executar a campanha               →  logcats + errors.csv
Estágio 3  consolidar, verificar, comparar   →  portões gh104 + diff contra a comp162
```

### Estágio 0 — geração de monitores (o passo novo)

**Geração de monitores NÃO é paralelizável.** O JavaMOP estagia os `.rvm` no diretório de specs
**compartilhado** e o gerador os **move** de lá
(`modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:218-222`).
N gerações concorrentes se roubam, o `ErrorHandler` engole a falha, e o lote sai **tecido sem
monitores, reportando sucesso**. Isso já custou uma campanha inteira
(`experimento-comp162-ajc/instrumentacao/README.md:30-36`).

Consequência de projeto: gerar **uma vez**, congelar num diretório com digest, e entrar nos
shards do estágio 1 por bind-mount `:ro` com `RV_SKIP_MONITORS=true`. O `pre_processor` procura
os monitores em `<output_dir>/monitors` (`modules/rv-experiment/src/rv_experiment/config.py:780-782`).

O `dexlib2` consome o **descritor `MultiSpec_1MonitorAspect.json`** e o
`MultiSpec_1RuntimeMonitor.java`; o `ajc` consome o `.aj` e o `.java`. O mesmo diretório serve
os dois (foi assim que `comp162` e `comp162-ajc` teceram de monitores byte-idênticos).

**Teto do gerador (gh104 D-1):** `CipherSpec` fica em 17 eventos, que é o limite —
17 eventos custam ~53 s e 3,3 GB; **18 estouram `StackOverflowError` em `EnableSet.parseSets`**.
Nenhum evento pode ser acrescentado sem remover outro. `TMPDIR` fora de tmpfs; `RVSEC_HOME`
obrigatório.

### Estágio 1 — instrumentação `dexlib2`, **no host**

Runbook completo em `instrumentacao/README.md`.

**A rota `dexlib2` roda no host, sem Docker.** É a decisão **D6** de
`docs/20260810_plano_prontidao_estudo03.md:58`, e ela **valeu** na produção do corpus da
`comp162`: 8 processos `rv-experiment` concorrentes, 3 h 53 min para 163 APKs, `rc=0`
(`docs/20260812_registro_execucao_prontidao_e3.md:228`). O paralelismo é **sharding de processo**,
não containers — D6 foi questionada e mantida.

> A rota `ajc` da campanha irmã precisou de Docker porque `ajc`/`d8`/`zipalign`/`apksigner` não
> existem no `PATH` do host. O `dexlib2` precisa só de `java` e `mvn`: os demais binários são
> resolvidos **dentro** do `instr-cli.jar` a partir de `ANDROID_HOME`/`JAVA_HOME`.

Isso tem uma consequência que decide o plano inteiro:

> **Os jars locais só entram no APK se a instrumentação rodar no host.** Em Docker a imagem clona
> do GitHub e reconstrói (`docker/rvandroid/Dockerfile:14-18`), então o que vale é o repositório
> Maven **local**. (`docs/20260811_handoff_execucao_prontidao_e3.md`, aprendizado 11.)

Pontos firmes:

- Variante `dexlib2` **tem de ser forçada** — o default do CLI é `ajc`
  (`modules/rv-instrumentation/src/rv_instrumentation/config.py:199-201`).
- O weaver é um CLI Java: `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`. O diretório
  `lib/` é **gitignored** — o jar só existe depois de um build do reator, que o copia por
  `maven-resources-plugin` (design D9). Rebuild isolado:
  `mvn -pl rvsec-android/rvsec-instrumentation-dexlib2/cli -am package`.
- O `--classpath` vem de `_resolve_runtime_libs`
  (`modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py:53-130`), que roda
  **`mvn dependency:copy-dependencies` sobre `rv-android/pom.xml`** e popula `<output_dir>/lib_tmp/`.
  Uma allowlist reduz a 3 jars: `rv-monitor-rt.jar`, `rvsec-core.jar`, `rvsec-logger-logcat.jar`
  (`aspectjrt`/`kotlin-stdlib` ficam de fora para evitar `Type defined multiple times` no d8).
- **Os jars vêm do repositório Maven local**: `/home/pedro/desenvolvimento/repository`
  (definido em `~/.m2/settings.xml` — **não** é `~/.m2/repository`). Último `install` completo:
  2026-08-11 10:14.
- **Cada shard precisa do seu próprio `--output-dir`.** `--work-dir == --output-dir`
  (`modules/rv-experiment/src/rv_experiment/config.py:856`), e o `BatchRunner.java` resolve
  `workDir.resolve("woven_" + entryName)` e `workDir.resolve("monitor-build")` — nomes planos e
  compartilhados. Duas JVMs no mesmo work dir sobrescrevem o `woven_classes.dex` uma da outra
  **sem erro**.
- Só o `dexlib2` escreve `instrument_results.json`, com `results[].weaveCounts` — **20 campos**,
  não 19: `advicesExcludedByArity` entrou em 2026-08-19 pelo commit `b43f500e` da própria gh104
  (INV-INS-122; `WrapperEmitter.java:91`, `BatchRunner.java:210`, e o lado Python em
  `dexlib_instrumentation.py:591-628`). O contador **mede e não filtra**: nenhum advice deixa de
  disparar por causa dele.
- `wrappersGenerated` vale **84** para as 23 specs do `jca`, e esse já é o valor **pós-`gh100`** —
  a fusão de wrappers levou 96 → 84 fundindo os 12 que antes eram descartados em silêncio, sem
  mexer em `wrappersSubstituted` (74 → 74). Para as **24** specs do `jca_android` o número será
  outro; o portão do P3 não pede um valor, pede que seja **o mesmo em todos os APKs**.
- **Não confie no exit code do `instr-cli`**: ele sai 0 mesmo com `success=false`. Quem detecta é a
  checagem de existência do APK no wrapper Python
  (`modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:273-284`).
- Métrica de superfície tecida é **`wrappersSubstituted`**, não `matchesApplied` — um APK pode ter
  `matchesApplied = 0` e estar corretamente instrumentado.

### Estágio 2 — execução

Molde da `comp162` (`experimento-comp162/docker-compose.yml`): 8 containers, `/dev/kvm`,
4 cpus + 10 g cada, `RV_DELAY` escalonado, e os **três skips ligados**
(`RV_SKIP_MONITORS`, `RV_SKIP_INSTRUMENT`, `RV_SKIP_STATIC_ANALYSIS` = `true`), porque o corpus
já entra instrumentado e com o `.apk.json` co-locado — que é como o `pre_processor` acha a
análise estática (`modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:459`,
INV-EXP-16).

`RV_LOGCAT_DIAGNOSTICS=true` (gh72) para materializar `app_events.csv` — foi o que permitiu, na
`comp162-ajc`, medir o confundidor de crashes. Vale manter.

**Nunca dar `docker compose down` antes de consolidar**: `app_events.csv` só materializa no
pós-processamento (`modules/rv-platform/src/rv_platform/components/result_processor.py:167`) e os
traces vivem no device, efêmeros.

**Resume:** re-rodar `docker compose up -d`. Identidade `COMPLETED` é pulada; `ERROR`/`FAILED` é
re-executada do zero. O resume **acrescenta** registro em vez de sobrescrever — toda contagem é
por identidade `(apk_name, tool.name, tool.variant, repetition, timeout)`, **nunca** por registro
nem por `grep COMPLETED tasks.json` (que conta em dobro por `result.state_transitions[]`).

---

## 3. Bloqueadores — o que precisa ser verdade antes de subir qualquer coisa

Seis dos oito caíram entre 18/08 e 24/08. A tabela abaixo é o estado **medido em 2026-08-24**;
reverifique antes de lançar, porque quatro deles são propriedades de mtime e de árvore de trabalho,
não de commit.

| # | Bloqueador | Como verificar | Estado em 2026-08-24 |
|---|---|---|---|
| B1 | A change gh104 implementada: conjunto sucessor em `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/` | `uv run python experimento-gh104/scripts/preflight.py --spec-set jca_android ...` imprime contagem e digest | **FECHADO** — **24** `.mop` + `codes.csv`, **zero** `ExecutionContext`. A cardinalidade não é 21: ver §3.1 |
| B2 | Reator Java reconstruído e **instalado** no repositório local, para que `rvsec-core` (ErrorDescription/ErrorCollector) e `rv-monitor` (macro `__EVENTNAME`) novos entrem no APK, e para recopiar o `instr-cli.jar` | `mvn clean install -DskipTests -DskipMopAgent` na raiz `rvsec`; conferir mtime do jar em `/home/pedro/desenvolvimento/repository/br/unb/cic/rvsec-core/0.9.3-SNAPSHOT/` | **FECHADO em 24/08 20:26** — o jar é posterior ao `.mop` mais novo (`IvChainJunction.mop`, 24/08 11:51). **Refazer se qualquer `.mop` mudar depois disso**: é a única verificação que envelhece sozinha |
| B3 | Imagem Docker com o código novo — **só afeta o estágio 2** | ver §4 | **ABERTO** — `phtcosta/rvandroid:0.9.3-gh104` não existe, e o branch `modules` está **124 commits** à frente de `origin/modules` |
| B4 | `mop_dir` da análise estática deixa de apontar para `jca` fixo | `get_static_analysis_config()` passa `mop_dir=self.resolve_spec_set_dir(rvsec_root)` (`modules/rv-experiment/src/rv_experiment/config.py:982`) | **RESOLVIDO** pelo commit `86a8f178` (tarefa 10.8 → 10.0). Isso **muda o estatuto da decisão D-c**: ver abaixo |
| B5 | Leitores de `errors.csv` atualizados para 13 colunas | `modules/aperv-tool/src/aperv_tool/analysis/violations.py:64-78` | **RESOLVIDO** — o header de 13 colunas está declarado, e `read_errors_csv:437` levanta fora dele |
| B6 | Um leitor congelado de 11 colunas para a baseline (D-9 da gh104) | a `comp162` deixa de ser legível pelo `aperv-tool` depois da mudança de header | **RESOLVIDO** — `scripts/gh104_baseline.py:371` (`_read_frozen(path, COMP162_HEADER, ...)`), privado ao arquivo por decisão D-9 |
| B7 | JDK para o build do reator | a `PROVENIENCIA.md` do E3 registra **Temurin 25.0.3+9**, que é o `java` atual do host — o reator buildou com 25, apesar do `java.version=21` do pom | OK — reconfirmado: o fechamento da `gh106` buildou 48 módulos e 2.034 testes sob JDK 25 |
| B8 | `instr-cli.jar` presente em `modules/rv-instrumentation-dexlib2/lib/` (gitignored) | `ls -l modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` | **FECHADO** — 24/08 20:28, recopiado pelo build do B2 |

### 3.1 — por que o conjunto tem 24 `.mop` e não 21

O número 21 deste plano vinha de uma decisão da própria gh104 que **foi retirada**. A revisão que
o plano leu em 18/08 deletava `RandomStringPassword.mop` e `SecretKeySpec.mop` — os dois
propagadores puros de predicado — o que daria 23 − 2 = 21. A **D-11** retirou a deleção
(`openspec/changes/gh104-legible-violation-reports/proposal.md:58`, `design.md:137`): o conjunto é a
semente inteira, **23 arquivos, os dois propagadores incluídos**.

Depois disso a **gh105** acrescentou **um** arquivo: `IvChainJunction.mop` (commit `889da829`,
tarefa 5.1). Ele existe porque a cláusula do IV liga o terceiro argumento de `Cipher.init`, que o
`CipherSpec.i2` não liga — e o `CipherSpec` está em **17 de 17 eventos**, o teto do gerador, com
headroom zero (INV-INS-145): nenhum evento novo cabe ali, então a ligação teve de sair para um
arquivo de junção, que deliberadamente **não declara `ORDER`** e portanto nunca falha por ordem.

`23 + 1 = 24`. A soma está normatizada em
`openspec/changes/gh105-predicate-wiring/specs/instrumentation/spec.md:422`.

**Consequência para quem lê tabela de cobertura**: a régua reusada (decisão D-c) mede o alcance das
**23** specs do `jca`; o outro lado da comparação tem **24**, não 21. A assimetria continua de 1
arquivo — mas na direção oposta à que este plano supunha.

### B4 — resolvido, e o que isso muda na decisão D-c

O defeito foi corrigido: `get_static_analysis_config()` passa
`mop_dir=self.resolve_spec_set_dir(rvsec_root)` (`modules/rv-experiment/src/rv_experiment/config.py:982`),
e o mapeamento conjunto→diretório passou a viver num método só, consumido pela geração de monitores
e pela análise estática (commit `86a8f178`). Uma campanha `jca_android` que rodasse a análise
estática hoje a rodaria **contra o conjunto certo**.

**Isso não muda a decisão D-c, mas muda a razão dela.** Enquanto o defeito existia, reusar os
`.apk.json` da `comp162` era a única rota que não produzia um denominador incoerente. Hoje é uma
**escolha de método**: reusar preserva o denominador e, com ele, a atribuibilidade da diferença
pareada. Escrevendo com honestidade — o texto antigo dizia que o defeito nos obrigava, e não diz
mais:

> Reusamos os `.apk.json` porque o pareamento exige denominador idêntico, **não** porque falte
> alternativa. O preço é escolhido: `cov_mop` desta campanha mede o alcance das **23 specs do
> `jca`** nos dois lados. Ele **não é** "cobertura das specs novas" — é a mesma régua da `comp162`,
> aplicada de propósito aos dois lados.

**A alternativa agora existe e fica registrada, não tomada**: rodar a análise estática com
`--specification-set jca_android` daria a cobertura das 24 specs novas, ao custo de dois
denominadores diferentes e de uma diferença pareada que deixaria de ser atribuível ao conjunto de
specs. Se alguém quiser esse número depois, ele é uma **terceira medição**, não um substituto —
e custa uma passagem inteira de GATOR sobre os 162.

### B3 — o que a imagem velha estragaria, e o que não

A mensagem de violação nasce **dentro do APK** (o `rvsec-core` e os monitores tecidos no estágio 1,
no host). Ela chega ao logcat com o envelope novo **mesmo se o container for velho**. O que a
imagem velha estragaria é o lado Python do estágio 2: o `errors.csv` sairia com 11 colunas, o
`unique_msg` com 5 partes, e os `ParserDiagnostics` não existiriam.

Ou seja: **B3 degrada a saída derivada, não a evidência bruta.** Se o rebuild da imagem atrasar,
os `.logcat` ainda servem — o `gh104_gates.py` lê as duas populações (CSV e logcat) exatamente
por isso.

---

## 4. A imagem Docker — necessária só no estágio 2

`docker/rvandroid/Dockerfile:14-18` faz:

```dockerfile
RUN git clone --branch ${RVSEC_BRANCH} https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && uv sync --no-dev
```

Ou seja: **a imagem clona do GitHub, não copia a árvore local.**

**Decidido: push em `origin/modules` + rebuild.** Medido em 24/08: o branch local `modules` está
**124 commits à frente de `origin/modules`** (eram 4 em 18/08) — a gh104, a gh105 e a gh106 inteiras
estão nesse intervalo. O remoto é `git@github.com:PAMunb/rvsec.git`.

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
git push origin modules
bash rv-android/docker/rvandroid/build.sh      # --no-cache; ver nota sobre a tag
```

**Taguear como `phtcosta/rvandroid:0.9.3-gh104`.** O `build.sh` como está aplica as tags `0.9.3`
**e** `latest`; editar a tag antes de rodar, ou taguear manualmente depois.

> **Correção de 24/08.** Este parágrafo dizia que sobrescrever `0.9.3` apagaria a imagem que
> reproduz a `comp162`. **Não apagaria**: a referência já tem tag própria. O compose da campanha de
> referência fixa `phtcosta/rvandroid:0.9.3-comp162` (`experimento-comp162/docker-compose.yml:58`),
> e o `manifest.json` dela pina o id `sha256:811d3ef3ad5b…`. Medido: `0.9.3` e `latest` apontam para
> `9cca8e617c7c`, uma imagem **diferente** da `811d3ef3ad5b`. A razão para não sobrescrever `0.9.3`
> continua válida — é a tag genérica de que outras coisas dependem — mas a justificativa que estava
> escrita era falsa, e uma justificativa falsa não sustenta a decisão quando alguém a questionar.

Rotas descartadas, e por quê:

- **Bind-mount por cima da imagem existente** (o que a `comp162-ajc` fez com o `ape-rv.jar`):
  serve para trocar poucos arquivos, não o reator Java inteiro — os jars já foram instalados no
  `~/.m2` da imagem durante o build.
- **`docker/rvandroid_dev/Dockerfile`**, que COPIA a árvore local: só traz o lado Python e herda o
  `/opt/rvsec` Java do `rvandroid_tools:0.9.3`. Não resolve `rvsec-core` nem o gerador.

Como a gh104 mexe em **Java** (`rvsec-core`, `rv-monitor`), em **Python** (parser, transporte,
`result_processor`) e nas **specs** (`.mop`), só o rebuild completo cobre os três.

---

## 5. Corpora disponíveis

Base: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`
(área de entrega; a fonte de verdade é o repo `rvsec-dataset` — ver o `CLAUDE.md` de lá).

| diretório | conteúdo |
|---|---|
| `APKS/` | **348 APKs originais**, não instrumentados — a entrada do estágio 1 |
| `APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/` | o corpus da `comp162` (162, `dexlib2`, specs `jca`) |
| `E3_jca_dexlib2_163/monitors_master/monitors/` | os monitores congelados do `jca`, digest `8c66bb247f14d3cfd6ca01afa636d78254f39d7a5bf0f516b89980097aa4f16d` |
| `APKS_INSTRUMENTED_jca_ajc_comp162ajc_selected41/` | o corpus da campanha `ajc` (41) — não é o nosso |

Os quatro APKs que a gh104 nomeia para o gate de dispositivo (tarefa 10.4) existem em `APKS/`:
`com.owncloud.android_48000100`, `eu.opencloud.android_9`, `de.luhmer.owncloudnewsreader_196`,
`com.etesync.syncadapter_20700`.

---

## 6. O que muda na saída — o que os portões têm de olhar

Resumo operacional; o detalhe com citação está em `docs/gh104_mudancas_observaveis.md`.

### Mensagem

Antes (real, `experimento-comp162/results/comp162_00/comp162_00/errors.csv`):

```
app.eduroam.geteduroam_2685.apk,1,300,ape,6,TrustManagerFactorySpec,okhttp3.internal.platform.Platform,platformTrustManager,Platform.kt:78,unknown,okhttp3...:::platformTrustManager:::TrustManagerFactorySpec:::InvalidSequenceOfMethodCalls:::unknown
```

Depois — envelope v1, gramática fixa:

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observado>' exp='<esperado>' msg='<texto>'
```

`KIND ∈ {ORDER, ALG, CONSTR, KEYSIZE, KSTYPE, PROTO, FORB, **NOBS**}`. Sem `st=`. Vírgulas
permitidas dentro de valores (27,06 % das mensagens hoje têm vírgula). `\n` e `:::` proibidos. `'`
escapado como `\'`. `val` limitado a 512 caracteres. Aspa final não fechada = registro truncado.

> **`NOBS` é o oitavo KIND, e ele não estava neste plano.** A gh105 introduziu a família *not
> observed* — uma leitura de predicado três-valorada cujo veredito `NOT_OBSERVED` tem de chegar ao
> envelope com **código de família própria, distinto do de violação** (INV-INS-143), para que
> ninguém a jusante confunda "violou" com "não observei". Medido no `codes.csv` vivo de 24/08:
> **30 dos 114 códigos são `NOBS`**, distribuídos por 14 especificações (`IvChainJunctionSpec` 6,
> `KeyGeneratorSpec` 3, `SignatureSpec` 3, sete specs com 2, quatro com 1).
>
> **Isso quebra o nosso portão G5 como ele está escrito** — ver §7.

### Esquema

- `errors.csv`: **11 → 13 colunas**, `code` e `event` inseridos **depois de `source`**:
  `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`.
  Leitores posicionais quebram.
- `unique_msg`: **5 → 7 partes** — `class:::method:::spec:::error_type:::code:::event:::message`.
- Campos fabricados viram sentinela explícito: `Unknown Source:1` → `UNSPECIFIED:0`;
  `No additional message` → `""`; `error_type` vazio → `UNSPECIFIED`; sem envelope →
  `code`/`event` = `UNSPECIFIED` (nunca string vazia).
- A **forma da linha de logcat não muda**: continuam 7 campos separados por vírgula; só o
  conteúdo do 7º muda.

### Baselines a bater (tarefa E10 da gh104)

| grandeza | `comp162` (antes) | alvo |
|---|---|---|
| `message == 'unknown'` | 15.714 de 19.664 = **79,91 %** | **0** |
| mensagens `but found .` | **98** | **0** |
| colunas do `errors.csv` | 11 | **13** |
| identidades de 5 campos | 6.344 para 19.664 linhas | identidade passa a 7 campos → **mais** linhas |

(No dataset publicado do artigo, 97.018 linhas: `unknown` = 70.760 = **72,93 %**;
`but found .` = 8.843.)

### Contagem — as forças mudaram de conta, e de sinal

**Este bloco foi reescrito em 24/08.** A versão de 18/08 listava quatro forças e atribuía o lado
"menos" às allow-lists **transcritas da api30**. A **D-15** retirou essa âncora
(`openspec/changes/gh104-legible-violation-reports/design.md:346`, decisão do pesquisador em
2026-08-24): as listas de valor passaram a ser transcrição literal dos `CONSTRAINTS` das **49
regras validadas por especialistas** do `RVSec-replication-package/tools/rules/`, pinadas por
sha256. As regras api30 continuam sendo o oráculo de **`ORDER`, alfabetos de evento e predicados** —
e só disso.

A contagem muda por causas simultâneas e **não separáveis a posteriori**:

**menos**
- as quatro linhas de artefato de plataforma que a D-15 mantém silenciosas, agora por listas
  expert + a camada `platform-value` de cinco entradas da tarefa 11.4: TLS **8.648** eventos,
  AndroidKeyStore **2.005**, X509 **643**, SHA256WITHRSA **4**;
- **17 acusadores órfãos** em 9 specs deixam de emitir o `InvalidSequenceOfMethodCalls` espúrio
  (gh105, grupo 3) — e num caso medido o órfão estava *suprimindo* o achado real, não só somando;
- a remoção do `reset` de `MessageDigestSpec`.

**mais**
- **MD5 e SHA-1 voltam a ser acusados** — **5.892 linhas** do corpus publicado. A api30 os admitia
  (é catálogo de disponibilidade do provider, não juízo de segurança); a regra expert não. O mesmo
  vale para `SSL` (**103** eventos), `NONEwithRSA` (**4**), `HmacMD5`, `HmacSHA1`, `ARC4`,
  `DESede`, `BLOWFISH`;
- **`AES/ECB` volta a ser acusado** (tarefa 11.3, commit `5bc5c893`): o `CipherSpec` volta a
  chamar a `CipherTransformationUtil` congelada. A `Api30CipherTransformationUtil` **admitia**
  `AES/ECB/PKCS5Padding` — falso negativo que a D-10 nunca nomeou;
- a família **`NOBS`** inteira: 30 códigos que **não existiam em nenhum conjunto anterior**;
- `IvChainJunctionSpec` abre **balde novo de *unique misuse*** no mesmo `(classe, método)`, por
  construção — a gh105 exige que esta campanha conte relatório de junção como acusador próprio,
  **nunca dobrado no balde do typestate**
  (`openspec/changes/gh105-predicate-wiring/design.md:415-425`);
- a identidade de dedupe de 7 campos;
- os pointcuts `s1`/`s2` do `SignatureSpec` revividos.

**medido no arnês diferencial** (tarefa 11.9, sobre 159 traces): `unchanged 119 · moved 22 ·
removed 12 · introduced 6`. Não é a campanha, é o replay — mas é o único número que já separa as
causas, porque cada delta tem atribuição nominal em
`data/jca_android/evidence/d15_harness_attribution.md`.

Qualquer comparação de contagem **tem de nomear a qual dessas causas atribui a diferença** —
exigência da própria change.

### Defeitos que **permanecem** e inflam a contagem no `dexlib2`

Relevante porque nossa rota é `dexlib2`:

- **double-fire**: `getInstance(String)` dispara `g1`+`g2`(+`g3`/`g4`), então **todo
  `TrustManagerFactory.getInstance("PKIX")` e `SecureRandom.getInstance("SHA1PRNG")` seguro
  acusa**. Na `comp162`: TMF 2.855 de sequência contra 61 de `UnsafeAlgorithm`; SecureRandom
  2.882 contra 0. **Isso não acontece sob `ajc`** — é ruído específico da nossa rota.
- **duplo report dos órfãos com cláusula**: cada disparo emite o report do corpo **e** um
  `InvalidSequenceOfMethodCalls` do `@fail`.

Ambos ficam **medidos, não reparados** pela gh104.

---

## 7. Ferramental

### O que já existe e serve

- `experimento-comp162/scripts/admissibility.py` — C1/C2/C5, piso `timeout − 45 s`. Copiar
  **verbatim**: julgar os dois lados com o mesmo código é a garantia de que a exclusão é derivada,
  não escolhida.
- `experimento-comp162/scripts/consolidate.py`, `analise.py`, `censo_substrato.py`,
  `smoke_gates.py`, `repair.py`, `monitor.sh`, `cycle.sh` — o ciclo de operação.
- `experimento-comp162-ajc/scripts/mop_diff.py` — a base do diff de violações (identidade,
  leitura de logcat, atribuição de causa por cobertura). Joga a mensagem fora de propósito.
- `.claude/skills/rv-experiment-compare/` — `gen_compare.py`, `monitor_compare.sh`,
  `consolidate_compare.py`, `templates/plan.md.tmpl`. Útil para campanhas no layout
  `data/results/<name>_NN/`; a nossa segue o layout manual `experimento-<x>/results/`.

### O que não existe e foi escrito para esta campanha

- `scripts/gh104_gates.py` — os portões das mensagens novas (`unknown` = 0, `but found .` = 0,
  13 colunas, `unique_msg` de 7 partes, envelope v1 bem-formado, `__EVENTNAME` não vazado,
  `advicesExcludedByArity`/`wrappersGenerated` presentes).
- `scripts/msg_diff.py` — diff de violações **e mensagens** entre a era antiga e a nova, com
  dimensão de spec (`inalterada`/`nova`/`removida`/`redefinida`) e uma quarta causa (`spec`) além
  de `exploracao`/`instrumentacao`/`indeterminado`.

Nenhum diff existente é sensível a mudança de spec, e nenhum compara o texto da mensagem — era
exatamente o buraco desta campanha. Isso continua verdadeiro: verificado em 24/08, **nada da
`gh106` substitui nem duplica esses dois**. A `gh106` é o instrumento **estrutural** (`.mop` ×
`.crysl`, métricas M0–M4); estes dois são o instrumento **comportamental** (logcat e `errors.csv`
de campanha gravada). A `gh106` diz isso de si mesma, e nunca menciona `experimento-gh104/`.

### Três defeitos deste ferramental, achados em 24/08 — F1 e F2 corrigidos em 25/08

**F1 — o portão G5 reprovaria uma campanha correta. CORRIGIDO.**
O script congelava `ENVELOPE_KINDS = {ORDER, ALG, CONSTR, KEYSIZE, KSTYPE, PROTO, FORB}` e o
`codes.csv` vivo tem **30 códigos `NOBS`** de 114: toda mensagem `*-NOBS-NN` seria contada como
`envelope_malformed`. O reparo foi o **melhor** dos dois propostos, e não o mínimo: o vocabulário
vem agora do `codes.csv` do conjunto sob medição, por `--codes-csv`
(`load_code_vocabulary`/`CodeVocabulary`), e a lista congelada — já com `NOBS` — sobrou como rede
de segurança de quem roda sem o arquivo, tipicamente contra um corpus pré-gh104, que não tem
envelope nenhum. Com o catálogo o portão passou a responder **duas** perguntas onde antes só havia
uma: o KIND é admitido (bem-formado) **e** o código existe. Um envelope perfeito cujo código não
está no `codes.csv` reprova como deriva de proveniência — o APK carrega monitores de outro
conjunto, e toda leitura a jusante estaria atribuindo a acusação à spec errada. Sem `--codes-csv` a
segunda pergunta é declarada não-respondida na linha do portão, nunca passada por omissão.

Verificado em 25/08: o baseline `comp162` reproduz os números congelados sob o script novo —
19.664 linhas, 15.714 mudas (79,91 %), 98 `but found .` —, e um corpus sintético com
`SIGNATURE-NOBS-00`, um KIND inexistente e um código bem-formado fora do catálogo separa os três
casos como esperado.

**F2 — o `msg_diff.py` tinha o mesmo ponto cego que custou treze traces à tarefa 11.9. CORRIGIDO.**
A identidade era `(apk, spec, classe, método, tipo_erro)` e **não continha `code`**; as mensagens
iam para um `Counter` ao lado e `_representative` devolvia a mais frequente, então duas acusações
colapsadas na mesma identidade viravam duas entradas do contador e a minoritária **desaparecia da
comparação**. O colapso é real: `SIGNATURE-CONSTR-00` e `SIGNATURE-NOBS-00` são o mesmo evento
`i1`, o mesmo `ErrorType` `UnsatisfiedConstraint`, códigos diferentes.

**A correção mínima registrada aqui em 24/08 estava errada, e é por isso que o reparo é outro.**
Ela mandava acrescentar o `code` à tupla de identidade com o sentinela `UNSPECIFIED` para a era
antiga, "senão todo o lado A vira `so_A`" — mas o sentinela não evita isso: com o código dentro da
chave, o lado A fica com tuplas `(…, UNSPECIFIED)` e o lado B com `(…, SIGNATURE-CONSTR-00)`, que
nunca casam. O resultado seria **100 % `so_A` + 100 % `so_B` e nenhuma linha `ambos`**: a
comparação inteira destruída em silêncio, que é pior que o defeito original.

O que foi feito: **junta-se por sítio, compara-se por código.** A leitura passou a ser
`viol[apk][sítio][code]` e cada linha do CSV é um par `(sítio, código)`. Quando um lado não tem
envelope, o seu único registro responde por **cada** código do outro lado — o par continua `ambos`,
e o `code` da linha é o do lado que o tem. Quando os dois lados têm códigos (comparação entre duas
campanhas pós-gh104), o código entra na comparação de verdade e uma acusação presente de um lado só
sai como `so_A`/`so_B` **dentro de um sítio que os dois enxergam**, com causa atribuída por spec ou
substrato — a cobertura não discrimina nada aí, porque o método foi executado dos dois lados.
Colunas novas: `code`, `codigos_no_sitio_a`, `codigos_no_sitio_b`; e um resumo "acusações por
sítio" que conta os sítios multi-acusação, que é exatamente o que sumia.

**F3 — colisão de nome com armadilha de `sys.path`.**
Existem dois `gh104_gates.py`: o desta campanha (portões de **mensagem** sobre campanha gravada) e
`scripts/gh104_gates.py` da raiz (nove portões **estruturais** sobre monitor gerado e `.mop`).
Propósitos disjuntos, zero funções em comum — mas `scripts/gh104_mop_lint.py:47` e
`scripts/gh104_message_gate.py:76` fazem `sys.path.insert(0, ...)` seguido de
`from gh104_gates import MopSpec, parse_mop, ...`. Com o nosso diretório antes no `sys.path`, o
import estoura com `ImportError`. **Proposta, a decidir pelo pesquisador**: renomear o nosso para
`campaign_message_gates.py`. O nome aparece em `PRONTIDAO.md`, `README.md` e neste arquivo.

---

## 8. Armadilhas registradas

1. **Não subir o estágio 1 enquanto outra campanha roda.** 32 cpus disputariam com emuladores que
   medem cobertura sob orçamento de tempo.
2. **Contar por identidade, nunca por registro.** O resume acrescenta.
3. **Não dar `down` antes de consolidar.**
4. **`RV_NO_QUARANTINE` é uma armadilha**: via `envvar=` do Click ela **liga** a quarentena,
   invertida (`modules/rv-experiment/src/rv_experiment/__main__.py:510-511`). A quarentena fica no
   default ligada, como em todas as campanhas anteriores.
5. **Monkey e APE são estocásticos.** O gate 10.5 da gh104 manda ler *forma*, não contagem: sítio
   não alcançado não é evidência de reparo.
6. **`lib_tmp/` é propenso a jar velho.** `mvn dependency:copy-dependencies` não sobrescreve
   snapshot por default; apagar `lib_tmp/` antes de reinstrumentar com jars novos.
7. **A geração de monitores não é paralelizável** (§2, estágio 0).

---

## 9. Decisões fechadas (2026-08-18)

| # | Decisão | Consequência |
|---|---|---|
| D-a | **Corpus: os mesmos 162 da `comp162`** (`selected162.txt`), instrumentados de novo com as specs novas | o pareamento com a referência fica completo; o único fator que varia é o conjunto de specs |
| D-b | **Braços: os 3 da `comp162`** — `ape`, `aperv:mop_off_llm_off`, `aperv:mop_on_llm_off`, R=3, T=300 s, 8 containers = **1458 identidades** (~20 h) | grade idêntica; o `wilcoxon.csv` das duas campanhas fica comparável contraste a contraste |
| D-c | **Reusar os `.apk.json` da `comp162`** | denominador idêntico; `cov_mop` medido contra as 23 specs antigas nos dois lados (declarar). **Desde 24/08 é escolha de método, não necessidade técnica** — o defeito B4 foi corrigido; ver §3 |
| D-d | **Push em `origin/modules` + rebuild** como `phtcosta/rvandroid:0.9.3-gh104` | §4; 124 commits a empurrar. Não sobrescrever `0.9.3` — mas **não** pela razão que este arquivo dava até 24/08: a `comp162` roda em `0.9.3-comp162` |
| D-e | **Rodar o gate 10.4 da gh104 como piloto antes da campanha** | 4 APKs × monkey × 180 s; é o critério que a própria change define, e é barato. **Continua válido e ficou mais forte**: a 10.4 é literalmente uma das três tarefas abertas da change, e a 10.5 declara "Runs only after Group 11" — o Grupo 11 fechou em 24/08 |

### O que a decisão D-a implica

O estágio 1 reinstrumenta **exatamente os 162 nomes** de
`APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/selected162.txt`, a partir dos
originais em `APKS/`. O `corpus_basis` do novo corpus **tem de ter nome próprio** (ex.
`selected162gh104:<sha256>`), mesmo que a lista de nomes seja idêntica — foi assim que a
`comp162-ajc` evitou que duas campanhas com corpora diferentes se passassem uma pela outra.

Vale registrar o que já se sabe do lado dexlib2: dos 163 originais, **1 falhou** de forma
determinística (`info.dvkr.screenstream_44000.apk`, `classes28.dex` com 65.521 dos 65.536
`method_ids` — os 84 wrappers não cabem). Se o conjunto novo tiver contagem de wrappers diferente,
essa fronteira se move: **checar `method_ids` (offset 88 do header DEX) antes de instrumentar** é a
verificação barata que o registro do E3 recomenda.

---

## 10. Esta campanha é o experimento **conjunto** — o que ela fecha

Registrado em 24/08, porque nenhum artefato do plano dizia isto e é o que justifica o custo.

**Ela é a única coisa que fecha três tarefas de duas changes:**

| tarefa | change | o que ela pede | onde |
|---|---|---|---|
| 10.4 | gh104 | `uv run rv-experiment run --tools monkey --specification-set jca_android --timeouts 180` sobre os 4 APKs; registrar `unknown` = 0, `but found .` = 0, campos do envelope populados, `advicesExcludedByArity` no results JSON e contadores do parser, em `data/gh104/evidence/device_validation.md` | `gh104/tasks.md:258` |
| 10.5 | gh104 | ler a evidência de dispositivo contra o tier do pivô — **três** linhas: `TrustManagerFactorySpec` `X509`, `KeyStoreSpec` `AndroidKeyStore`, `SSLContextSpec` `TLS`; forma, não contagem. "Runs only after Group 11" | `gh104/tasks.md:259` |
| 8.8 | gh105 | destravada pelo **arquivamento** da gh104, que só vem depois desta campanha | `gh105/tasks.md:1295` |

A gh105 escreve isso explicitamente no seu preâmbulo: as tarefas 8.8 e 8.9 "cannot close inside
this change's own execution window, **by construction and not by delay**"
(`openspec/changes/gh105-predicate-wiring/tasks.md:3-7`), e o Grupo 10 da gh104 "roda no
experimento conjunto depois que **ambas** as changes caírem"
(`openspec/changes/gh105-predicate-wiring/design.md:656-660`).

**O que a 10.5 pede hoje é diferente do que este plano dizia em 18/08.** A tabela antiga tinha
cinco linhas e justificava TLS e AndroidKeyStore com "está na lista api30". Sob a D-15 o mecanismo
é outro — listas expert **mais** a camada `platform-value` de cinco entradas da tarefa 11.4 **mais**
a regra de normalização da tarefa 2.5 — e a lista de conferência encolheu para três: `CipherSpec`
OAEP e `SignatureSpec` SHA256WITHRSA saíram (a segunda porque a comparação case-insensitive já a
cobre; a primeira porque nunca esteve na metade silenciosa — era erro de contabilidade da D-10,
corrigido pela 11.5).

**As cinco entradas `platform-value`**, para conferência no P6:
`SSLContextSpec += TLS` (citando Conscrypt `android11-release` `OpenSSLProvider.java:81`, onde
`SSLContext.TLS` liga à implementação TLSv1.2/TLSv1.3) e
`KeyStoreSpec += {AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}`. Não há sexta: `X509`
resolve para `PKIX` pela alias table, `SHA256WITHRSA` é coberto por case-insensitivity, e **`SSL`
não ganhou linha** (decisão do pesquisador, 24/08) — continua acusado, e a razão está escrita na
linha `behavioural` de `data/jca_android/divergence_record.csv:307`.

**A gh106 não participa disto.** Ela mede o contrato `.mop` × `.crysl` estaticamente e declara que
não muda o que os monitores acusam. Mas ela nos deixou uma exigência de método que este arquivo
adota na §"Regra de carimbo": escalar publicado sem regra de contagem e sem commit não é
verificável. A Fase 0 dela achou **quatro** escalares assim, e o que funcionou não foi caçar a
regra nem apagar o número, mas registrar que ele não reproduz, dizer o que foi tentado, e publicar
o valor do instrumento com a regra sob a qual foi tomado (`UnreproducibleFigure`).
