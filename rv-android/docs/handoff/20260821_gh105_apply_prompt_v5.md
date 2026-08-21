# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 25/74, Grupo 3 fechado)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `8fdf73fd`
**Progresso**: 25 de 74 tarefas (Grupos 1, 2 e **3 inteiros**)
**Estado da árvore**: verde — 92 asserções nas quatro suítes de gates passam.

---

## O que estamos fazendo

Aplicando a change **gh105-predicate-wiring** (GitHub issue #105) pelo workflow OpenSpec.
A change fia as predicates CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) no conjunto `jca_android`,
que hoje não as fia: das 19 predicates conectáveis contra as 33 regras api30, o conjunto
realiza 3 elos; as leituras de predicate vivem dentro de `condition(...)`, onde uma guarda
falsa suprime a transição e converte "origem de chave não modelada" num
`InvalidSequenceOfMethodCalls` errado; e os acusadores órfãos sustentavam no máximo 39.682
eventos = 56,1 % daquela categoria publicada (teto medido sobre a campanha `jca`, não
atribuição causal).

O gh104 fez o handler `@fail` falar. Esta change faz ele parar de disparar quando não deve.
**O Grupo 3 acabou de fechar essa segunda metade para os 17 acusadores órfãos.**

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform
gerencia o ciclo de vida inteiro. Vale para as tarefas 4.3 e 8.5.

---

## Artefatos da change (leitura obrigatória)

Em `openspec/changes/gh105-predicate-wiring/`:

| Arquivo | O que contém |
|---|---|
| `proposal.md` | o porquê, o escopo, o que é BREAKING |
| `design.md` | D-1 a D-14, o **ledger de 36 cláusulas**, o censo dos 17 órfãos (corrigido 2026-08-20, refinado 2026-08-21) |
| `specs/instrumentation/spec.md` | INV-INS-130 a INV-INS-148, Data Contracts, cenários WHEN/THEN |
| `tasks.md` | as 74 tarefas, com o comentário HTML de despacho no topo |

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
openspec instructions apply --change gh105-predicate-wiring --json
openspec validate gh105-predicate-wiring          # note: `validate` NÃO aceita --change
```

---

## O que foi feito

### Grupo 1 — substrato (rvsec-core) — 6/6, commit `b55a61a2`

`PredicateVerdict`, `PredicateStore` (chave de identidade fraca com `ReferenceQueue`,
posições `String`/`int`/`Integer` sem distinguir caixa, aridade N, `ensure/validate(Property,
Object bound, Object... values)`, `negate`, `validateAbsent`, `reset`), 19 testes JUnit,
reset do substrato no `TraceRunner.replay()`, `ExecutionContext.java` byte-idêntico em
`FROZEN_PATHS`, `Property` append-only.

**Decisão ainda a confirmar com o pesquisador**: `bound == null` é tolerado (no-op /
`NOT_OBSERVED` / `SATISFIED`) em vez de lançar, porque uma NPE dentro de advice tecido
derruba a app sob teste. Documentado no javadoc.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130),
reescopo do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`,
pré-imagem em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, **fechado**

| tarefa | commit | o que fez |
|---|---|---|
| 3.1 `SecureRandomSpec` | `25cfc590` | `c3`→`c2`, `setSeed3`→`setSeed2` fundidos; `g4` absorvido (laços no `fsm`) |
| 3.2 `TrustManagerFactorySpec` | `f464d604` | `g3`→`g1`; **correção do censo** (três "absorções" eram gêmeos) |
| 3.3 `IvParameterSpec` | `b28540ef` | `c3`→`c1`, `c4`→`c2` |
| 3.4 `SecretKeySpecSpec` | `428fd238` | `c3`→`c1`, `c4`→`c2`; linha do allow-list retirada |
| 3.5 `PBEKeySpecSpec` | `e5c5c140` | `err1`/`err2`/`err3`→`c1` numa seta; `f1`/`f2` absorvidos (Kleene) |
| 3.6 os quatro últimos | `0cd7d168` | `PBEParameterSpecSpec.c3`→`c1`, `SSLContextSpec.unsafe_protocol`→`g1`, `SignatureSpec.g3`→`g1`, `KeyPairGeneratorSpec.initError` **absorvido como alternativa de `Inits`** |
| 3.7 fechamento | `8fdf73fd` | G-ACC verde nas duas direções, **17 linhas aposentadas** da baseline, ledger dos 17 commitado |

O ledger completo, uma linha por órfão com tratamento, tarefa, trace e medição, está em
`data/gh105/evidence/f1-group-three-the-seventeen.md`. **Leia esse arquivo antes do Grupo 8**
— ele carrega os três achados que o plano não previa e os dois códigos inalcançáveis.

---

## Decisões tomadas nesta sessão (ratificadas pelo pesquisador)

### 1. A guarda do `g2` fica onde está, registrada e não tocada

Em `TrustManagerFactorySpec`, `SignatureSpec` e `SSLContextSpec`, o `g2` (sobrecarga de dois
argumentos) carrega a mesma `condition(ConscryptAliasTable.matches(...))` que o `g1` perdeu na
fusão, com a mesma supressão: `getInstance("SunX509", provider)` não dispara evento, o monitor
não observa a fábrica, e o `init` seguinte cai em `fail`. O `g2` **está** no autômato, então o
G-ACC não o vê e nenhuma tarefa dos Grupos 3-6 o alcança. **Decisão: só registrar.** Está
escrito no corpo dos dois `.mop` que a 3.6 reescreveu e no ledger dos 17. Vale abrir tarefa
própria quando alguém decidir mexer — é mudança comportamental, não reparo estrutural.

### 2. Absorção tem duas formas, e a regra decide qual

O plano definia absorver de um jeito só: laço benigno + linha `order-unmapped`. Certo para o
`SecureRandomSpec.g4` e os dois construtores proibidos do `PBEKeySpecSpec`, cujas chamadas as
regras **recusam** em vez de sequenciar. Errado para o `KeyPairGeneratorSpec.initError`, que
casa `initialize(int)` — a api30 chama isso de `i3` e põe o tamanho de chave nas CONSTRAINTS.
Num `ere`, laço não avança o autômato: `initError*` deixaria
`getInstance("RSA"); initialize(3072); generateKeyPair()` acusando `KEYPAIRGENERATOR-ORDER-00`
além do `KEYSIZE-00`, sobre uma ordenação que a regra aceita. E manter a isenção junto com a
colocação certa seria pior: a apagadura é movimento epsilon, tornaria `Inits` opcional e criaria
uma quinta divergência de G-ORDER que é artefato do mapeamento.

**Decisão: entra como alternativa do grupo `Inits`, com linha `mapped,i3`.** Medido 2 → 1.
INV-INS-135 no `spec.md` agora enuncia as duas formas; o censo do `design.md` registra o
refinamento; a partição segue 12 gêmeos + `err1` + 4 absorções = 17. Evidência em
`data/gh105/evidence/f1-KeyPairGeneratorSpec-absorption.md`.

---

## Achados desta sessão que valem mais que as tarefas

### 1. O órfão podia **suprimir** o achado, e o `SignatureSpec` é o caso extremo

`Signature.getInstance("SHA512withDSA")` seguido de um `initSign`/`update`/`sign` comum
emitia **quatro** `SIGNATURE-ORDER-00` — no `g3`, no `initSign`, no `update` e no `sign` — e
**nenhuma** acusação de algoritmo: cada `__RESET` devolve o monitor ao estado inicial, onde o
evento seguinte não está declarado, e a transição que falha toma o `@fail` em vez do corpo,
que é onde mora a checagem. Depois da fusão: um relato, `SIGNATURE-ALG-00 val='SHA512withDSA'`.
O `SSLContextSpec` faz o mesmo com dois relatos.

### 2. Um evento que não liga o parâmetro da especificação vai para **todos** os monitores

`SSLContextSpec.unsafe_protocol` era `after(String protocol)` — sem `returning`, sem `target`.
O gerador despachava para o conjunto inteiro, não para uma instância: **um** protocolo
rejeitado em qualquer ponto do programa empurrava **todo** monitor SSLContext vivo para `fail`.
É o mesmo padrão do `PBEKeySpecSpec.f1`/`f2` da 3.5. Procure `after(...)` sem `returning`/
`target` do tipo da especificação nos Grupos 4-6.

### 3. O veredito do harness continua sendo piso, não contagem

Vale para todo sítio onde os dois relatos saem da **mesma** chamada de dispatcher. Nas 3.6 a
sonda do `ErrorCollector` inteiro foi necessária só para o `PBEParameterSpecSpec` (2 → 1); nos
outros três a própria tabela do harness já mostra dois eventos acusadores do lado A. O programa
está em `data/gh105/evidence/f1-PBEParameterSpecSpec-report-count.md`; classpath em
`rvsec/rvsec-mop/target/gh104-classpath.txt`; os dois snapshots ficam no diretório que o resumo
JSON nomeia em `"scratch"`.

### 4. Uma trace do corpus estava rotulada errado

`PBEParameterSpecSpec.txt` dizia "legitimate" com um `byte[]` que nada randomiza, então violava
`randomized[salt]` o tempo todo e alcançava o órfão pela metade errada da disjunção. Comentário
corrigido; `PBEParameterSpecSpec-randomised.txt` é a que satisfaz o `c1` inteiro. **Antes de
usar uma trace do corpus como lado "satisfaz", confira que ela satisfaz todas as cláusulas.**

### 5. Aposentar um portão precisava sobreviver a `--write`

O `gh105_gate_baseline.py --write` relia a árvore e reescrevia a baseline inteira; num dia em
que a árvore tivesse regredido, ele recolocaria silenciosamente a expectativa que o grupo tinha
removido. Agora existe `retire()`: o bloco `retired` do JSON é carregado adiante e o portão
aposentado sai do payload novo, reporte ele ou não. **As próximas tarefas de fechamento de grupo
(4.15, 5.11, 7.6) usam o mesmo mecanismo** — acrescentar uma entrada em `retired` com `task`,
`was` e `note`, e tirar as linhas de `gates`.

---

## Números medidos (estado atual, reproduzidos da fonte)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **11** | 0 |
| leituras em corpo | 0 | **7** | todas |
| escritas em corpo de evento | 42 | 42 | 0 sem motivo |
| escritas no ponto de aceitação | 7 | 7 | 49 |
| chamadas de estado de aceitação | 25 | 25 | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| menções a `ExecutionContext` (INV-INS-130) | 23 arquivos | 23 | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| hunks no registro de divergência | — | **148, todos registrados** | — |
| traces do corpus | 63 | **78** | — |
| linhas do `gate_allowlist.csv` | 7 | **5** | — |
| portões aposentados na baseline | 0 | **1 (G-ACC)** | todos (7.6 apaga o mecanismo) |

Harness sobre as 78 traces contra `backup/gh105-preimage/jca_android`: **61 inalteradas,
13 movidas, 4 removidas, 0 introduzidas** (cumulativas contra a pré-imagem). Nenhuma trace do
corpus é acusada pelo sucessor e não pela pré-imagem.

G-ORDER, as quatro divergências (inalteradas pelo Grupo 3 inteiro; endereçadas por 7.1 e Grupo 6):
- `CipherSpec`: `f2` aceito pelo ORDER, rejeitado pela especificação.
- `SSLContextSpec`: `g1 Init se1 se1` aceito pela especificação, rejeitado pelo ORDER.
- `SecureRandomSpec`: `c1 c1` aceito pela especificação, rejeitado pelo ORDER.
- `TrustManagerFactorySpec`: `g1 i1 gtm` aceito pelo ORDER, rejeitado pela especificação.

---

## Pendências levantadas e ainda não endereçadas

1. **A guarda do `g2`** nos três arquivos (ver Decisão 1 acima). Registrada, não reparada.
2. **Arquivos `selftest-*.md` modificados e não commitados na árvore.**
   `data/gh104/evidence/harness/selftest-*.md` estão modificados desde antes destas sessões e a
   versão da árvore contradiz a commitada. **Não confiar nessas versões como evidência**; ler
   `git show HEAD:<caminho>`. Não foram tocados.
3. **`PBEKEYSPEC-CONSTR-01` e `SECRETKEYSPEC-CONSTR-01` são códigos sem execução possível**, por
   motivos diferentes: o primeiro porque a única cadeia de produtor que marca um `char[]` como
   randomizado passa por `String.valueOf(Object)`, que o resolvedor de pointcut do harness não
   casa; o segundo porque o construtor do JDK rejeita com exceção antes do `after ... returning`.
   Nenhum foi reparado — reparar muda o que o conjunto acusa. Ambos no `divergence_record.csv`
   e no ledger dos 17. **Quem auditar os códigos no Grupo 8 precisa saber.**

---

## Próximo passo: Grupo 4, e ele começa com uma decisão

### A change pode parar na 4.3

A sonda de alcance (design D-12) faz a pergunta que anula a change: se `UnsatisfiedConstraint`
ficar em zero no caminho de produção, o weaver é pré-requisito e os grupos de fiação **não podem**
começar. Ela roda logo depois do primeiro arquivo migrado (4.1 `CipherSpec` + 4.2 `codes.csv`,
**um commit atômico**), via `rv-experiment`/`rv-platform` (a plataforma gerencia o emulador), e o
veredito é commitado de qualquer jeito. Adiar a 4.1 não reduz risco: ela é pré-requisito da sonda.

### O que a 4.1 pede, e o que precisa ser decidido antes de editar

`CipherSpec` (3 leituras / 12 escritas / 1 chamada de estado de aceitação):

- **A tricotomia de origem de chave do `i2`** (`GENERATED_KEY` ‖ `GENERATED_PUBLIC_KEY` ‖
  `GENERATED_PRIVATE_KEY`, hoje em `condition(...)`, `CipherSpec.mop:82-86`) vira **um** sítio
  composto no corpo, sobre o `PredicateStore`, com veredito de três valores e no máximo um
  relato por cláusula violada (INV-INS-133). É a primeira leitura de três valores do conjunto,
  então é ela que obriga a 4.2.
- **As 12 escritas** — `ENCRYPTED` em `u1`-`u5`, `f1`, `f2`, `f3`, `f5`, `f6`, `f7` (11) e
  `WRAPPED_KEY` em `wkb1` (1) — mudam para o ponto de aceitação (INV-INS-134). **Decidir antes
  de editar**: cada evento escreve um *cifrado diferente*; o `@match1` só vê o último. Ou o
  ponto de aceitação recebe a coleção, ou cada escrita fica no corpo com `reason` registrado no
  `predicate_graph.csv` (que o INV-INS-134 admite). A 5.3 consome essas escritas pelo
  `validateAbsent`, então a forma escolhida tem que servir a ela.
- **A chamada `setObjectAsInAcceptingState(cipher)`** do `@match1` sai (INV-INS-147).
- **`ExecutionContext` sai do arquivo inteiro** (INV-INS-130) — são 17 menções hoje.
- **Zero headroom de eventos** (INV-INS-145): `CipherSpec` está em 17/17 eventos. **Nenhuma
  tarefa pode acrescentar evento ao `CipherSpec`**; toda ligação nova passa por junction spec ou
  pelo store.

A 4.2 acrescenta a **família de códigos *not observed*** ao `codes.csv` e estende o
`gh104_message_gate.py` (INV-INS-143) — no **mesmo commit** que a 4.1, para que não exista estado
intermediário em que o terceiro valor é computado e indistinguível rio abaixo.

Nota para as 4.4/4.6/4.10: os censos por arquivo em `tasks.md` são **pré-change**. Depois do
Grupo 3, `IvParameterSpec` tem 2 leituras (não 4), `PBEKeySpecSpec` 2 (não 4) e
`PBEParameterSpecSpec` 1 em `condition` + 1 em corpo. Reconferir com o grafo antes de citar.

---

## Receita por tarefa (a que funcionou nas 3.1 a 3.7)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai —
   foi ela que decidiu fusão vs. absorção, e qual das duas absorções.
2. **A escrita continua guardada** onde a guarda existia: `spec = s` só acontece quando a
   leitura passa, porque o `@match` transforma isso em `ENSURES` e o CrySL só garante predicate
   para um uso que satisfez a regra.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro.
4. `codes.csv` segue o sítio (colunas `event` e `file_line`); reconferir com `grep -n 'addError'`.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped` ao símbolo que a regra dá à chamada (ver Decisão 2).
6. Traces satisfaz/viola em `data/gh104/traces/`. Se um dos lados for impossível, **declarar e
   medir** a impossibilidade em vez de assumir.
7. Regerar o grafo: `--emit`. Conferir round-trip.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo, com
   a coluna `task` acumulando (`2.4;7.5;3.6`).
9. Rodar o harness diferencial (background, ~10 min) **e**, onde os dois relatos saem da mesma
   chamada, a sonda de contagem.
10. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número.
11. Rodar as quatro suítes. Commitar. Marcar o checkbox.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`, `Property.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (gramática das traces; a limitação do envelope está em `replay`)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: tarefa 7.6**)
- `scripts/gh104_gates.py` (G-CONF lê condição **e** corpo), `gh104_divergence_record.py`, `gh104_diff_harness.py`, `gh104_message_gate.py` (a 4.2 estende)
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`
- `data/gh104/traces/` (78 traces)
- `data/gh105/evidence/`: `f1-group-three-the-seventeen.md` (o ledger),
  `f1-IvParameterSpec-report-count.md`, `f1-PBEParameterSpecSpec-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f1-*.md` (gerados)
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 92 passando, ~75 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI (--json dá as contagens por gate)
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android

# baseline (comparar; --write só quando a tarefa mandar — e ele já preserva `retired`)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~10 min) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON (inclusive o "scratch") fica no TOPO da saída
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android --b $SPECS/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f1

# build do reator Java (JDK 21 no prefixo; recurso serializado)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
mvn -o test -pl rvsec-core,rvsec-mop -DskipMopAgent
```

---

## Aprendizados que custaram tempo (não redescobrir)

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda. Corpo que acusa por conta
   própria → absorve. Corpo que só religa campo → funde.
2. **E o critério de qual absorção é a regra**, não o formato do autômato. Ver Decisão 2.
3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
4. **Um órfão pode suprimir o achado, não só somar ruído.** Medido em 3.2, 3.6 (quatro vezes no
   `SignatureSpec`).
5. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` resolve para
   `PKIX` (`alias_table.csv:2`). Antes de escrever trace de violação, confira a tabela.
6. **O digest de hunk é do conteúdo.** Terminar o `.mop` antes de sincronizar `codes.csv`.
7. **`openspec validate` não aceita `--change`** — a sintaxe é `openspec validate <nome>`.
8. **`csv.writer` escreve `\r\n` por padrão.** `divergence_record.csv` **é** CRLF (preserve);
   `gate_allowlist.csv` é LF (passe `lineterminator="\n"`).
9. **Dois hunks com as mesmas linhas mudadas colidem num digest.** O `g1` e o `g2` do
   `SignatureSpec` compartilhavam a linha `24b25ebd8720` até a 3.6 separar os dois. Se uma linha
   `stale` não aparece onde você esperava, é isso.
10. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30`. Congelado; o leitor pula com motivo.
11. **`TraceRunnerTest` tem 2 falhas pré-existentes.** Verificado com `git stash`. Não é regressão.
12. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (mtime do
    `lib/gator/rvsec-analysis-client.jar`). É o tripwire funcionando.
13. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
14. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. A árvore tem **muita** modificação
    pré-existente não relacionada — **stage por caminho explícito**, nunca `git add -A`.
15. **A baseline não precisa ser regerada quando um grupo aterrissa**: as envoltórias afirmam
    *subconjunto*. As linhas saem quando a tarefa de fechamento do grupo manda, e agora saem pelo
    bloco `retired`, que o `--write` preserva.
16. **O `ere` suporta `*`, `+`, `|` e agrupamento.** Mas laço não avança o autômato — se o evento
    absorvido precisa satisfazer uma posição, ele entra como alternativa, não como laço.

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 4.1.
Leia primeiro docs/handoff/20260821_gh105_apply_prompt_v5.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/, e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão.
A 4.1 tem uma decisão a tomar antes de editar (onde as 12 escritas de ENCRYPTED aterrissam);
traga as opções ao pesquisador em vez de escolher sozinho.
```
