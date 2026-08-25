# Prontidão — a ordem de execução e os portões

Checklist mestre. Cada linha é verificável por comando. **Nenhum estágio começa antes do portão do
anterior fechar.**

**Estado em 2026-08-25: P0, P1 fechados. P2 em diante, abertos.** Os escalares foram medidos em
24/08 (HEAD `6192b57a`) e reverificados em 25/08 — `rvsec-core.jar` às 23:01 e `instr-cli.jar` às
23:12 contra o `.mop` mais novo às 11:51; 24 `.mop` e `codes.csv` com 114 códigos. Reverifique
antes de agir: o P1 envelhece sozinho.

**O ferramental está pronto**: os três defeitos de script (F1, F2 e o verde-sobre-nada do
`smoke_gates.py`) foram corrigidos em 25/08 e exercitados. Falta artefato, não código — os
monitores do P2 em diante. O F3 (colisão de nome entre os dois `gh104_gates.py`) continua aberto e
é decisão do pesquisador.

Documentos: `CONTEXTO.md` (a memória), `docs/gh104_mudancas_observaveis.md` (o que muda na saída),
`instrumentacao/README.md` (estágios 0 e 1), `README.md` (estágios 2 e 3),
`docs/20260824_reconciliacao.md` (o que mudou entre 18/08 e 24/08, com comando ao lado).

```
P0  a change gh104 implementada             ← bloqueia tudo; não é nosso
P1  reator Java reconstruído e instalado    ← host
P2  estágio 0: monitores gerados (uma vez)  ← host, ~2 min
P3  estágio 1: 162 APKs tecidos             ← host, 8 shards, ~4 h
P4  corpus montado e validado em emulador   ← ~1 h
P5  imagem Docker reconstruída              ← push + build
P6  piloto do gate 10.4 (4 APKs)            ← ~30 min; decide se vale rodar 20 h
P7  smoke da campanha (6 identidades)       ← 7 portões + o de mensagens, ou não segue
P8  estágio 2: a campanha (1458 identidades)← ~20 h
P9  estágio 3: consolidação e verificação   ← offline
```

---

## P0 — a change gh104 implementada

Não é trabalho desta campanha. O que precisamos é do resultado.

```bash
S=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
ls $S/jca_android/*.mop | wc -l              # esperado: 24  (23 da semente + IvChainJunction.mop)
grep -rc 'ExecutionContext' $S/jca_android/ | grep -v ':0' | wc -l   # esperado: 0 arquivos
ls -d $S/jca_android_bug_predicate           # o conjunto reprovado da gh101 foi renomeado
ls $S/jca_android/codes.csv                  # o catálogo de códigos do envelope
```

E o conjunto congelado tem de continuar intocado:

```bash
cd $RVSEC_HOME && git diff 7e7acb69 -- rvsec/rvsec-mop/src/main/resources/jca   # vazio
```

**Medido em 2026-08-24 (HEAD `6192b57a`): 24 `.mop`, zero `ExecutionContext`, `codes.csv` presente
com 114 códigos, `git diff` do congelado vazio. Este portão ABRIU.**

> **A contagem esperada era 21 e não é.** O número vinha da deleção de `RandomStringPassword.mop` e
> `SecretKeySpec.mop`, que a **D-11** retirou — a semente inteira fica, 23 arquivos. A gh105
> acrescentou `IvChainJunction.mop` (tarefa 5.1) porque a cláusula do IV liga um argumento que o
> `CipherSpec.i2` não liga, e o `CipherSpec` está no teto do gerador (17 de 17 eventos, headroom
> zero). `23 + 1 = 24`. Detalhe em `CONTEXTO.md` §3.1.

**Três tarefas da gh104 continuam abertas, e duas delas são desta campanha**: `10.4` e `10.5` são o
piloto do P6; `10.8` é o sync de invariantes, que roda no arquivamento. A `gh105` fica em 72/74 até
a gh104 arquivar. Ver `CONTEXTO.md` §10.

---

## P1 — reator reconstruído

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipTests -DskipMopAgent
```

`-DskipMopAgent` é obrigatório (sem ele o `install` de raiz falha, e `rvsec-agent/pom.xml:94-111`
regeneraria o monitor do agente JSE a partir de `resources/jca`).

Portão:

```bash
R=/home/pedro/desenvolvimento/repository/br/unb/cic
ls -l $R/rvsec-core/0.9.3-SNAPSHOT/rvsec-core-0.9.3-SNAPSHOT.jar     # mtime > mtime do .mop mais novo
ls -l modules/rv-instrumentation-dexlib2/lib/instr-cli.jar           # recopiado pelo build (D9)
```

**Reverificado em 2026-08-25: `rvsec-core.jar` às 24/08 23:01, `instr-cli.jar` às 24/08 23:12,
contra o `.mop` mais novo às 24/08 11:51. Este portão ABRIU.** (A medida anterior deste bloco dizia
20:26/20:28 — o reator foi reconstruído de novo mais tarde no mesmo dia; o veredito não muda.) Ele é o único da lista que **envelhece sozinho**: qualquer
edição posterior num `.mop` o reabre sem avisar, e o `preflight.py` é quem grita
(`check_runtime_jars`, `preflight.py:190-194`).

**Por que importa:** o `rvsec-core.jar` é dexado dentro de cada APK. Se ele for o velho, o
`ErrorDescription` de 3 argumentos continua emitindo `unknown` e a campanha inteira mede o
comportamento antigo com specs novas — o pior dos dois mundos, e difícil de perceber depois.

Registrar a proveniência (branch, commit, JDK, sha256 dos dois jars e de **cada** `.mop`) em
`monitores/PROVENIENCIA.md`, no molde do
`RV_ANDROID_NOVO_DATASET/E3_jca_dexlib2_163/PROVENIENCIA.md`.

---

## P2 — estágio 0: monitores

Comando em `instrumentacao/README.md` §"Estágio 0". **Um processo só** — a geração não é
paralelizável e falha em silêncio quando concorre.

Portão:

```bash
M=experimento-gh104/monitores/monitors_master/monitors
ls $M/MultiSpec_1MonitorAspect.json          # o descritor: sem ele, MissingDescriptorError
ls $M/MultiSpec_1RuntimeMonitor.java         # sem ele, o corpus sai inútil
grep -c '__EVENTNAME' $M/MultiSpec_1RuntimeMonitor.java   # TEM de ser 0
grep -c tryLock $M/MultiSpec_1RuntimeMonitor.java
grep -c unlock  $M/MultiSpec_1RuntimeMonitor.java
grep -c finally $M/MultiSpec_1RuntimeMonitor.java         # os três TÊM de bater
sha256sum $M/*                                            # registrar o digest
```

O `grep -c finally` é o teste do INV-INS-129: hoje ele dá **0** contra 134 `tryLock`, e é por isso
que uma exceção dentro de um handler converte o app num livelock que **parece timeout**.

---

## P3 — estágio 1: tecelagem

Comandos em `instrumentacao/README.md` §"Estágio 1". Preflight por shard antes de lançar.

Portão:

```bash
ls experimento-gh104/instrumentacao/results/s*/instrumented_apks/*.apk | wc -l   # 162 menos as perdas
ls experimento-gh104/instrumentacao/results/s*/instrumented_apks/*.apk \
  | xargs -n1 basename | sort | uniq -d                                          # vazio
cat experimento-gh104/instrumentacao/results/s*/instrumented_apks/instrument_errors.json
```

E no `instrument_results.json`: `advices` e `wrappersGenerated` **iguais em todos os APKs**, e
**nenhum APK com `wrappersSubstituted == 0`**. Desde 2026-08-19 o documento também traz
`advicesExcludedByArity` (commit `b43f500e`, INV-INS-122) — `weaveCounts` passou de 19 para **20**
campos, e é isso que o G10 do portão de mensagens exige (`scripts/gh104_gates.py:179`).

**Modo de falha novo, herdado da gh100**: `parseCommonPointcut` passou a levantar
`UnsupportedAspectConstructError` em vez de devolver `null` (`DexWeaver.java:888-893`). Um
descritor com `commonPointcut` malformado, que antes tecia todos os sítios que as exclusões
existiam para excluir e reportava sucesso, agora **falha**. Se um APK cair aí, é isso, e é a falha
certa.

**Regra de decisão, escrita antes do dado:** a corrida anterior perdeu 1 de 163 (0,61 %). Se a
perda desta vez passar de **~5 %**, parar e investigar antes de montar o corpus — provavelmente é
o teto de `method_ids` se movendo com a contagem nova de wrappers, e o preflight já terá avisado
quais APKs estão na fronteira.

---

## P4 — corpus montado e validado

Montagem em `instrumentacao/README.md` §6; validação em §7.

Portão:

```bash
C=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_android_gh104_selected162
ls $C/*.apk | wc -l ; ls $C/*.apk.json | wc -l      # têm de bater 1:1
sha256sum -c $C/SHA256SUMS
sha256sum $C/selected162.txt                        # este é o corpus_basis
```

Validação em emulador: instalou N/N, lançou N/N, `RVSEC-COV` ≥ 2 em N/N, **zero** `VerifyError`,
`FATAL EXCEPTION`, `ANR` e `Error type 3`. É a barra que o `jca`/`dexlib2` bateu.

---

## P5 — imagem Docker

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
git push origin modules
# editar a tag antes: gerar phtcosta/rvandroid:0.9.3-gh104, NÃO sobrescrever 0.9.3/latest
bash rv-android/docker/rvandroid/build.sh
docker images --digests | grep rvandroid          # registrar o image id no manifest.json
```

**Não sobrescrever a tag `0.9.3`** — mas note que a razão registrada até 24/08 estava errada: a
`comp162` **não** roda em `0.9.3`, roda em `phtcosta/rvandroid:0.9.3-comp162`, id
`sha256:811d3ef3ad5b…` (`../experimento-comp162/docker-compose.yml:58` e o `manifest.json` dela).
Medido: `0.9.3` e `latest` apontam para `9cca8e617c7c`, outra imagem. A referência já está
protegida por tag própria; a razão para preservar `0.9.3` é ela ser a tag genérica de que outras
coisas dependem.

O branch `modules` está **124 commits** à frente de `origin/modules` (eram 4 em 18/08).

**O que a imagem velha estragaria, se este portão atrasar:** só a saída derivada. A mensagem nasce
dentro do APK (tecido no host, no P3), então o `.logcat` já traz o envelope novo; o que sairia
velho é o `errors.csv` (11 colunas), o `unique_msg` (5 partes) e os `ParserDiagnostics`. O
`gh104_gates.py` lê as duas populações — CSV e logcat — exatamente por isso.

---

## P6 — piloto do gate 10.4

É o critério que a própria change define (tarefa 10.4), e custa quase nada perto da campanha.

4 APKs, `monkey`, 180 s: `com.owncloud.android_48000100`, `eu.opencloud.android_9`,
`de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700`.

**Verificado: os quatro estão nos 162 de `selected162.txt`.** Saem prontos do estágio 1, sem shard
extra e sem tecelagem à parte — o piloto é só apontar a corrida para eles dentro do corpus novo.

```bash
uv run python experimento-gh104/scripts/gh104_gates.py \
  --results-glob '<dir do piloto>' --label piloto-10.4 --json experimento-gh104/consolidado/piloto_gates.json
```

Critérios (tarefa 10.4): `unknown` = 0 · `but found .` = 0 · `ev`/`val`/`exp` populados ·
`advicesExcludedByArity` e `wrappersGenerated` presentes · contadores do parser presentes.

**Leitura de forma, não de contagem** (tarefa 10.5, Monkey é estocástico). **O critério mudou em
24/08 e o texto antigo deste bloco foi substituído.** A tarefa 10.5 hoje pede **três** linhas, não
cinco (`openspec/changes/gh104-legible-violation-reports/tasks.md:259`):

| linha | esperado | mecanismo sob a D-15 |
|---|---|---|
| `TrustManagerFactorySpec` `X509` | **não reportada** | resolve para `PKIX` pela regra de normalização da tarefa 2.5; `PKIX` está na lista expert. Não precisou de entrada `platform-value` |
| `KeyStoreSpec` `AndroidKeyStore` | **não reportada** | entrada `platform-value` da tarefa 11.4 (a lista expert é JSE-only: `{JCEKS, JKS, DKS, PKCS11, PKCS12}`) |
| `SSLContextSpec` `TLS` | **não reportada** | entrada `platform-value` citando Conscrypt `OpenSSLProvider.java:81` |

Saíram da lista de conferência: `SignatureSpec` `SHA256WITHRSA` (coberto por comparação
case-insensitive) e `CipherSpec` `RSA/ECB/OAEPWithSHA1AndMGF1Padding` — este **nunca esteve** na
metade silenciosa; era erro de contabilidade da D-10, corrigido pela tarefa 11.5. Ele continua
acusado, como sempre esteve.

**E há o outro lado do critério, que é bilateral**: a D-15 devolveu acusações. Se aparecerem no
piloto, é o esperado, não regressão — `MD5`/`SHA-1` em `MessageDigestSpec`, `SSL` em
`SSLContextSpec`, `AES/ECB` em `CipherSpec`, e a família `NOBS` inteira em qualquer spec.

Sítio não alcançado **não** é evidência de reparo.

**Se este portão reprovar, não rodar as 20 h.** É para isso que ele existe.

---

## P7 — smoke da campanha

2 APKs × 3 braços × 1 rep × 120 s = 6 identidades, 2 containers. Os **7** portões de execução do
`scripts/smoke_gates.py` **mais** o portão de mensagens (`gh104_gates.py` sobre `results_smoke/`)
— o critério de aceitação são os dois scripts, **não** o `docker compose up` ter retornado. (Este
arquivo dizia "8 portões do `smoke_gates.py`"; são sete, e o oitavo critério é o outro script.)

Desde 25/08 nenhum portão do `smoke_gates.py` passa sobre população vazia: um `tasks.json` ausente
fazia os portões 2 a 6 anunciarem PASS sobre nada, porque cada um é um laço com acumulador
começando em `True`. Agora eles reprovam com `NADA MEDIDO`.

Só aqui o `docker compose down` é permitido.

---

## P8 — a campanha

1458 identidades, 8 containers, ~20 h. Ciclo de monitoramento de hora em hora:
`monitor.sh` (só lê) → reparar container **parado** → `docker compose up -d` (é o resume) →
admissibilidade.

- Contar por **identidade** `(apk, tool, variant, rep, timeout)`, nunca por registro: o resume
  acrescenta, e `state_transitions[]` conta em dobro.
- **Nunca `docker compose down` antes de consolidar**: `app_events.csv` só materializa no
  pós-processamento e os traces vivem no device.

---

## P9 — consolidação e verificação

Ordem em `README.md`. O que é específico desta campanha:

```bash
# 1. os portões da gh104 sobre a campanha nova — SEMPRE com --codes-csv: sem ele o G5
#    julga o KIND contra a lista congelada e não verifica se o código existe
uv run python experimento-gh104/scripts/gh104_gates.py \
  --results-glob 'experimento-gh104/results/gh104_*/gh104_*' \
  --codes-csv "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv" \
  --label gh104 --json experimento-gh104/consolidado/gh104_gates.json

# 2. a mesma leitura sobre a referência, para a tabela antes/depois. Sem --codes-csv, e de
#    propósito: o corpus pré-gh104 não tem envelope nenhum, logo não há código a catalogar
uv run python experimento-gh104/scripts/gh104_gates.py \
  --results-glob 'experimento-comp162/results/comp162_*/comp162_*' \
  --label baseline-comp162 --json experimento-gh104/consolidado/baseline_gates.json

# 3. o diff de violações E mensagens, com dimensão de spec
uv run python experimento-gh104/scripts/msg_diff.py \
  --run-a experimento-comp162    --prefix-a comp162 --label-a jca \
  --run-b experimento-gh104      --prefix-b gh104   --label-b jca_android \
  --specs-a $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --specs-b $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android \
  --out experimento-gh104/consolidado
```

O passo 2 já roda hoje e reproduz as baselines congeladas da gh104 (19.664 linhas · 15.714 mudas
= 79,91 % · 98 `but found .`), o que é a prova de que o portão mede a coisa certa.

> **Os dois reparos do ferramental foram feitos em 25/08** (achados em 24/08, detalhe em
> `CONTEXTO.md` §7):
> 1. **F1** — o G5 não conhecia o KIND `NOBS`, e **30 dos 114 códigos são `NOBS`**. O vocabulário
>    agora vem do `codes.csv` do conjunto sob medição (`--codes-csv`), e o portão passou a
>    verificar também se o código **existe** no catálogo, não só se o KIND é plausível.
> 2. **F2** — o `msg_diff.py` não punha `code` na identidade e resolvia mensagens pela mais
>    frequente, então uma segunda acusação num sítio já acusado sumia. Agora ele **junta por sítio
>    e compara por código**, uma linha por par `(sítio, código)`. A "correção mínima" que este
>    arquivo registrava — pôr o código na tupla de junção com sentinela para a era antiga — **não
>    funcionava**: destruiria o pareamento inteiro (100 % `so_A` + 100 % `so_B`, zero `ambos`).
>
> Verificado: o baseline `comp162` reproduz os números congelados sob o script novo (19.664
> linhas · 15.714 mudas = 79,91 % · 98 `but found .`), e corpora sintéticos exercitam os caminhos
> que ainda não têm dado real — `NOBS` aceito, KIND inexistente reprovado, código fora do catálogo
> reprovado, e o sítio com duas acusações rendendo duas linhas em vez de uma.

### O que olhar no `msg_diff.csv`

| coluna | leitura |
|---|---|
| `code` | **qual** acusação é esta linha. Cada linha do CSV é um par `(sítio, código)`; um sítio com dois códigos rende duas linhas, que é a acusação que a identidade antiga engolia |
| `codigos_no_sitio_b` | os códigos que aquele sítio carrega no lado novo. Com `\|` no meio, o sítio é multi-acusação — o resumo "acusações por sítio" os conta |
| `lado = so_A` + `causa = spec` | violações que o conjunto novo **deixou** de acusar por decisão — TLS, AndroidKeyStore, X509, SHA256WITHRSA, e os 17 acusadores órfãos que a gh105 calou. **MD5/SHA-1 não estão mais aqui**: a D-15 os devolveu |
| `lado = so_B` + `causa = spec` | violações **novas** — MD5/SHA-1 (5.892 linhas), `SSL` (103), `AES/ECB`, `NONEwithRSA`, a família `NOBS` inteira (30 códigos), o balde próprio do `IvChainJunctionSpec`, as guardas recuperadas e os pointcuts `s1/s2` do `SignatureSpec` |
| `msg_status = ilegivel_para_legivel` | o objetivo da change, sítio a sítio |
| `msg_status = legivel_para_ilegivel` | **regressão — tem de ser 0** |
| `causa = instrumentacao` | divergência que a mudança de specs **não** explica; investigar |

### O que não se pode concluir

A contagem total de violações muda por várias causas ao mesmo tempo, e elas **não são separáveis a
posteriori** — a lista atual, sob a D-15, está em `CONTEXTO.md` §6. Toda comparação de contagem tem
de nomear a qual delas atribui a diferença; é exigência da própria change.

**Uma regra de contagem específica desta corrida**: relatório de junção (`IvChainJunctionSpec`)
conta como **acusador próprio**, nunca dobrado no balde do typestate. Ele abre balde novo no mesmo
`(classe, método)` por construção, e a gh105 exige que o experimento conjunto o conte assim
(`openspec/changes/gh105-predicate-wiring/design.md:415-425`).

Também continua no lado `dexlib2`, medido e não reparado, o ruído estrutural que infla
`InvalidSequenceOfMethodCalls`: o **double-fire** de `getInstance(String)` (na `comp162`: TMF 2.855
de sequência contra 61 de `UnsafeAlgorithm`; SecureRandom 2.882 contra 0) e o **duplo report** dos
órfãos com cláusula.

E `cov_mop` continua medido contra o alcance das **23 specs do `jca`** nos dois lados, porque os
`.apk.json` são reusados de propósito (decisão D-c). `cov_mop` desta campanha **não é** cobertura
das specs novas — o outro lado tem **24**, não 21. Desde que o defeito B4 foi corrigido
(`86a8f178`), isso é escolha de método e não falta de alternativa: ver `CONTEXTO.md` §3, B4.

### Lacuna conhecida

**Não existe script de comparação pareada de cobertura entre as duas campanhas** — o análogo do
`experimento-comp162/scripts/compare_cmp163.py`. O `msg_diff.py` cobre violações e mensagens, que
é a pergunta que a change faz; a leitura de cobertura ficou de fora por não ser a pergunta.

Se ela for necessária depois, o script tem de consumir os dois `per_apk_admissivel.csv`, **nunca**
os `per_apk_paired.csv` crus: o `admissivel` já passou pela mesma regra C1/C2/C5 dos dois lados, e
é isso que faz a exclusão ser derivada em vez de escolhida. O molde é o `compare_cmp163.py`, que
também mostra o padrão certo quando níveis absolutos não são comparáveis: comparar os **contrastes
internos** de cada campanha (`mop_on × mop_off`, `mop_on × ape`) entre campanhas, e não os valores
absolutos.
