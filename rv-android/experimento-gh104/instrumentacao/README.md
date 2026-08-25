# Estágios 0 e 1 — gerar os monitores das specs novas e tecer os 162 APKs (`dexlib2`, no host)

Este diretório produz **um artefato só**: o corpus dos 162 APKs da `comp162` reinstrumentados com
o conjunto de specs novo da change `gh104`, para que a campanha possa rodar de novo com **o
conjunto de specs como único fator que varia**.

Nada aqui executa aplicação. A Fase 2 do `ExperimentController` é pulada inteira
(`--skip-execution`) e nenhum emulador sobe.

O contexto, as decisões fechadas e os bloqueadores estão em `../CONTEXTO.md`. Leia antes.

---

## Por que no host, e não em Docker

A decisão **D6** (`docs/20260810_plano_prontidao_estudo03.md:58`) manda rodar análise estática e
instrumentação **no host, sem Docker**, e ela valeu na produção do corpus da `comp162`:
8 processos `rv-experiment` concorrentes, **3 h 53 min para 163 APKs**, `rc=0`
(`docs/20260812_registro_execucao_prontidao_e3.md:228`). O paralelismo é sharding de processo.

> A campanha irmã `comp162-ajc` precisou reabrir a D6 porque `ajc`, `d8`, `zipalign` e `apksigner`
> não existem no `PATH` do host. **A rota `dexlib2` não tem esse problema**: o Python só invoca
> `java` e `mvn`; `javac`, `d8` e a assinatura são resolvidos **dentro** do `instr-cli.jar` a
> partir de `ANDROID_HOME`/`JAVA_HOME`.

E há uma razão que decide o plano inteiro:

> **Os jars locais só entram no APK se a instrumentação rodar no host.** Em Docker a imagem clona
> do GitHub e reconstrói (`docker/rvandroid/Dockerfile:14-18`); o que vale ali é o `~/.m2` da
> imagem, não o nosso. Como a gh104 muda o `rvsec-core` (o `ErrorDescription` que produz a
> mensagem) e o `rv-monitor` (a macro `__EVENTNAME`), tecer no host é o que garante que o binário
> carrega o código novo.

---

## Pré-requisitos

```bash
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk
```

O `preflight.py` confere tudo isto e reprova com exit ≠ 0. Em resumo:

| item | onde | observação |
|---|---|---|
| specs novas | `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/` | o conjunto sucessor: **24** `.mop` + `codes.csv`, **zero** `ExecutionContext` (medido 24/08, HEAD `6192b57a`). Eram esperados 21 — ver `../CONTEXTO.md` §3.1 |
| reator instalado | `/home/pedro/desenvolvimento/repository` | repositório Maven local — **não** é `~/.m2/repository`; está em `~/.m2/settings.xml` |
| `instr-cli.jar` | `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` | `lib/` é gitignored; o jar só existe depois de um build do reator |
| `java`, `mvn` | `PATH` | o `dexlib2` invoca os dois |
| keystore | `modules/rv-instrumentation/assets/keystore.jks` | resolvido automaticamente (`modules/rv-experiment/src/rv_experiment/config.py:863-872`); **não** é o `keystore.jks` da raiz |

### O build do reator é obrigatório antes de tudo

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipTests -DskipMopAgent
```

`-DskipMopAgent` **é obrigatório**: sem ele o `install` de raiz falha, e além disso
`rvsec/rvsec-agent/pom.xml:94-111` regeneraria o monitor do agente JSE a partir de
`resources/jca` a cada build.

Esse build faz duas coisas de que o estágio 1 depende:

1. republica `rvsec-core-0.9.3-SNAPSHOT.jar` no repositório local — **esse jar é dexado dentro de
   cada APK**, via `mvn dependency:copy-dependencies`
   (`modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py:114-123`);
2. recopia o `instr-cli.jar` para `modules/rv-instrumentation-dexlib2/lib/` (design D9). Rebuild
   isolado, se precisar: `mvn -pl rvsec-android/rvsec-instrumentation-dexlib2/cli -am package`.

**Se o reator não for reconstruído depois da mudança de specs, o APK sai com o `rvsec-core`
velho e as mensagens continuam ilegíveis** — o `preflight.py` avisa alto quando o mtime do
`rvsec-core.jar` é anterior ao `.mop` mais novo.

### Reverificar o build antes de lançar — este portão envelhece sozinho

Reverificado em 2026-08-25: `rvsec-core-0.9.3-SNAPSHOT.jar` às **24/08 23:01** e `instr-cli.jar` às
**24/08 23:12**, ambos posteriores ao `.mop` mais novo do conjunto (`IvChainJunction.mop`, 11:51).
O portão continua **fechado**. (A medida anterior registrava 20:26/20:28; o reator foi reconstruído
outra vez no mesmo dia.)

O `preflight.py` do shard `s0` rodou em 25/08 e passou em tudo menos no diretório de saída, que só
nasce no estágio 1: conjunto `jca_android` com 24 `.mop`
(`sha256=6ad2dee42645fab3b200ceed400c0f876b888c93bf1b7f7ef58af558ad2c4998`), os três jars de runtime
no repositório local, `dexlib2 -> DexlibInstrumentation`, JDK 25 e Maven 3.9.9, 21/21 APKs do shard
presentes. Os três avisos de `method_ids` são os mesmos de 18/08 —
`com.dessalines.rankmyfavs_44.apk:classes13.dex free=5`,
`com.dessalines.habitmaker_5501.apk:classes.dex free=18`,
`rocks.poopjournal.metadataremover_20020.apk:classes16.dex free=20`.

É o único item da prontidão que se reabre sem que ninguém mexa nele: basta um `.mop` ser editado
depois do último `install`. O `preflight.py` avisa alto quando o mtime do `rvsec-core.jar` é
anterior ao `.mop` mais novo (`preflight.py:190-194`) — e é por isso que ele roda por shard, e não
uma vez só.

### Registrar a proveniência antes de lançar

Espelhar o que o E3 fez em `RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/PROVENIENCIA.md`:
branch, commit, JDK, repositório Maven local, sha256 do `rvsec-core.jar` e do `instr-cli.jar`, e
**o sha256 de cada `.mop` do conjunto novo**. Sem isso não se sabe, depois, qual conjunto produziu
qual número. O `preflight.py` imprime esses hashes.

---

## Estágio 0 — gerar os monitores, **uma vez, sozinho**

### O defeito que obriga a isto

Geração de monitores **não é paralelizável**. O JavaMOP deixa os `.rvm` no diretório de specs
**compartilhado** e o gerador os **move** de lá
(`modules/rv-monitor-generator/src/rv_monitor_generator/runtime_verification_generator.py:218-222`).
N geradores concorrentes roubam os `.rvm` uns dos outros e `_execute_rvmonitor` morre com
`[Error] Target file, .../monitors/*.rvm, doesn't exist!`.

**E a falha não aborta**: o `ErrorHandler` a captura e o pipeline segue para a instrumentação com
monitores faltando, **reportando sucesso**. No piloto do E3, cinco fatias concorrentes produziram
cinco conjuntos diferentes, e só uma saiu com `MultiSpec_1RuntimeMonitor.java`
(`docs/20260812_registro_execucao_prontidao_e3.md:190-213`; a evidência está preservada em
`backup/e3-piloto-monitor-race-20260812/`).

Contrapartida boa: **rodando sozinha, a geração é determinística** — o mesmo conjunto de specs
produz monitores byte-idênticos. É isso que permite congelar um `monitors_master` e reusá-lo.

### O comando

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
D=$(pwd)/experimento-gh104/instrumentacao

uv run rv-experiment run \
  --name gh104_monitors \
  --specification-set jca_android \
  --instrumentation-variant dexlib2 \
  --generate-monitors \
  --skip-instrument \
  --skip-static \
  --skip-execution \
  --apks-dir    /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS \
  --apks-filter $D/../filters/s0.txt \
  --output-dir  $D/../monitores/monitors_master \
  2>&1 | tee $D/../monitores/monitors_master.log
```

O `--apks-filter` é exigido pelo CLI mas é **inerte** aqui: `--skip-instrument` não toca APK
nenhum. Custo medido na corrida anterior (23 specs `jca`): **73 s**. Para o conjunto novo, espere
mais: o `CipherSpec` está no teto de 17 eventos e a gh105 mediu **duas gerações de 79 s e 77 s com
pico de RSS de 5,4 GB e 4,5 GB**, byte-idênticas entre si. O `TMPDIR` fora de tmpfs deixa de ser
higiene e passa a ser requisito.

### Portão do estágio 0 — não seguir sem isto

```bash
ls -l experimento-gh104/monitores/monitors_master/monitors/
sha256sum experimento-gh104/monitores/monitors_master/monitors/*
```

Tem de existir, no mínimo:

| arquivo | quem consome |
|---|---|
| `MultiSpec_1MonitorAspect.json` | **o `dexlib2`** — é o descritor, passado em `--descriptor` |
| `MultiSpec_1RuntimeMonitor.java` | compilado por `javac` dentro do `instr-cli` |
| `MultiSpec_1MonitorAspect.aj` | só a variante `ajc`; fica no diretório sem ser usado |
| `Coverage.aj` | idem |

Sem o `.json`: `MissingDescriptorError` (INV-INS-50). Sem o `*RuntimeMonitor.java`: a tecelagem
segue e sai um corpus inútil.

**Verificações extras que a gh104 exige do gerador** (grupo G):

```bash
M=experimento-gh104/monitores/monitors_master/monitors/MultiSpec_1RuntimeMonitor.java
grep -c 'tryLock'  $M
grep -c 'unlock'   $M
grep -c 'finally'  $M      # os três TÊM de bater — hoje o terceiro é 0
grep -c '__EVENTNAME' $M   # TEM de ser 0: a macro não pode sobreviver no Java gerado
```

Registrar o digest do conjunto (sha256 ordenado dos sha256 por arquivo) — ele entra no
`manifest.json` da campanha.

---

## Estágio 1 — tecer os 162, em 8 shards paralelos

### 1. Partição

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
uv run python experimento-gh104/scripts/make_shards.py
uv run python experimento-gh104/scripts/make_shards.py --check
```

Round-robin sobre a ordem **decrescente de tamanho** do APK original, para os grandes se
espalharem e os shards terminarem juntos. Escreve `experimento-gh104/filters/s0.txt .. s7.txt`.

**LF only, sem espaço à direita, sem duplicata.** O filtro casa por basename via
`read_text().strip().splitlines()` (`modules/rv-experiment/src/rv_experiment/config.py:584-586`) —
um `\r` faz o APK sumir **em silêncio**.

> Esta partição é a da **instrumentação**. A partição da **campanha** (`batch_NN.txt`) é outra
> coisa: ela é herdada verbatim da `comp162` e apenas podada, para que o índice de container por
> app seja o mesmo dos dois lados e o efeito-de-container cancele no pareamento.

### 2. Copiar os monitores para cada shard — **cópia real, nunca symlink**

```bash
D=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/experimento-gh104
for i in 0 1 2 3 4 5 6 7; do
  mkdir -p $D/instrumentacao/results/s$i
  cp -r $D/monitores/monitors_master/monitors $D/instrumentacao/results/s$i/monitors
done
```

Por que cópia real: `WrapperEmitter.generate(descriptor, wrapperOutDir=cfg.monitorSrcDir(), ...)`
(`BatchRunner.java:195-199`) **escreve dentro de `monitors/`** durante a tecelagem —
`mop/MonitorWrappers.java` e `mop/Coverage.java` aparecem lá. Um diretório compartilhado (ou
somente-leitura) entre shards se corromperia.

### 3. Preflight por shard — só lançar com PASS

```bash
for i in 0 1 2 3 4 5 6 7; do
  uv run python experimento-gh104/scripts/preflight.py \
    --shard-file experimento-gh104/filters/s$i.txt \
    --output-dir experimento-gh104/instrumentacao/results/s$i \
    --spec-set jca_android \
    --expect $(wc -l < experimento-gh104/filters/s$i.txt) \
    --methodid-margin 30 \
    || echo "REPROVOU s$i"
done
```

O preflight também lê o header DEX de cada `classes*.dex` e avisa quando a folga de `method_ids`
é pequena — é a antecipação barata da única perda determinística da corrida anterior
(`info.dvkr.screenstream_44000.apk`: `classes28.dex` com **65.521 dos 65.536** `method_ids`; os 84
wrappers não cabem). **Se o conjunto novo tiver contagem de wrappers diferente, essa fronteira se
move.**

**Use `--methodid-margin 30`, não o default de 200.** Medido no shard `s0`: com 200, 18 dos 21
APKs disparam o aviso, incluindo APKs que a `comp162` instrumentou com sucesso (o caso limite
conhecido que passou tinha `free=183`). Com 30, sobra o sinal útil — na cauda ficam
`com.dessalines.rankmyfavs_44.apk:classes13.dex free=5`,
`com.dessalines.habitmaker_5501.apk:classes.dex free=18` e
`rocks.poopjournal.metadataremover_20020.apk:classes16.dex free=20`. Esses são os candidatos reais
a perda determinística.

> O leitor de `method_ids` foi conferido contra o registro do E3: para o `screenstream` ele devolve
> `classes28.dex used=65521 free=15`, exatamente o número documentado.

### 4. Lançar as 8 fatias

Cada fatia precisa do **seu próprio `--output-dir`**. `--work-dir == --output-dir`
(`modules/rv-experiment/src/rv_experiment/config.py:856`) e o `BatchRunner.java` resolve
`workDir.resolve("woven_" + entryName)` e `workDir.resolve("monitor-build")` — nomes planos e
compartilhados. Duas JVMs no mesmo work dir sobrescrevem o `woven_classes.dex` uma da outra **sem
erro**.

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
D=$(pwd)/experimento-gh104

for i in 0 1 2 3 4 5 6 7; do
  uv run rv-experiment run \
    --name gh104_instr_s$i \
    --specification-set jca_android \
    --instrumentation-variant dexlib2 \
    --skip-monitors \
    --instrument-apks \
    --skip-static \
    --skip-execution \
    --apks-dir    /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS \
    --apks-filter $D/filters/s$i.txt \
    --output-dir  $D/instrumentacao/results/s$i \
    > $D/instrumentacao/results/s$i.log 2>&1 &
done
wait
```

`--instrumentation-variant dexlib2` **tem de ser explícito**: o default do CLI é `ajc`
(`modules/rv-instrumentation/src/rv_instrumentation/config.py:199-201`).

Orçamento: ~1,4 min/APK medido, **~3 h 53 min** para 162 em 8 fatias. RSS de 1,0–2,1 GiB por JVM;
picos de até ~1400 s num único APK. **Não há timeout de wallclock por APK, por decisão**
(`modules/rv-instrumentation-dexlib2/.../config.py:93-100`) — acompanhar por **progresso**, não
por relógio:

```bash
watch -n 300 'ls experimento-gh104/instrumentacao/results/s*/instrumented_apks/*.apk 2>/dev/null | wc -l'
```

### 5. Portão do estágio 1

```bash
# cardinalidade: 162 esperados, zero duplicados entre fatias
ls experimento-gh104/instrumentacao/results/s*/instrumented_apks/*.apk | xargs -n1 basename | sort | uniq -d
ls experimento-gh104/instrumentacao/results/s*/instrumented_apks/*.apk | wc -l

# perdas: cada fatia tem o seu
cat experimento-gh104/instrumentacao/results/s*/instrumented_apks/instrument_errors.json
```

**Não confie no exit code do `instr-cli`**: ele sai 0 mesmo com `success=false`. Quem detecta é a
checagem de existência do APK no wrapper Python
(`modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:273-284`)
e o `_demote_silent_failures` do caminho batch.

**Um modo de falha que a `gh100` acrescentou, e que é bem-vindo**: `parseCommonPointcut` levanta
`UnsupportedAspectConstructError` em vez de devolver `null` (`DexWeaver.java:888-893`). Um
descritor com `commonPointcut` malformado, que antes degradava "graciosamente" tecendo todos os
sítios que as exclusões existiam para excluir — e reportava sucesso —, agora para a tecelagem. Um
APK que falhe assim está dizendo a verdade.

Ler o `instrument_results.json` de cada fatia — `{"variant": "dexlib2", "results": [...]}`, cada
entrada com `apkName, success, message, phase, weaveCounts`. `weaveCounts` tem **20** campos
(19 antes de 2026-08-19). Referências da corrida com o `jca`:

| campo | valor no `jca` | leitura |
|---|---|---|
| `advices` | **115** em todos os 162 | o descritor congelado |
| `wrappersGenerated` | **84** | wrappers `mop.MonitorWrappers` para as 23 specs |
| `wrappersSubstituted` | mediana 170, soma 46.926, **zero APKs com 0** | **esta** é a métrica de superfície tecida |
| `matchesApplied` | — | **NÃO** é a métrica de superfície: um APK pode ter `matchesApplied = 0` e estar corretamente instrumentado |
| `plansSkippedAliasing` | 1832 em 139 APKs (3,9 %) | recusa deliberada, INV-INS-66 |
| `advicesExcludedByArity` | **existe desde 2026-08-19** (commit `b43f500e`, INV-INS-122) | mede e **não filtra**; é **fração de 48**, não de 115. Cobre só *after*-advices do caminho de wrapper — `before` e construtor nunca chegam ao laço de agrupamento |

Os três primeiros mudam com o conjunto novo (**24** specs em vez de 23) — o valor não importa em
si, importa que seja **o mesmo em todos os APKs** e que ninguém saia com zero sítios.

**`weaveCounts` tem 20 campos, não 19**: `advicesExcludedByArity` entrou em 19/08, um dia depois de
este runbook ser escrito. O `../scripts/gh104_gates.py:179` já o exige, e o G10 reprova sem ele —
ou seja, o script sempre esteve certo e este parágrafo é que estava velho.

**E `wrappersGenerated = 84` já é valor pós-`gh100`.** A fusão de wrappers levou 96 → 84 juntando
os 12 que antes eram descartados em silêncio, sem mover `wrappersSubstituted` (74 → 74). Nada da
gh100 renomeou contador nem mudou a semântica de `wrappersSubstituted` ou `matchesApplied`.

### 6. Montar o corpus de entrega

Layout **plano**: `<nome>.apk` e `<nome>.apk.json` lado a lado, mais `selected162.txt`. É como o
`pre_processor` acha a análise estática — `app_path + EXTENSION_STATIC_ANALYSIS`
(`modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:459`, INV-EXP-16).

Destino: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_android_gh104_selected162/`

- os `.apk` vêm das 8 fatias (**cópia real**, para as fatias ficarem como proveniência);
- os `.apk.json` são **copiados tal e qual** do corpus da `comp162`
  (`APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162/`) — é a decisão D-c: denominador
  de cobertura idêntico, que é a condição que torna a comparação pareada atribuível;
- gerar `SHA256SUMS` e a lista `selected162.txt`;
- **o `corpus_basis` tem nome próprio**, mesmo com a lista de nomes idêntica à da `comp162`:
  `selected162gh104:<sha256 do txt>`. Duas campanhas com corpora diferentes não podem se passar
  uma pela outra.

> Não existe script committado de montagem de corpus para a rota `dexlib2` — na corrida anterior a
> montagem foi manual (`docs/20260812_registro_execucao_prontidao_e3.md:425-441`).

### 7. Validar em emulador antes de declarar o corpus pronto

```bash
uv run python scripts/e3_validate_emulator.py \
  --corpus /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_android_gh104_selected162 \
  --out    /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/E3_VALIDACAO_EMULADOR_gh104
```

Instala, lança, espera 15 s, lê o logcat, classifica, desinstala — serial, retomável, um logcat
por APK. **É validação de boot, não de exploração.**

Referência do `jca`/`dexlib2` (2026-08-12, 49 min, 18,1 s/APK): instalou 162/162, lançou 162/162,
`RVSEC-COV` ≥ 2 em 162/162, **zero** `VerifyError`, `FATAL EXCEPTION`, `ANR` e `Error type 3`.
É a barra a bater.

> O emulador desta validação é subido **pelo pesquisador**, por `scripts/run_emulator.sh`, e é a
> única exceção autorizada à regra de não gerenciar emuladores. O pipeline nunca sobe emulador
> nesta fase.

Aqui há um ganho específico da gh104 a observar: com o `try/finally` nos 134 dispatchers
(INV-INS-129), runs que hoje travam em livelock — e **parecem timeout** — deixam de travar. Se a
validação do conjunto novo mostrar menos ANR que a do `jca`, é isso.

---

## Saídas deste estágio

```
experimento-gh104/
├── monitores/
│   ├── monitors_master/monitors/{*.json,*.java,*.aj}   ← congelado, com digest
│   └── monitors_master.log
└── instrumentacao/
    └── results/
        └── s0..s7/
            ├── experiment_config.json      ← a config efetiva: a fonte de verdade do que rodou
            ├── monitors/                   ← cópia do master + mop/ gerado na tecelagem
            ├── lib_tmp/                    ← jars do mvn copy-dependencies
            ├── woven_classes*.dex          ← scratch do ÚLTIMO APK da fatia (nomes planos)
            ├── monitor-build/              ← scratch do javac/d8
            └── instrumented_apks/
                ├── <nome>.apk  <nome>.apk.idsig
                ├── instrument_results.json     ← results[].weaveCounts
                ├── instrument_errors.json
                └── instrument_results.d/<stem>.{json,log}   ← argv literal + exit + stdout
```

`instrument_results.d/<stem>.log` guarda o **argv literal** da JVM daquele APK. É o primeiro lugar
a olhar quando um APK falha.

---

## Armadilhas

1. **`lib_tmp/` é propenso a jar velho.** `mvn dependency:copy-dependencies` não sobrescreve
   snapshot por default. Apagar `lib_tmp/` de cada fatia antes de reinstrumentar com jars novos.
2. **Não rodar o estágio 1 enquanto uma campanha ocupa a máquina.** 8 JVMs a 2 GiB disputariam com
   emuladores que medem cobertura sob orçamento de 300 s.
3. **`--output-dir` não pode preexistir** — o preflight reprova, de propósito, para não misturar
   com uma corrida anterior.
4. **Nunca `nohup`/`setsid`** para lançar as fatias: o processo tem de ficar rastreável.
5. **A geração de monitores nunca em paralelo** (estágio 0).
