# gh104 — sessão do Grupo 8 (E4: reparos estruturais)

Leia este arquivo inteiro antes de tocar em qualquer coisa. Ele é o ponto de entrada da sessão.

## O que estamos fazendo

Aplicando a change OpenSpec `gh104-legible-violation-reports` (GitHub issue **#104**), que torna
legíveis os relatórios de violação do RVSEC e corrige o que o conjunto de especificações acusa no
Android. O trabalho desta sessão é o **Grupo 8 (E4)**: seis reparos estruturais provados contra a
regra api30, a assinatura JDK ou o monitor gerado; dois sítios medidos sem edição; uma retirada; três
itens comportamentais herdados do Grupo 7 (8.14, 8.15, 8.16); e o registro das divergências
estruturais que o conjunto herda e este grupo não toca.

Diretório da change:
`openspec/changes/gh104-legible-violation-reports/` — `proposal.md`, `design.md`, `tasks.md`
(96 tarefas em 10 grupos) e `tasks/<GRUPO>.md` (arquivos de execução por grupo).

## Regras que não se negociam

- **Siga rigorosamente o workflow.** `docs/WORKFLOW.md` e a regra do `CLAUDE.md`: artefatos OpenSpec
  **nunca** são escritos à mão. Use as skills via a ferramenta `Skill` — `openspec-apply-change`
  para implementar, `openspec-update-change` para revisar plano. A única edição manual permitida em
  `tasks.md` é marcar `- [ ]` → `- [x]`, imediatamente depois de cada tarefa fechar.
- **`tasks.md` é a fonte de verdade das marcas.** Não marque nada que não tenha rodado.
- Commits **sem** `Co-Authored-By` — o Pedro é o único autor. **Sempre** com pathspec explícito: o
  repositório tem centenas de linhas sujas alheias à change. **Nunca** `git add -A` nem `git commit -a`.
- Um repositório só: `git rev-parse --show-toplevel` = `.../rvsec`; `rv-android` é subdiretório dele.
- **Nunca** iniciar, parar ou gerenciar emulador à mão. (Não é problema deste grupo — a única tarefa
  de dispositivo é a 10.4.)
- **Nunca** editar `rvsec/rvsec-mop/src/main/resources/jca/` (conjunto congelado, byte-idêntico a
  `7e7acb69`), `jca_android_bug_predicate/` (arquivo reprovado, só leitura — lê-lo como referência é
  permitido; ler não é tocar), `MetaCrySL/` (oráculo, só leitura), `CipherTransformationUtil.java`
  nem `AndroidCipherTransformationUtil.java`.
- P1–P4 do `CLAUDE.md`: simplicidade; documentação narrativa que explica o *porquê*; sem
  retrocompatibilidade (código morto é deletado, backup em `backup/`); comentários no estado atual.
- Escreva em português com acentuação correta quando escrever em português. Trate o Pedro por "você".

## Estado: 67 de 96 tarefas, 37 commits

| Grupo | | Estado |
|---|---|---|
| 1 | E0 — baseline e definições | completo |
| 2 | S — arquivar o reprovado, semear o sucessor `jca_android` | completo |
| 3 | G — `__EVENTNAME` no gerador de monitor | completo |
| 4 | E2 — aridade do `args()` no tecelão | completo |
| 5 | E3 — transporte honesto | completo |
| 6 | EV — kit de validação (portões, lint, message gate, harness) | completo |
| 7 | E1 — mensagens legíveis em `jca_android` | completo |
| **8** | **E4 — reparos estruturais** | **0/16 ← esta sessão** |
| 9 | E6 — identidade | 0/4 |
| 10 | Integração e verificação | 0/9 |

Os quatro artefatos de planejamento estão completos e `openspec validate
gh104-legible-violation-reports` passa.

### O que a sessão do Grupo 7 (2026-08-20) entregou, e o que muda para você

Três commits:

- `4284cd3b` — `rvsec-core` `ErrorType` ganhou **`ForbiddenMethod`** (e só isso; `RequiredPredicate`
  não entrou, D-13) com `ErrorTypeTest` fixando o vocabulário inteiro. 48 testes verdes em
  `rvsec-core`. **Já foi feito `mvn install -pl rvsec/rvsec-core -DskipTests`**, então o monitor
  regenerado compila.
- `f60926d3` — **quatro reparos nos instrumentos do Grupo 6**, que tinham sido escritos antes de
  existir envelope. Leia isto com atenção, porque você vai usar os mesmos instrumentos:
  1. `gh104_message_gate.py` `literal-mismatch`: `v=1` era lido como inteiro isolado e produzia 50
     falsos achados. O marcador de versão sai antes da varredura numérica.
  2. `gh104_message_gate.py` `code-bijection`: comparava literais inteiros contra `codes.csv`, o que
     nunca casaria com um código que é campo do envelope. Passa a ler `code=<TOKEN>` de dentro da
     mensagem e cobre as **duas** direções — site sem código e código emitido duas vezes agora são
     achados. **Consequência para você: um reparo que remove um site (8.3, 8.6) tem de remover a
     linha do `codes.csv`, e um que adiciona (8.14) tem de adicionar — o portão pega os dois.**
  3. `gh104_diff_harness.py` `val ∈ exp`: extraía o valor observado da prosa
     `expecting ... but found ...`, o que num envelope captura a aspa de fechamento junto e **nunca**
     disparava. Passa a ler `val=`/`exp=` do envelope, com a prosa como fallback para o lado anterior.
  4. `error_sites()` em `gh104_mop_lint.py` marca site comentado (`"commented": True`) e lint e
     message gate o pulam. **Consequência para 8.14: ao descomentar o `g4` do `MessageDigestSpec`
     ele passa a contar em tudo — censo, lint, message gate, `codes.csv`.**
  E `gh104_divergence_record.py` aceita a espécie `message`.
- `6c6e1510` — os **50 sites vivos** com envelope `v=1`, `codes.csv` com 50 linhas bijetivas, cinco
  mensagens mentirosas consertadas, três `ErrorType` corrigidos (D-13), 16 sites trocando campo do
  monitor pelo getter do objeto ligado, nove linhas `guard-on-field` no registro de conformidade,
  dois traces novos (`KeyGeneratorSpec-guard-on-field.txt`, `KeyStoreSpec-guard-on-field.txt`, agora
  são 59), `data/gh104/evidence/e1_messages.md` e 23 arquivos `evidence/harness/e1-<Spec>.md`.

**E1 não tocou autômato nenhum**, e isso foi verificado mecanicamente contra o snapshot pré-E1: nos
23 arquivos, todo nome de evento, `kind`, pointcut, `args()` e `condition()` é idêntico, todo
`ere`/`fsm` é idêntico, e as contagens de `__RESET` e de `ExecutionContext` por arquivo não mudaram.
O snapshot pré-E1 está em `backup/gh104-group7-pre-e1/` (23 `.mop`, gitignored) e foi conferido
byte a byte contra o `HEAD` do Grupo 2 — **é o lado A correto se você precisar de um antes/depois
que atravesse E1**; para o Grupo 8 o lado A é o `HEAD` de agora.

## O idioma do envelope, que você tem de preservar

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observado>' exp='<esperado>' msg='<frase>'
```

`<SPEC>` é o nome da especificação sem o sufixo `Spec`, em maiúsculas (`MESSAGEDIGEST`,
`KEYPAIRGENERATOR`, `GCMPARAMETERSPEC`) — derivado mecanicamente, sem tabela de abreviações.
`<KIND>` é `ORDER`, `ALG`, `CONSTR`, `KEYSIZE`, `KSTYPE`, `PROTO` ou `FORB`, e tem de bater com o que
o `ErrorType` implica (o gerador do `codes.csv` assertava isso). `<NN>` é sequencial por spec×kind.
`ev=` **sempre** vem de `__EVENTNAME` — o gerador expande para o literal do nome no corpo de evento e
para `RVM_eventName()` num handler. **Nunca** escreva campo ou statement de bookkeeping: o lint
falha (INV-INS-120).

`q(s)` é um helper privado em `declarations` (null → `""`, `'` → `\'`, corte em 512) presente nos 11
arquivos cujo envelope interpola valor vindo da aplicação. Métodos privados em `declarations` são
emitidos verbatim no monitor.

**Cuidado com números literais na mensagem:** o `literal-mismatch` compara todo inteiro isolado de um
literal de string com os inteiros da guarda. Se o site que você editar precisar de um número na
frase, ele tem de estar na guarda; senão, escreva a frase sem dígitos (foi o que E1 fez no
`KEYPAIRGENERATOR-KEYSIZE-00`, cujo `exp` nomeia a cláusula api30 em vez de listar tamanhos).

## O trabalho: Grupo 8, tarefas 8.1 a 8.16

Leia `openspec/changes/gh104-legible-violation-reports/tasks/E4-automata.md` inteiro — é o arquivo de
execução, com a tabela de classificação item a item, a prova de cada diagnóstico e as linhas do
monitor de controle congelado. Leia também `design.md` **D-1, D-7, D-10 e D-14**, e o delta
`specs/instrumentation/spec.md` (`Executable Structural Gates`, `Differential Harness`,
INV-INS-118/123/124/125/129).

Resumo do que cada tarefa pede:

- **8.1** `GCMParameterSpecSpec`: renomear o segundo `event c1` para `c2` — é o que `ere : c1 | c2`
  sempre referenciou. G-ERE e G-6′ zeram nesse arquivo. Efeito comportamental nulo (o monitor é
  indexado pelo objeto construído, cada monitor vê no máximo um evento, `fail` é inalcançável antes e
  depois; 0 linhas no corpus). **Depois disso, a linha do `gate_allowlist.csv` que o Grupo 7 escreveu
  (`G-ERE, GCMParameterSpecSpec, c2, "... until 8.1"`) tem de sair** — ela é explicitamente temporária.
- **8.2** `SecretKeySpecSpec`: **verifique antes de editar.** O `)` sobrando é real no texto e inerte
  no efeito (o JavaMOP captura o pointcut como texto cru e parseia sem exigir `<EOF>`). Ele
  **sobreviveu** aos Grupos 2 e 7 — o lint ainda reporta `unbalanced` em `SecretKeySpecSpec.mop:26`.
  Remova-o e o lint fica limpo nesse item.
- **8.3** `MessageDigestSpec`: deletar o evento `reset`. **É o único reparo do grupo que remove
  acusações** — evidência de harness obrigatória, classe `removed`, nunca `unchanged`.
- **8.4** `KeyPairGeneratorSpec`: `String algorithm` sem inicializador. Guardar as **três condições**
  (`init1`, `init2`, `initError` ganham `algorithm != null && ...`), **não** o `validate()` — a
  correção do diagnóstico da linhagem está escrita na tarefa e é importante.
- **8.5** `SignatureSpec`: pointcuts mortos de `sign()` — `byte` → `byte[]` e `byte` → `int`. Adiciona
  **e** remove acusações; o harness tem de nomear as duas classes por trace.
- **8.6** `KeyPairGeneratorSpec`: remover o ramo inalcançável do `init1`. **Isso apaga o site
  `KEYPAIRGENERATOR-ALG-00` — a linha do `codes.csv` sai junto**, ou o `code-bijection` falha.
- **8.7** `SSLContextSpec` e `TrustManagerFactorySpec`: dois pointcuts mortos **medidos, não
  reparados**. Nenhum texto `.mop` muda.
- **8.8** **Retirada**: `KeyGeneratorSpec`/`MessageDigestSpec` testando o campo em vez do argumento
  ligado **não é defeito**. Entra no registro de conformidade como não-defeito verificado, com a
  fragilidade nomeada. Nenhuma edição.
- **8.9** Por reparo: uma entrada no `divergence_record.csv` (espécie + razão + tarefa), uma rodada de
  harness antes/depois com a classificação escrita, e a bijeção do `codes.csv` preservada.
- **8.10** Portões verdes em `jca_android`; lint limpo; `gate_allowlist.csv` com razão para cada hit
  G-2b′/G-2d restante; `CipherSpec` ainda gera.
- **8.11** Registro de conformidade completo, incluindo o fechamento das nove linhas `guard-on-field`
  que E1 deixou (reparadas, ou revertidas com a razão).
- **8.12** Registrar nove divergências estruturais herdadas como **medidas, não reparadas**.
- **8.13** `/rv-test-run tests/parity`.
- **8.14** Reviver o report `g4` do `MessageDigestSpec` (hoje comentado): descomentar com envelope e
  linha no `codes.csv`; harness com classe esperada `introduced`.
- **8.15** `__RESET` no `@fail` do `KeyPairGeneratorSpec`: **remove** acusações; classe `removed`.
- **8.16** Guardar no argumento/getter nos nove sítios `guard-on-field` que E1 declarou; única classe
  admissível é `removed` e só nos traces sem `getInstance` observado; qualquer outra classe em
  qualquer trace → reverter aquele sítio e registrar por quê.

### Ordem interna

1. **8.2 primeiro** (é uma verificação barata que fecha um item do lint).
2. 8.1 e 8.6 depois — os dois mexem no que os portões medem e o 8.6 mexe no `codes.csv`.
3. 8.3, 8.4, 8.5 — os que mudam comportamento com prova; cada um com sua rodada de harness.
4. 8.7, 8.8, 8.12 — registro, sem edição.
5. 8.14, 8.15, 8.16 — os itens medidos herdados de E1, cada um com veredito próprio.
6. 8.9, 8.10, 8.11, 8.13 fecham o grupo.

O grupo é pequeno; execução sequencial está ótima. **Não dispare subagente sem o Pedro pedir.**

## O que ainda falha, e por quê

`tests/parity` hoje: **7 falhas e 7 erros**, nenhuma delas regressão do Grupo 7.

Do `test_gh104_structural_gates.py` — **estes são os seus alvos**:

| teste | por quê |
|---|---|
| `test_jca_android_lint_is_clean` | `duplicate-event` 1 e `undeclared-symbol` 1 (`GCMParameterSpecSpec`, tarefa 8.1), `unbalanced` 1 (`SecretKeySpecSpec`, tarefa 8.2) |
| `test_jca_android_has_no_orphan_without_a_clause` | G-2 com 3 falhas (`MessageDigestSpec.reset` → 8.3, `PBEKeySpecSpec.err2`, `SecretKeySpecSpec.c3`) |
| `test_jca_android_event_names_survive_generation` | G-6′ com 1 falha (`GCMParameterSpecSpec`, 8.1) |
| `test_jca_android_message_gate_is_clean` | os 15 `self-contradicting envelope` do caso declarado — **fecham na 8.16**, não antes |

`G-ERE` **já ficou verde** no Grupo 7 (a linha da allowlist), e G-CONF e G-PRED estão verdes com 0
falhas. Eram 5 falhas nesse arquivo antes do Grupo 7, são 4.

Falhas ambientais/pré-existentes, **não mexa**: `test_no_legacy_mop::test_repo_is_clean`
(`reachesMop` no `aperv-tool`), `test_baseline_freshness`, `test_signature_file_subset`,
`test_reachability_parity` e `test_sentinel_emission` (os três últimos querem `ANDROID_SDK_HOME`).

## Comandos

```bash
# ambiente (o estado de shell não persiste entre chamadas — reexporte em cada uma)
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR    # /tmp e o scratchpad são tmpfs

# build completo do reator (só entre ondas, na raiz de .../workspace-rv/rvsec) — JDK 21
mvn clean install -DskipMopAgent -DskipTests
mvn -q install -pl rvsec/rvsec-core -DskipTests   # só o rvsec-core, se mexer nele
mvn -q test -pl rvsec/rvsec-core

# assinaturas reais da plataforma (tarefas 8.5, 8.7, 8.12g)
javap -classpath $ANDROID_HOME/platforms/android-30/android.jar java.security.Signature

# testes Python — contrato de CI; sem esses flags a coleta quebra
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q

# lint e message gate sobre o conjunto (caminhos absolutos!)
python3 scripts/gh104_mop_lint.py "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android"
python3 scripts/gh104_message_gate.py "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# gerar o monitor em scratch (~1min16) — depois ESCREVA O MARCADOR, senão os portões pulam
#   G-ERE/G-CONF/G-PRED com "the set directory could not be derived from the monitor"
uv run rv-monitor-generator generate \
  --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" --output "$TMPDIR/e4-gen"
echo -n "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" > "$TMPDIR/e4-gen/gh104_set.txt"

# portões sobre o monitor gerado
python3 scripts/gh104_gates.py --monitor "$TMPDIR/e4-gen/MultiSpec_1RuntimeMonitor.java" \
  --allowlist data/jca_android/gate_allowlist.csv \
  --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30 \
  --alias data/jca_android/alias_table.csv \
  --constraint-table data/jca_android/constraint_table.csv

# compilar o monitor gerado (prova de que compila; ~30s)
CP="$RVSEC_HOME/rvsec/rvsec-mop/target/test-classes:$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)"
javac -nowarn -cp "$CP" -d "$TMPDIR/e4-compile" "$TMPDIR/e4-gen/MultiSpec_1RuntimeMonitor.java"

# registro de divergência
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas para editar

# harness antes/depois (~7 min: rode em SEGUNDO PLANO, --traces em caminho ABSOLUTO)
python3 scripts/gh104_diff_harness.py --a <snapshot antes> --b "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --traces "$PWD/data/gh104/traces" --out "$PWD/data/gh104/evidence/harness" --group e4 \
  --json "$TMPDIR/harness_e4.json"
```

## Arquivos relacionados

- **Change**: `openspec/changes/gh104-legible-violation-reports/{proposal,design,tasks}.md`, `tasks/*.md`
  — o desta sessão é `tasks/E4-automata.md`.
- **Conjunto sucessor** (o que você edita):
  `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` (50 linhas)
- **Registros do conjunto**: `data/jca_android/` — `README.md` (censo + descrição do `codes.csv`),
  `divergence_record.csv` (121 hunks + 4 narrativas; espécies `allow-list`, `message`,
  `cipher-import`, `api30-omits`, `behavioural`, `set-archived`), `conformance_record.csv` (60 linhas,
  incluindo as 9 `guard-on-field`), `alias_table.csv` (158), `constraint_table.csv` (59),
  `gate_allowlist.csv` (a linha G-ERE sai na 8.1)
- **Evidência**: `data/gh104/` — `baseline.md`, `definitions.md`, `consumer_matrix.md`,
  `evidence/g_regeneration.md`, `evidence/e2_reach.md`, `evidence/e2_reweave.md`,
  `evidence/s_group_harness.md`, **`evidence/e1_messages.md`** (leia: traz os limites que o Grupo 8
  herda), `evidence/harness/` (`s-<Spec>.md` ×23, `e1-<Spec>.md` ×23, `selftest*.md`),
  `traces/` (**59**), `jca_frozen_control.sha256`
- **Snapshot pré-E1** (gitignored, byte-idêntico ao `HEAD` do Grupo 2): `backup/gh104-group7-pre-e1/`
- **Testes**: `tests/parity/test_gh104_specset_gates.py` (2, verdes),
  `tests/parity/test_gh104_structural_gates.py` (4 falhas em `jca_android`, todas alvo deste grupo)
- **Semente congelada** (só leitura): `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **Oráculo** (só leitura): `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/*.cryptsl`
- **Controle congelado** (`M`, `W`, `.aj` das provas): `results/gh101_group8_jca_frozen_control/monitors/`
  (gitignored; manifesto versionado; os testes pulam com razão nomeada quando ele falta)
- **Handoffs**: `docs/handoff/20260819_gh104_handoff.md`, `docs/handoff/20260820_gh104_grupo7_prompt.md`

## Aprendizados que economizam horas

1. **Caminhos passados a processos Java precisam ser `/home/pedro/...`.** O alias de diretório de
   trabalho `/pedro/...` não é um caminho que a JVM abra, e as ferramentas falham tarde e feio.
2. **O repositório Maven local é `/home/pedro/desenvolvimento/repository`**, não `~/.m2/repository`.
   Os artefatos saem com class major 65 (Java 21) mesmo compilados sob JDK 25, então JDK 21 lê tudo.
3. **O JDK faz parte da fixação da cadeia de ferramentas.** A numeração de estados de um monitor
   gerado depende do JDK que roda a geração; o controle congelado foi gerado sob JDK 25 e sob JDK 21
   o diff dá 347 diferenças, com os autômatos provadamente isomorfos. Os portões são invariantes a
   isso; só o `gh104_regen_diff.py` é sensível. Para o harness tanto faz, desde que os dois lados
   usem o mesmo JDK.
4. **O harness leva ~7 min** (duas gerações mais o replay) e a geração sozinha ~1min16. Rode em
   segundo plano. `--traces` precisa ser **absoluto**.
5. **Não escreva loop de espera com `pgrep -f "<padrão>"`**: o próprio shell do loop casa com o
   padrão e ele nunca termina. A sessão do Grupo 7 encontrou três desses rodando havia 21 horas.
   Espere pelo arquivo de saída, ou deixe a notificação de tarefa em segundo plano avisar.
6. **`rg` não está instalado** — use `grep -rE`.
7. **Não confie em número de plano nem de subagente sem reconferir.** Nesta change já vieram errados:
   a tabela de restrições (59 linhas, não 74 nem 65), `MOP-SEM-BASE` (4, não 1), a contagem de sites
   do Grupo 7 (50, não 44). Meça você mesmo antes de publicar. **As tabelas de linha por arquivo do
   `E4-automata.md` são da semente congelada e mudaram duas vezes (Grupos 2 e 7): localize por
   símbolo, nunca por número, e registre o número que você realmente editou.**
8. **Java dentro de corpo de `.mop` é inlinado literalmente no monitor.** Mantenha mínimo. Métodos
   privados em `declarations` são emitidos verbatim — é onde vive o helper `q(s)`.
9. **Os hunks do registro de divergência são chaveados por digest das linhas mudadas, com `n=0`.**
   Editar uma linha adjacente a um hunk já registrado **funde os dois** e muda o digest: o
   `--check` acusa a linha antiga como `stale` e a nova como `unrecorded`. Quando isso acontecer,
   escreva uma linha só cobrindo os dois fatos, com o `task` nomeando as duas tarefas. Hunks
   idênticos dentro de um mesmo arquivo colidem no mesmo digest — uma linha por chave basta.
10. **Defeito pré-existente, fora de escopo**: `modules/rv-instrumentation-dexlib2/pyproject.toml`
    declara um console script `rv_instrumentation_dexlib2.__main__:main` sem `__main__.py`.
11. **`mvn install` sem `-DskipMopAgent` falha** no goal `agent-gen` (`aspectjrt.jar is missing`),
    mas só *depois* de o `mop-gen` regenerar o monitor do agente JSE. Falha pré-existente.

## Definição de pronto para esta sessão

- 8.1 a 8.16 marcadas em `tasks.md`, cada uma só depois de rodar.
- Seis reparos feitos, dois sítios registrados sem edição, a retirada registrada, e as nove
  divergências herdadas da 8.12 registradas como medidas.
- Cada reparo com sua entrada no `divergence_record.csv` e sua rodada de harness com a classificação
  **escrita** — `unchanged`, `moved`, `removed` ou `introduced`. Os que mudam o que é acusado (8.3,
  8.5, 8.14, 8.15, 8.16) **não podem** ser `unchanged`.
- `codes.csv` bijetivo com o censo depois das remoções (8.6, e 8.3 não tem site) e da adição (8.14).
- Lint limpo em `jca_android`; G-2 `orphan-without-clause` = 0, G-6′ = 0, G-ERE = 0 (com a linha
  temporária da allowlist **removida**), G-CONF e G-PRED verdes; `gate_allowlist.csv` com razão para
  cada G-2b′/G-2d restante.
- Message gate: `self-contradicting envelope` a zero em todo sítio que a 8.16 deixar reparado; os
  revertidos com a razão no registro de conformidade.
- As quatro falhas de `test_gh104_structural_gates.py` fechadas, ou cada uma que sobrar explicada por
  escrito com o item que a carrega.
- Commits com pathspec explícito, mensagem no padrão `feat(jca_android): … (refs #104)`.

## Comece assim

```
Skill: openspec-apply-change  →  gh104-legible-violation-reports
```

Depois leia `tasks/E4-automata.md` inteiro e `data/gh104/evidence/e1_messages.md` (os limites que
este grupo herda), e comece pela 8.2 — a verificação barata.
