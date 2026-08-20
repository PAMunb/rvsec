# gh104 — sessão do Grupo 9 (E6: identidade)

Leia este arquivo inteiro antes de tocar em qualquer coisa. Ele é o ponto de entrada da sessão.

## O que estamos fazendo

Aplicando a change OpenSpec `gh104-legible-violation-reports` (GitHub issue **#104**), que torna
legíveis os relatórios de violação do RVSEC e corrige o que o conjunto de especificações acusa no
Android. O trabalho desta sessão é o **Grupo 9 (E6: identidade)**: quatro tarefas que medem se o
`event` separa causas hoje inseparáveis e, se separar, o fazem entrar na identidade de deduplicação
do `rvsec-core`.

**O Grupo 10 não é desta sessão.** Não execute nenhuma tarefa `10.x` — nem a validação de
dispositivo, nem `/rv-verify`, nem o sync de invariantes. Se o Grupo 9 fechar antes do fim da
sessão, pare e relate.

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
- **Nunca** iniciar, parar ou gerenciar emulador à mão. (Este grupo é JVM/Python puro — não há
  tarefa de dispositivo nenhuma. A validação de dispositivo é a 10.4, que **não** é desta sessão.)
- **Nunca** editar `rvsec/rvsec-mop/src/main/resources/jca/` (conjunto congelado),
  `jca_android_bug_predicate/` (arquivo reprovado, só leitura), `MetaCrySL/` (oráculo, só leitura).
  Este grupo **não tem nenhuma tarefa em `.mop`** — se você se pegar editando um `.mop`, parou de
  fazer o Grupo 9.
- P1–P4 do `CLAUDE.md`: simplicidade; documentação narrativa que explica o *porquê*; sem
  retrocompatibilidade (código morto é deletado, backup em `backup/`); comentários no estado atual.
- Escreva em português com acentuação correta quando escrever em português. Trate o Pedro por "você".

## Estado: 83 de 96 tarefas, 42 commits

| Grupo | | Estado |
|---|---|---|
| 1 | E0 — baseline e definições | completo |
| 2 | S — arquivar o reprovado, semear o sucessor `jca_android` | completo |
| 3 | G — `__EVENTNAME` no gerador de monitor | completo |
| 4 | E2 — aridade do `args()` no tecelão | completo |
| 5 | E3 — transporte honesto | completo |
| 6 | EV — kit de validação (portões, lint, message gate, harness) | completo |
| 7 | E1 — mensagens legíveis em `jca_android` | completo |
| 8 | E4 — reparos estruturais | completo |
| **9** | **E6 — identidade** | **0/4 ← esta sessão** |
| 10 | Integração e verificação | 0/9 — **não é desta sessão** |

Os quatro artefatos de planejamento estão completos e `openspec validate
gh104-legible-violation-reports` passa.

### O que a sessão do Grupo 8 (2026-08-20) entregou, e o que muda para você

Quatro commits — `bdc027a6`, `bc5e3e09`, `61c704fa`, `53eecdfe`.

**Os seis reparos estruturais e os três itens medidos.** `GCMParameterSpecSpec` `c1`→`c2`; o `)`
sobrando do `SecretKeySpecSpec`; o evento `reset` do `MessageDigestSpec` deletado; a guarda
`algorithm != null` nas três condições do `KeyPairGeneratorSpec`; os dois tipos de retorno do
`sign()` no `SignatureSpec`; o ramo inalcançável do `init1`. A 8.14 reviveu o report `g4` do
`MessageDigestSpec` (`introduced`), a 8.16 moveu quinze guardas de nove specifications para o getter
que a mensagem já nomeia (message gate de 15 para 0), e a **8.15 foi revertida** — a razão importa
para você e está abaixo.

**Três reparos de instrumento, que você herda.** Leia com atenção, porque a 9.1 lê a saída do
harness:

1. **`TraceRunner`: portão de tipo de retorno.** `Pointcut` descartava o tipo de retorno, então
   `call(public byte Signature.sign())` resolvia `s.sign()` igual a `byte[]`. Os dois tecelões
   gateiam o retorno de forma exata. Sem o reparo, a 8.5 media `unchanged`.
2. **`TraceRunner`: exceção é resultado, não fim da rodada.** Uma guarda que levanta encerrava o
   replay inteiro. Agora ela é registrada contra a sua linha de trace e o replay segue.
3. **`gh104_divergence_record.py` aceita a espécie `automaton`** (o Grupo 7 tinha acrescentado
   `message`).

**Quatro traces novos**, total agora **63**: `SignatureSpec-sign-unobserved.txt`,
`SignatureSpec-initsign-after-sign.txt`, `MessageDigestSpec-unlisted-only.txt` e
`KeyPairGeneratorSpec-sticky-fail.txt`.

**A reconciliação D-7 × D-11**, que fecha um conflito de ordem entre decisões: a D-7 dizia que os
três órfãos sem cláusula estariam "absent from `jca_android` by construction", o que valia enquanto
os predicados iam ser removidos; a **D-11 é posterior** e retirou aquela remoção. Resultado medido:
**G-2 fica em 2**, não em 0 (`PBEKeySpecSpec.err2` e `SecretKeySpecSpec.c3`), ambos com razão no
`gate_allowlist.csv`, e mais quatro hits (G-2a 1, um G-2b′, dois G-2d) vivos em `SecretKeySpec.mop`
e `RandomStringPassword.mop`. Corrigido em `design.md`, `specs/instrumentation/spec.md`, `tasks.md`
§8.10 e nos dois arquivos de execução.

## O achado do Grupo 8 que decide o seu trabalho

**`ErrorCollector.addError` escreve uma linha só quando `errors.add(err)` tem sucesso**, e o campo
é um `HashSet<ErrorDescription>`. **Atenção: o `ErrorCollector` não fica no `rvsec-core` — são
dois**, um por caminho de saída, e a 9.3 tem de olhar os dois:

- `rvsec/rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` (`addError` :40-44)
  — escreve `pw.println(err.getErrorSummary() + "," + escape(err.getExpecting()).trim())`;
- `rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java`
  (`addError` :50-54) — chama `Log.v("RVSEC", buildLine(err))`, e o `buildLine` é mantido separado
  de propósito, porque `android.util.Log` levanta `RuntimeException` no jar de stub contra o qual o
  módulo compila. **É esse o caminho do logcat que a 9.3 tem de exercitar com a fixture**, e é o
  único dos dois que a 10.4 vai usar no dispositivo.

O `buildLine` do logcat fala em "the six summary fields" no comentário — confira quantos são de
fato antes de escrever qualquer número, e ajuste o comentário se a 9.2 mudar a contagem (P4:
comentários no estado atual).

`ErrorDescription.equals/hashCode` comparam **só o `ErrorSummary`** (`ErrorDescription.java`,
`equals` :109). O `ErrorSummary` de hoje é a 5-tupla
`(spec, error, class, method, location)`, e `location` vem do `__LOC`, que expande para
`com.runtimeverification.rvmonitor.java.rt.ViolationRecorder.getLineOfCode()` — uma caminhada de
pilha.

Isso tem duas consequências que você precisa carregar:

1. **Repetição no mesmo `location` já é suprimida antes de chegar ao `errors.csv`.** Não é o
   `errors.csv` que deduplica; é o coletor.
2. **Foi exatamente isso que impediu a medição da 8.15.** O `__RESET` no `@fail` do
   `KeyPairGeneratorSpec` está certo por construção — as outras 20 handlers resetam, e o
   `Category_fail` é pegajoso, então o dispatcher rerroda o handler em todo dispatch seguinte — mas
   o harness classificou `unchanged` nos 62 traces, porque o replay tem um sítio de chamada só e o
   `ErrorSummary` colapsa a repetição. A 8.15 foi **revertida e registrada** em
   `data/jca_android/conformance_record.csv`, com essa cadeia escrita por extenso.

**Por que isso é seu:** a tarefa 9.2 acrescenta `code` e `event` ao `ErrorSummary`. Com `event`
dentro da identidade, uma repetição em **eventos distintos** deixa de colapsar e passa a ser
escrita. Ou seja, a 9.2 pode tornar a 8.15 mensurável. Não reabra a 8.15 nesta sessão — ela está
fechada com o registro certo — mas, se a 9.2 entrar, **anote em `identity_discontinuity.md` que a
reversão da 8.15 é candidata a remedição**, e diga contra qual corpus. Quem decide reabrir é o
Pedro.

## O trabalho: Grupo 9, tarefas 9.1 a 9.4

Leia `openspec/changes/gh104-legible-violation-reports/tasks/E6-identity.md` inteiro — é o arquivo
de execução. Leia também `design.md` **D-5**, o delta `specs/instrumentation/spec.md` (a
`Requirement: Dedupe Identity of a Violation Report`, INV-INS-126) e o delta `specs/core/spec.md`
(INV-CORE-57, declaração de era).

- **9.1 mede, 9.2 é que aterrissa.** Escreva `scripts/gh104_identity_discontinuity.py` e registre
  em `data/gh104/identity_discontinuity.md`. **Meça primeiro; se a descontinuidade for zero num
  corpus que carrega `ev=`, pare, não aterrisse a 9.2, e reabra a D-5** — documentado em `tasks.md`
  como bloqueado, nunca pulado em silêncio.
- **Qual corpus decide.** Em comp162 a delta é **zero por construção**: aquele corpus é anterior ao
  envelope e todo `event` sai `UNSPECIFIED`. Meça-o assim mesmo e registre os dois números lado a
  lado, mas **o número que decide a E6 é o mesmo recálculo sobre um insumo cujos registros carregam
  `ev=`** — a saída do harness do Grupo 6/8, que já existe. **Diga com todas as letras de qual
  corpus vem o número não-zero.**
- **9.2** `ErrorSummary` ganha `code` e `event`; `ErrorDescription` os extrai do envelope do campo
  `expecting` (`code=`, `ev=`), com sentinela `UNSPECIFIED`; o `toString` do `ErrorSummary` **não
  muda** — o formato da linha de logcat continua o mesmo, porque o envelope já os carrega.
- **9.3** confirme, com um logcat gravado como fixture, que as colunas `code`/`event` e as partes do
  `unique_msg` (Grupo 5) são alimentadas da linha do coletor ponta a ponta; declare a era.
- **9.4** reconstrua os jars de `lib/` e rode `/rv-test-run modules/rv-coverage` e
  `/rv-test-run modules/aperv-tool`.

### Os números que você deve reconferir, não repetir

A tabela do Grupo 1 diz **6.344** identidades distintas sob a 8-tupla
`(apk, rep, tool, spec, class, method, source, message)` em 19.664 linhas, e **409** sob a 5-tupla
`(spec, error, class, method, location)` do `ErrorSummary`. **Nomeie a tupla, nunca diga
"cinco campos".** Meça os dois você mesmo — a seção "Aprendizados" explica por quê.

Conferido nesta sessão, para você não perder tempo:

- `experimento-comp162/results/` **existe** no disco.
- `ERRORS_CSV_HEADER` do Grupo 5 tem **13 colunas**, com `code` e `event` entre `source` e
  `message` (`modules/aperv-tool/src/aperv_tool/analysis/violations.py:64-78`). Por isso a 9.1 tem
  de usar o **leitor congelado de 11 colunas** do `scripts/gh104_baseline.py`, e não o do
  `aperv_tool`, que rejeita os arquivos de comp162.
- A evidência de harness tem **281 linhas de envelope** e **19 valores distintos de `ev=`** em
  `data/gh104/evidence/harness/*.md`. É o corpus que decide.
- Alvos da 9.2, com as linhas medidas hoje (**localize por símbolo, não por número**):
  `ErrorSummary.java` 127 linhas (`hashCode` :74, `equals` :86, `toString` :123, os dois
  construtores :32 e :36); `ErrorDescription.java` 146 linhas (`createErrorSummary` :89, campo
  `expecting` :31); `ErrorDescriptionTest.java` 221 linhas (`hashCodeMatchesEquals` :180, e há um
  segundo teste vizinho, `hashCodeMatchesEqualsWhenLocationsDifferButSummariesDoNot` :197, que a
  mudança também atinge — o plano não o menciona).

### Ordem interna

1. **9.1 primeiro, sempre.** É a tarefa que decide se as outras três acontecem.
2. 9.2 só depois de a 9.1 dar não-zero num corpus com `ev=`.
3. 9.3 depois da 9.2, com a fixture.
4. 9.4 fecha; o `mvn install` na raiz do reator é o passo entre ondas.

O grupo é pequeno; execução sequencial está ótima. **Não dispare subagente sem o Pedro pedir.**

## O que ainda falha, e por quê

`tests/parity` ao fim do Grupo 8: **3 falhas e 7 erros**, todas ambientais ou pré-existentes, e
nenhuma delas do gh104. **Não mexa nelas**: `test_no_legacy_mop::test_repo_is_clean` (`reachesMop`
no `aperv-tool`), `test_baseline_freshness`, `test_signature_file_subset`, `test_reachability_parity`
e `test_sentinel_emission` (os quatro últimos querem `ANDROID_SDK_HOME`).

Os **23 testes de portão do gh104** (`test_gh104_structural_gates.py` 16,
`test_gh104_specset_gates.py` 2, `test_gh101_specset_gates.py` 5) estão **verdes**. Se algum deles
ficar vermelho depois de uma mudança sua no `rvsec-core`, é regressão sua — a 9.2 mexe no
`ErrorType`/`ErrorSummary`, que o monitor gerado consome.

## Comandos

```bash
# ambiente (o estado de shell não persiste entre chamadas — reexporte em cada uma)
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR    # /tmp e o scratchpad são tmpfs

# só o rvsec-core (a 9.2 vive aqui)
mvn -q test -pl rvsec/rvsec-core                                  # na raiz .../workspace-rv/rvsec
mvn -q install -pl rvsec/rvsec-core -DskipTests

# rebuild dos jars de lib/ (tarefa 9.4) — na raiz do reator, entre ondas
mvn clean install -DskipMopAgent -DskipTests

# testes Python — contrato de CI; sem esses flags a coleta quebra
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-coverage -q     # 9.4
uv run pytest --import-mode=importlib -o "addopts=" modules/aperv-tool -q      # 9.4

# os portões do gh104, para provar que a 9.2 não regrediu nada
uv run pytest --import-mode=importlib -o "addopts=" \
  tests/parity/test_gh104_structural_gates.py tests/parity/test_gh104_specset_gates.py \
  tests/parity/test_gh101_specset_gates.py -q

# gerar o monitor em scratch (~1min21) — depois ESCREVA O MARCADOR, senão os portões pulam
uv run rv-monitor-generator generate \
  --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" --output "$TMPDIR/e6-gen"
echo -n "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" > "$TMPDIR/e6-gen/gh104_set.txt"

# compilar o monitor gerado (prova de que a 9.2 não quebrou o que o monitor consome; ~2s)
CP="$RVSEC_HOME/rvsec/rvsec-mop/target/test-classes:$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)"
javac -nowarn -cp "$CP" -d "$TMPDIR/e6-compile" "$TMPDIR/e6-gen/MultiSpec_1RuntimeMonitor.java"

# harness antes/depois, se precisar remedir (~7 min: rode em SEGUNDO PLANO, --traces ABSOLUTO)
python3 scripts/gh104_diff_harness.py --a <snapshot antes> --b "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --traces "$PWD/data/gh104/traces" --out "$PWD/data/gh104/evidence/harness" --group e6 \
  --json "$TMPDIR/harness_e6.json"

git status --short -- rvsec/rvsec-core rv-android/scripts rv-android/data/gh104   # da raiz; pathspec sempre
```

## Arquivos relacionados

- **Change**: `openspec/changes/gh104-legible-violation-reports/{proposal,design,tasks}.md`,
  `tasks/*.md` — o desta sessão é `tasks/E6-identity.md`.
- **Alvos da 9.2** (Java): `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorSummary.java`,
  `.../ErrorDescription.java`, `rvsec/rvsec-core/src/test/java/br/unb/cic/mop/eh/ErrorDescriptionTest.java`
- **Os dois coletores** (leia para entender a dedup; a fixture da 9.3 exercita o de logcat):
  `rvsec/rvsec-logger-csv/.../eh/ErrorCollector.java` e
  `rvsec/rvsec-android/rvsec-logger-logcat/.../eh/ErrorCollector.java`
- **Alvos da 9.1/9.3** (Python): `scripts/gh104_identity_discontinuity.py` (a criar),
  `scripts/gh104_baseline.py` (o leitor congelado de 11 colunas — **reuse, não reescreva**),
  `modules/aperv-tool/src/aperv_tool/analysis/violations.py` (o cabeçalho de 13 colunas do Grupo 5)
- **Corpus que decide**: `data/gh104/evidence/harness/*.md` (92 arquivos das rodadas `e4`,
  `e4-8.14`, `e4-8.15`, `e4-8.16`, mais `s-*` e `e1-*`), 281 linhas de envelope
- **Corpus de comp162**: `experimento-comp162/results/*/*/errors.csv`, fixado por
  `modules/aperv-tool/tests/fixtures/cmp162_manifest.json` (465 entradas)
- **Evidência**: `data/gh104/` — `baseline.md` (que deve passar a referenciar a era),
  `definitions.md`, `evidence/e1_messages.md`, **`evidence/e4_automata.md`** (leia: traz a cadeia
  `__LOC`/`ErrorSummary`/dedup por extenso), `traces/` (**63**)
- **Registros do conjunto**: `data/jca_android/` — `divergence_record.csv` (130 hunks + 4
  narrativas), `conformance_record.csv` (73 linhas), `gate_allowlist.csv` (7 linhas),
  `alias_table.csv`, `constraint_table.csv`, `README.md`
- **Testes**: `tests/parity/test_gh104_structural_gates.py`, `test_gh104_specset_gates.py`,
  `test_gh101_specset_gates.py` — 23 verdes
- **Handoffs**: `docs/handoff/20260819_gh104_handoff.md`,
  `docs/handoff/20260820_gh104_grupo7_prompt.md`, `docs/handoff/20260820_gh104_grupo8_prompt.md`

## Aprendizados que economizam horas

1. **Caminhos passados a processos Java precisam ser `/home/pedro/...`.** O alias de diretório de
   trabalho `/pedro/...` não é um caminho que a JVM abra, e as ferramentas falham tarde e feio.
2. **O repositório Maven local é `/home/pedro/desenvolvimento/repository`**, não `~/.m2/repository`.
   Os artefatos saem com class major 65 (Java 21) mesmo compilados sob JDK 25, então JDK 21 lê tudo.
3. **O JDK faz parte da fixação da cadeia de ferramentas.** A numeração de estados de um monitor
   gerado depende do JDK que roda a geração. Os portões são invariantes a isso; só o
   `gh104_regen_diff.py` é sensível.
4. **Não escreva loop de espera com `pgrep -f "<padrão>"`**: o próprio shell do loop casa com o
   padrão e ele nunca termina. Espere pelo arquivo de saída, ou deixe a notificação de tarefa
   avisar.
5. **`rg` não está instalado** — use `grep -rE`.
6. **Não confie em número de plano nem de subagente sem reconferir.** Nesta change já vieram
   errados: a tabela de restrições (59 linhas, não 74 nem 65), `MOP-SEM-BASE` (4, não 1), a contagem
   de sites do Grupo 7 (50, não 44), a contagem de pointcuts `call(` do Grupo 8 (**143** sobre 23
   arquivos, não 141 sobre 21), e a previsão da D-7 de que G-2 zeraria (fica em **2**). Meça você
   mesmo antes de publicar.
7. **Uma previsão do plano pode ter sido vencida por uma decisão posterior.** O caso é a D-7 contra
   a D-11, e foi corrigido nesta sessão. Quando um critério não fechar, **verifique se outra decisão
   da change o revogou** antes de tratar como reparo inacabado.
8. **Um instrumento pode ser cego ao defeito que ele foi chamado para medir.** O Grupo 8 achou dois
   casos no `TraceRunner` e reparou os dois. Se um veredito vier `unchanged` onde a prova estática
   diz que algo mudou, **suspeite do instrumento antes de suspeitar do reparo** — mas prove qual dos
   dois, e registre.
9. **O rótulo do classificador do harness é grosso.** `classify()` compara a **lista de nomes de
   evento**, então só diz `removed` quando o lado B não acusa nada, e diz `unchanged` quando o tipo
   de erro mudou mas o evento não. A 8.16 caiu nos dois casos. Leia os envelopes, não só a classe.
10. **Os hunks do registro de divergência são chaveados por digest das linhas mudadas, com `n=0`.**
    Editar uma linha adjacente a um hunk já registrado **funde os dois** e muda o digest. Quando
    isso acontecer, escreva uma linha só cobrindo os dois fatos, com o `task` nomeando as duas
    tarefas. Hunks idênticos dentro de um mesmo arquivo colidem no mesmo digest.
11. **O INV-INS-128 compara as linhas `ExecutionContext` da semente com as do sucessor
    verbatim.** Se você precisar editar uma linha que carrega uma chamada de predicado, procure a
    forma que deixa aquela linha byte-idêntica — foi o que a 8.2 teve de fazer na segunda tentativa.
12. **Defeito pré-existente, fora de escopo**:
    `modules/rv-instrumentation-dexlib2/pyproject.toml` declara um console script
    `rv_instrumentation_dexlib2.__main__:main` sem `__main__.py`.
13. **`mvn install` sem `-DskipMopAgent` falha** no goal `agent-gen` (`aspectjrt.jar is missing`),
    mas só *depois* de o `mop-gen` regenerar o monitor do agente JSE. Falha pré-existente.

## Definição de pronto para esta sessão

- 9.1 a 9.4 marcadas em `tasks.md`, cada uma só depois de rodar — **ou** a 9.1 marcada e as outras
  três explicitamente bloqueadas em `tasks.md` com a razão, se a descontinuidade der zero num
  corpus que carrega `ev=` (nesse caso a D-5 é reaberta via `openspec-update-change`, não à mão).
- `data/gh104/identity_discontinuity.md` com: os dois números em comp162 (a 8-tupla e a 5-tupla do
  `ErrorSummary`), o recálculo com `event`, **o nome do corpus de onde vem o número que decide**, as
  definições, e a declaração de era. `data/gh104/baseline.md` referenciando a era.
- Se a 9.2 entrar: `mvn -q test -pl rvsec/rvsec-core` verde, o monitor gerado ainda compila, e os
  23 testes de portão do gh104 continuam verdes.
- 9.4: jars de `lib/` reconstruídos, `modules/rv-coverage` e `modules/aperv-tool` verdes.
- A nota sobre a 8.15 escrita em `identity_discontinuity.md`, se a 9.2 entrar — candidata a
  remedição, com o corpus nomeado. **Não reabra a 8.15 sozinho.**
- Commits com pathspec explícito, mensagem no padrão `feat(rvsec-core): … (refs #104)` ou
  `docs(gh104): … (refs #104)`.
- **Nenhuma tarefa `10.x` executada.**

## Comece assim

```
Skill: openspec-apply-change  →  gh104-legible-violation-reports
```

Depois leia `tasks/E6-identity.md` inteiro, o D-5 do `design.md` e
`data/gh104/evidence/e4_automata.md` (a cadeia `__LOC`/`ErrorSummary`/dedup que o Grupo 8 mediu), e
comece pela 9.1 — a medição que decide se o resto do grupo acontece.
